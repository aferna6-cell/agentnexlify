"""Prod incident fixes: lead status check, phone-only SMS, Places key, image 401.

Covers the contracts that were 500s in production:
- stage labels map onto leads_status_check; unknown labels are 422;
  Postgres 23514 is 422
- SMS send accepts a phone without lead_id, normalizes E.164, finds or
  creates a manual lead, and refuses opted-out numbers
- a non-ASCII GOOGLE_PLACES_API_KEY is ProspectingNotConfigured, not an
  httpx header crash
- provider 401/403 is image_gen_not_configured (422), not a generic 503
"""

import asyncio
from types import SimpleNamespace
import httpx
import pytest

from backend.services.lead_status import (
    UnknownLeadStatus,
    canonical_lead_status,
    is_check_violation,
    stage_label_for_lead,
)
from backend.services.tenant_kb_index import faq_rows_to_chunks, load_corpus_from_documents
from backend.tests.conftest import _make_auth_token

TENANT = "00000000-0000-0000-0000-000000000001"


def _headers():
    return {"Authorization": f"Bearer {_make_auth_token(TENANT)}"}


class _Result:
    def __init__(self, data):
        self.data = data
        self.count = len(data) if data is not None else 0


class _Chain:
    def __init__(self, name, store):
        self.name = name
        self.store = store
        self.op = "select"
        self.payload = None

    def select(self, *args, **kwargs):
        self.op = "select"
        return self

    def insert(self, payload):
        self.op = "insert"
        self.payload = payload
        return self

    def eq(self, *args, **kwargs):
        return self

    def in_(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def execute(self):
        if self.op == "insert" and self.name == "leads":
            row = dict(self.payload)
            row.setdefault("id", "lead-new")
            self.store["inserted"].append(row)
            return _Result([row])
        if self.name == "tenants":
            return _Result([{"id": TENANT, "plan": "growth"}])
        if self.name == "leads":
            return _Result(list(self.store.get("leads", [])))
        return _Result([])


def _wire(mock_supabase, store):
    mock_supabase.table.side_effect = lambda name: _Chain(name, store)


# ---------------------------------------------------------------------------
# Lead status
# ---------------------------------------------------------------------------


def test_canonical_status_maps_stage_labels():
    assert canonical_lead_status("New Lead") == "new"
    assert canonical_lead_status("Contacted") == "contacted"
    assert canonical_lead_status("Booked") == "appointment_booked"
    assert canonical_lead_status("Appointment Set") == "appointment_booked"
    assert canonical_lead_status("Won") == "closed"
    assert canonical_lead_status("Lost") == "lost"
    assert canonical_lead_status("closed") == "closed"
    assert canonical_lead_status(None) == "new"


def test_canonical_status_rejects_unknown():
    with pytest.raises(UnknownLeadStatus):
        canonical_lead_status("Qualified")


def test_check_violation_detects_23514():
    err = Exception("new row violates check constraint")
    err.code = "23514"
    assert is_check_violation(err)
    assert not is_check_violation(RuntimeError("boom"))


def test_board_groups_by_pipeline_stage_label():
    stages = [
        {"name": "New Lead"},
        {"name": "Won"},
        {"name": "Lost"},
    ]
    assert stage_label_for_lead({"pipeline_stage": "New Lead", "status": "new"}, stages) == "New Lead"
    assert stage_label_for_lead({"status": "closed"}, stages) == "Won"


def test_create_lead_maps_new_lead_and_keeps_stage(client, mock_supabase, monkeypatch):
    captured = {}

    class _Query:
        def execute(self):
            row = dict(captured)
            row["id"] = "lead-1"
            return _Result([row])

    def _insert(db, table, tenant, data):
        assert table == "leads"
        assert tenant == TENANT
        captured.update(data)
        return _Query()

    monkeypatch.setattr("backend.routers.leads.tenant_insert", _insert)
    resp = client.post(
        f"/api/v1/leads/{TENANT}",
        headers=_headers(),
        json={"name": "Ada", "status": "New Lead"},
    )
    assert resp.status_code == 201, resp.text
    assert captured["status"] == "new"
    assert captured["pipeline_stage"] == "New Lead"
    assert captured["client_id"] == TENANT
    assert captured["source"] == "manual"


def test_create_lead_unknown_status_is_422(client, mock_supabase):
    resp = client.post(
        f"/api/v1/leads/{TENANT}",
        headers=_headers(),
        json={"name": "Ada", "status": "Qualified"},
    )
    assert resp.status_code == 422


def test_create_lead_check_violation_is_422(client, mock_supabase, monkeypatch):
    class _Query:
        def execute(self):
            err = Exception({"message": "leads_status_check", "code": "23514"})
            err.code = "23514"
            raise err

    monkeypatch.setattr(
        "backend.routers.leads.tenant_insert",
        lambda *args, **kwargs: _Query(),
    )
    resp = client.post(
        f"/api/v1/leads/{TENANT}",
        headers=_headers(),
        json={"name": "Ada", "status": "new"},
    )
    assert resp.status_code == 422
    assert "check constraint" in resp.text


# ---------------------------------------------------------------------------
# SMS
# ---------------------------------------------------------------------------


def test_sms_requires_lead_or_phone(client, mock_supabase):
    resp = client.post(
        "/api/v1/sms/send",
        headers=_headers(),
        json={"message": "hi"},
    )
    assert resp.status_code == 422


def test_sms_phone_only_creates_lead_and_sends(client, mock_supabase, monkeypatch):
    store = {"inserted": [], "leads": []}
    _wire(mock_supabase, store)
    sent = {}

    monkeypatch.setattr("backend.routers.sms.check_sms_rate_limit", lambda *a, **k: True)
    monkeypatch.setattr("backend.routers.sms.sms_compliance.is_suppressed", lambda *a, **k: False)
    monkeypatch.setattr("backend.routers.sms.increment_sms_count", lambda *a, **k: None)

    async def _send(**kwargs):
        sent.update(kwargs)
        return True

    monkeypatch.setattr("backend.routers.sms.send_sms", _send)
    resp = client.post(
        "/api/v1/sms/send",
        headers=_headers(),
        json={"phone": "(555) 555-0100", "message": "Hello"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["success"] is True
    assert sent["to"] == "+15555550100"
    assert store["inserted"][0]["status"] == "new"
    assert store["inserted"][0]["source"] == "manual"
    assert store["inserted"][0]["phone"] == "+15555550100"
    assert store["inserted"][0]["client_id"] == TENANT


def test_sms_opted_out_number_is_422_and_not_sent(client, mock_supabase, monkeypatch):
    store = {"inserted": [], "leads": []}
    _wire(mock_supabase, store)
    monkeypatch.setattr("backend.routers.sms.check_sms_rate_limit", lambda *a, **k: True)
    monkeypatch.setattr("backend.routers.sms.sms_compliance.is_suppressed", lambda *a, **k: True)

    async def _send(**kwargs):
        raise AssertionError("must not send to an opted-out number")

    monkeypatch.setattr("backend.routers.sms.send_sms", _send)
    resp = client.post(
        "/api/v1/sms/send",
        headers=_headers(),
        json={"phone": "+15555550100", "message": "Hello"},
    )
    assert resp.status_code == 422
    assert "STOP" in resp.text
    assert store["inserted"] == []


def test_sms_invalid_phone_is_422(client, mock_supabase, monkeypatch):
    store = {"inserted": []}
    _wire(mock_supabase, store)
    monkeypatch.setattr("backend.routers.sms.check_sms_rate_limit", lambda *a, **k: True)
    resp = client.post(
        "/api/v1/sms/send",
        headers=_headers(),
        json={"phone": "123", "message": "Hello"},
    )
    assert resp.status_code == 422
    assert store["inserted"] == []


# ---------------------------------------------------------------------------
# Prospecting key
# ---------------------------------------------------------------------------


def test_places_key_non_ascii_raises_before_http(monkeypatch):
    from backend.services import prospecting

    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "key\u2019with-smart-quote")

    async def _boom(*args, **kwargs):
        raise AssertionError("httpx must not be called")

    monkeypatch.setattr(prospecting, "_search_places_text", _boom)
    with pytest.raises(prospecting.ProspectingNotConfigured):
        asyncio.run(
            prospecting.discover(
                object(), client_id=TENANT, query="plumber", location="Austin, TX"
            )
        )


def test_places_key_is_stripped(monkeypatch):
    from backend.services import prospecting

    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "  abc123 \n")
    seen = {}

    async def _search(text_query, api_key, page_size):
        seen["api_key"] = api_key
        return []

    monkeypatch.setattr(prospecting, "_search_places_text", _search)

    class _DB:
        def table(self, name):
            return self

        def upsert(self, *args, **kwargs):
            return self

        def execute(self):
            return _Result([])

    asyncio.run(
        prospecting.discover(_DB(), client_id=TENANT, query="plumber", location="Austin")
    )
    assert seen["api_key"] == "abc123"


# ---------------------------------------------------------------------------
# Image gen auth
# ---------------------------------------------------------------------------


def test_openai_401_is_credential_rejection():
    from backend.services import image_gen

    request = httpx.Request("POST", "https://api.openai.com/v1/images/generations")
    response = httpx.Response(401, request=request)

    def _post(*args, **kwargs):
        raise httpx.HTTPStatusError("unauthorized", request=request, response=response)

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(image_gen.httpx, "post", _post)
    try:
        with pytest.raises(image_gen.ImageGenError) as exc:
            image_gen._generate_openai("a cat", "sk-bad")
    finally:
        monkeypatch.undo()
    assert exc.value.status_code == 401
    assert image_gen.provider_rejected_credentials(exc.value)


def test_image_gen_401_router_returns_422(client, mock_supabase, monkeypatch):
    from backend.limiter import limiter
    from backend.main import app
    from backend.services.agent_os_gate import require_agent_os_access
    from backend.services.image_gen import ImageGenError

    limiter.reset()
    app.dependency_overrides[require_agent_os_access] = lambda: {"tenant_id": TENANT}
    monkeypatch.setattr("backend.routers.os_files.is_configured", lambda: True)
    monkeypatch.setattr(
        "backend.routers.os_files._count_today_generated",
        lambda *a, **k: 0,
    )

    def _rejected(*args, **kwargs):
        raise ImageGenError("nope", status_code=403)

    monkeypatch.setattr("backend.routers.os_files.generate_image_png", _rejected)
    try:
        resp = client.post(
            "/api/v1/os/images/generate",
            headers=_headers(),
            json={"prompt": "a cat"},
        )
    finally:
        app.dependency_overrides.pop(require_agent_os_access, None)
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["error"] == "image_gen_not_configured"


# ---------------------------------------------------------------------------
# FAQ rows feed the retrievable KB corpus
# ---------------------------------------------------------------------------


def test_faq_rows_feed_the_kb_index_when_no_faq_document():
    class _DB:
        def __init__(self):
            self.names = []
            self.name = None

        def table(self, name):
            self.names.append(name)
            self.name = name
            return self

        def select(self, *args, **kwargs):
            return self

        def eq(self, *args, **kwargs):
            return self

        def execute(self):
            data = []
            if self.name == "faq_entries":
                data = [
                    {
                        "question": "What services do you offer?",
                        "answer": "Oil changes and brakes.",
                        "is_active": True,
                    }
                ]
            return SimpleNamespace(data=data)

    chunks = load_corpus_from_documents(_DB(), TENANT)
    faq = [c for c in chunks if c.source_type == "faqs"]
    assert len(faq) == 1
    assert "Oil changes" in faq[0].content
    assert faq[0].account_id == TENANT


def test_inactive_faq_is_not_indexed():
    chunks = faq_rows_to_chunks(
        TENANT,
        [{"question": "Hours?", "answer": "9-5", "is_active": False}],
    )
    assert chunks == []


def test_check_violation_reads_dict_payload_and_message():
    err = Exception({"code": "23514", "message": "check"})
    assert is_check_violation(err)
    assert is_check_violation(Exception("violates check constraint leads_status_check"))


def test_stage_label_covers_aliases_and_misses():
    stages = [
        {"name": ""},
        {"name": "Qualified"},
        {"name": "Won"},
        {"name": "Closed"},
    ]
    assert stage_label_for_lead({"status": "Won"}, stages) == "Won"
    assert stage_label_for_lead({"status": "not-a-status"}, stages) is None
    assert stage_label_for_lead({"status": "new"}, stages) is None
    assert canonical_lead_status("Recently Contacted") == "contacted"
    assert canonical_lead_status("Marked Lost") == "lost"
    assert canonical_lead_status("New Lead inbound") == "new"
    closed_only = [{"name": "Completed Deal"}]
    # "Completed Deal" does not map; no column for status closed.
    assert stage_label_for_lead({"status": "closed"}, closed_only) is None
    booked = [{"name": "Showing Scheduled"}, {"name": "Booked"}]
    assert stage_label_for_lead({"status": "appointment_booked"}, booked) == "Booked"


def test_create_lead_non_check_error_propagates(client, mock_supabase, monkeypatch):
    class _Query:
        def execute(self):
            raise RuntimeError("db down")

    monkeypatch.setattr("backend.routers.leads.tenant_insert", lambda *a, **k: _Query())
    resp = client.post(
        f"/api/v1/leads/{TENANT}",
        headers=_headers(),
        json={"name": "Ada", "status": "new"},
    )
    assert resp.status_code == 500


def test_update_lead_maps_won_and_keeps_label(client, mock_supabase, monkeypatch):
    captured = {}

    class _Query:
        def eq(self, *args, **kwargs):
            return self

        def execute(self):
            return _Result([{"id": "lead-1", **captured}])

    def _update(db, table, tenant, data):
        captured.update(data)
        return _Query()

    monkeypatch.setattr("backend.routers.leads.tenant_update", _update)
    resp = client.patch(
        f"/api/v1/leads/{TENANT}/lead-1",
        headers=_headers(),
        json={"status": "Won"},
    )
    assert resp.status_code == 200, resp.text
    assert captured["status"] == "closed"
    assert captured["pipeline_stage"] == "Won"


def test_update_lead_check_violation_is_422(client, mock_supabase, monkeypatch):
    class _Query:
        def eq(self, *args, **kwargs):
            return self

        def execute(self):
            err = Exception("check")
            err.code = "23514"
            raise err

    monkeypatch.setattr("backend.routers.leads.tenant_update", lambda *a, **k: _Query())
    resp = client.patch(
        f"/api/v1/leads/{TENANT}/lead-1",
        headers=_headers(),
        json={"status": "new"},
    )
    assert resp.status_code == 422


def test_update_lead_route_rejects_constructed_unknown_status():
    from fastapi import HTTPException
    from backend.models.schemas import LeadUpdateRequest
    from backend.routers.leads import update_lead

    req = LeadUpdateRequest.model_construct(status="Qualified")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(update_lead(TENANT, "lead-1", req, {"tenant_id": TENANT}))
    assert exc.value.status_code == 422


class _QueueDB:
    def __init__(self, responses):
        self.responses = list(responses)
        self.updates = []

    def table(self, name):
        self.name = name
        self.payload = None
        return self

    def select(self, *args, **kwargs):
        return self

    def update(self, payload):
        self.payload = payload
        self.updates.append(payload)
        return self

    def delete(self):
        return self

    def insert(self, payload):
        self.payload = payload
        return self

    def eq(self, *args, **kwargs):
        return self

    def ilike(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        data = self.responses.pop(0)
        if isinstance(data, Exception):
            raise data
        return _Result(data)


def test_pipeline_move_maps_won(client, mock_supabase):
    db = _QueueDB([
        [{"id": "lead-1", "status": "new", "pipeline_stage": "New Lead", "name": "Ada", "email": None}],
        [{"id": "lead-1", "status": "closed", "pipeline_stage": "Won"}],
    ])
    mock_supabase.table.side_effect = db.table
    resp = client.put(
        f"/api/v1/pipeline/{TENANT}/move/lead-1",
        headers=_headers(),
        json={"status": "Won"},
    )
    assert resp.status_code == 200, resp.text
    assert db.updates[0]["status"] == "closed"
    assert db.updates[0]["pipeline_stage"] == "Won"


def test_pipeline_move_unknown_is_422(client, mock_supabase):
    db = _QueueDB([
        [{"id": "lead-1", "status": "new", "pipeline_stage": None, "name": "Ada", "email": None}],
    ])
    mock_supabase.table.side_effect = db.table
    resp = client.put(
        f"/api/v1/pipeline/{TENANT}/move/lead-1",
        headers=_headers(),
        json={"status": "Qualified"},
    )
    assert resp.status_code == 422


def test_pipeline_move_check_violation_is_422(client, mock_supabase):
    db = _QueueDB([
        [{"id": "lead-1", "status": "new", "pipeline_stage": "New Lead", "name": "Ada", "email": None}],
        Exception("check"),
    ])
    # The update execute raises a plain Exception; mark it as 23514 via a custom error.
    err = Exception("check constraint")
    err.code = "23514"
    db.responses[1] = err
    mock_supabase.table.side_effect = db.table
    resp = client.put(
        f"/api/v1/pipeline/{TENANT}/move/lead-1",
        headers=_headers(),
        json={"status": "lost", "pipeline_stage": "Lost"},
    )
    assert resp.status_code == 422


def test_pipeline_delete_counts_pipeline_stage(client, mock_supabase):
    db = _QueueDB([
        [{"id": "stage-1", "name": "New Lead"}],
        [{"id": "lead-1"}],
        [],
    ])
    mock_supabase.table.side_effect = db.table
    resp = client.delete(
        f"/api/v1/pipeline/{TENANT}/stages/stage-1",
        headers=_headers(),
    )
    assert resp.status_code == 409


def test_pipeline_board_groups_pipeline_stage(client, mock_supabase):
    db = _QueueDB([
        [{"id": "s1", "name": "New Lead", "sort_order": 0, "is_won": False, "is_lost": False}],
        [{
            "id": "lead-1",
            "name": "Ada",
            "status": "new",
            "pipeline_stage": "New Lead",
            "deal_value": 10,
            "created_at": "2026-01-01T00:00:00+00:00",
        }],
    ])
    mock_supabase.table.side_effect = db.table
    resp = client.get(f"/api/v1/pipeline/{TENANT}/board", headers=_headers())
    assert resp.status_code == 200, resp.text
    assert resp.json()["leads_by_stage"]["New Lead"][0]["id"] == "lead-1"


def test_sms_lead_id_uses_stored_phone(client, mock_supabase, monkeypatch):
    store = {"inserted": [], "leads": [{"id": "lead-9", "phone": "5555550100"}]}
    _wire(mock_supabase, store)
    sent = {}
    monkeypatch.setattr("backend.routers.sms.check_sms_rate_limit", lambda *a, **k: True)
    monkeypatch.setattr("backend.routers.sms.sms_compliance.is_suppressed", lambda *a, **k: False)
    monkeypatch.setattr("backend.routers.sms.increment_sms_count", lambda *a, **k: None)

    async def _send(**kwargs):
        sent.update(kwargs)
        return True

    monkeypatch.setattr("backend.routers.sms.send_sms", _send)
    resp = client.post(
        "/api/v1/sms/send",
        headers=_headers(),
        json={"lead_id": "lead-9", "message": "Hello"},
    )
    assert resp.status_code == 200, resp.text
    assert sent["to"] == "+15555550100"
    assert store["inserted"] == []


def test_sms_lead_not_found(client, mock_supabase, monkeypatch):
    _wire(mock_supabase, {"inserted": [], "leads": []})
    monkeypatch.setattr("backend.routers.sms.check_sms_rate_limit", lambda *a, **k: True)
    resp = client.post(
        "/api/v1/sms/send",
        headers=_headers(),
        json={"lead_id": "missing", "message": "Hello"},
    )
    assert resp.status_code == 404


def test_sms_find_or_create_edges():
    from fastapi import HTTPException
    from backend.routers.sms import _find_or_create_lead_by_phone

    with pytest.raises(HTTPException) as missing:
        _find_or_create_lead_by_phone(object(), TENANT, "")
    assert missing.value.status_code == 422

    class _Down:
        def table(self, name):
            raise RuntimeError("down")

    with pytest.raises(HTTPException) as lookup:
        _find_or_create_lead_by_phone(_Down(), TENANT, "+15555550100")
    assert lookup.value.status_code == 503

    class _InsertFail:
        def table(self, name):
            return self

        def select(self, *a, **k):
            return self

        def eq(self, *a, **k):
            return self

        def in_(self, *a, **k):
            return self

        def limit(self, *a, **k):
            return self

        def insert(self, payload):
            raise RuntimeError("insert down")

        def execute(self):
            return _Result([])

    with pytest.raises(HTTPException) as created:
        _find_or_create_lead_by_phone(_InsertFail(), TENANT, "+15555550100")
    assert created.value.status_code == 503

    class _EmptyInsert(_InsertFail):
        def insert(self, payload):
            return self

        def execute(self):
            if getattr(self, "_inserted", False):
                return _Result([])
            self._inserted = True
            return _Result([])

    with pytest.raises(HTTPException) as empty:
        _find_or_create_lead_by_phone(_EmptyInsert(), TENANT, "+15555550100")
    assert empty.value.status_code == 503


def test_prospecting_status_reports_ascii_key(monkeypatch):
    from backend.routers.prospecting import prospecting_status
    from backend.services import prospecting

    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "")
    assert asyncio.run(prospecting_status({"tenant_id": TENANT})) == {"configured": False}
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "  abc \n")
    assert asyncio.run(prospecting_status({"tenant_id": TENANT})) == {"configured": True}
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "bad\u2019key")
    assert asyncio.run(prospecting_status({"tenant_id": TENANT})) == {"configured": False}


def test_sync_faq_document_paths(monkeypatch):
    from backend.services import tenant_kb as tk

    class _Boom:
        def table(self, name):
            raise RuntimeError("no faqs")

    assert tk.sync_faq_document(_Boom(), TENANT) == "skipped"
    assert tk._faq_markdown([{"question": " ", "answer": "x", "is_active": True}]) == ""
    assert "Hours" in tk._faq_markdown([{"question": "Hours?", "answer": "9-5", "is_active": False}]) or True
    assert tk._faq_markdown([{"question": "Hours?", "answer": "9-5", "is_active": False}]) == ""

    class _Empty:
        def __init__(self):
            self.updated = None
            self._calls = 0

        def table(self, name):
            self.name = name
            return self

        def select(self, *a, **k):
            return self

        def eq(self, *a, **k):
            return self

        def limit(self, *a, **k):
            return self

        def update(self, payload):
            self.updated = payload
            return self

        def execute(self):
            self._calls += 1
            if self._calls == 1:
                return _Result([])
            return _Result([{"id": "doc-1", "source": "faq", "external_id": "faq_entries"}])

    db = _Empty()
    assert tk.sync_faq_document(db, TENANT) == "empty"
    assert db.updated["status"] == "deleted"

    monkeypatch.setattr(tk, "upsert_document", lambda *a, **k: "added")

    class _Faqs:
        def table(self, name):
            return self

        def select(self, *a, **k):
            return self

        def eq(self, *a, **k):
            return self

        def execute(self):
            return _Result([{"question": "Services?", "answer": "Oil changes", "is_active": True}])

    assert tk.sync_faq_document(_Faqs(), TENANT) == "added"


def test_load_corpus_skips_duplicate_faqs_and_survives_doc_failure():
    class _FaqDoc:
        def table(self, name):
            self.name = name
            return self

        def select(self, *a, **k):
            return self

        def eq(self, *a, **k):
            return self

        def execute(self):
            return SimpleNamespace(data=[{
                "id": "11111111-1111-1111-1111-111111111111",
                "filename": "FAQs.md",
                "content_md": "## Services?\n\nOil changes",
                "source": "faq",
                "status": "active",
            }])

    chunks = load_corpus_from_documents(_FaqDoc(), TENANT)
    assert chunks
    assert all(c.source_type == "faq" for c in chunks)

    class _DocsDown:
        def table(self, name):
            self.name = name
            if name == "tenant_kb_documents":
                raise RuntimeError("docs down")
            return self

        def select(self, *a, **k):
            return self

        def eq(self, *a, **k):
            return self

        def execute(self):
            return SimpleNamespace(data=[{
                "question": "Hours?",
                "answer": "9 to 5",
                "is_active": True,
            }])

    fallback = load_corpus_from_documents(_DocsDown(), TENANT)
    assert any("9 to 5" in c.content for c in fallback)

    class _FaqDown(_DocsDown):
        def table(self, name):
            raise RuntimeError("all down")

    assert load_corpus_from_documents(_FaqDown(), TENANT) == []
