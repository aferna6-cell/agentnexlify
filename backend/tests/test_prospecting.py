"""Tests for backend/services/prospecting.py and backend/routers/prospecting.py.

Uses a purpose-built in-memory fake Supabase client (real per-table filtering,
insert/update/upsert semantics) rather than the trivial fake_supabase.Query
helper — dedup and idempotency assertions need filters to actually filter.
"""

import asyncio
import uuid
from datetime import datetime, timezone

import httpx
import pytest

import backend.models.database as _db_module
from backend.routers import prospecting as prospecting_router
from backend.services import prospecting
from backend.tests.conftest import SyncASGITestClient


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Fake Supabase client — real filtering/insert/update/upsert semantics
# ---------------------------------------------------------------------------


class _Result:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class _FakeQuery:
    def __init__(self, store, table):
        self._store = store
        self._table = table
        self._mode = None
        self._pending = None
        self._on_conflict = None
        self._filters = []
        self._order = None
        self._order_desc = False
        self._range = None
        self._limit = None
        self._count = None

    # --- verb entrypoints ---
    def select(self, columns="*", count=None, **_kw):
        self._mode = "select"
        self._count = count
        return self

    def insert(self, rows):
        self._mode = "insert"
        self._pending = rows
        return self

    def update(self, values):
        self._mode = "update"
        self._pending = values
        return self

    def upsert(self, rows, on_conflict=None, **_kw):
        self._mode = "upsert"
        self._pending = rows
        self._on_conflict = on_conflict
        return self

    def delete(self):
        self._mode = "delete"
        return self

    # --- filters/chain ---
    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def in_(self, col, vals):
        self._filters.append((col, set(vals)))
        return self

    def order(self, col, desc=False):
        self._order = col
        self._order_desc = desc
        return self

    def range(self, start, end):
        self._range = (start, end)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def is_(self, col, _val):
        return self

    # --- execution ---
    def _matches(self, row):
        for col, val in self._filters:
            if isinstance(val, set):
                if row.get(col) not in val:
                    return False
            elif row.get(col) != val:
                return False
        return True

    def _rows(self):
        return self._store.setdefault(self._table, [])

    def execute(self):
        rows = self._rows()

        if self._mode == "select":
            matched = [r for r in rows if self._matches(r)]
            total = len(matched)
            if self._order:
                matched = sorted(
                    matched, key=lambda r: r.get(self._order) or "", reverse=self._order_desc
                )
            if self._range:
                start, end = self._range
                matched = matched[start : end + 1]
            elif self._limit is not None:
                matched = matched[: self._limit]
            count = total if self._count else None
            return _Result([dict(r) for r in matched], count=count)

        if self._mode == "insert":
            pending = self._pending if isinstance(self._pending, list) else [self._pending]
            inserted = []
            now = datetime.now(timezone.utc).isoformat()
            for row in pending:
                new_row = dict(row)
                new_row.setdefault("id", str(uuid.uuid4()))
                new_row.setdefault("created_at", now)
                new_row.setdefault("updated_at", now)
                rows.append(new_row)
                inserted.append(dict(new_row))
            return _Result(inserted)

        if self._mode == "update":
            matched = [r for r in rows if self._matches(r)]
            for row in matched:
                row.update(self._pending)
                row["updated_at"] = datetime.now(timezone.utc).isoformat()
            return _Result([dict(r) for r in matched])

        if self._mode == "upsert":
            pending = self._pending if isinstance(self._pending, list) else [self._pending]
            conflict_cols = (self._on_conflict or "").split(",") if self._on_conflict else []
            result_rows = []
            now = datetime.now(timezone.utc).isoformat()
            for row in pending:
                existing = None
                if conflict_cols:
                    for r in rows:
                        if all(r.get(c) == row.get(c) for c in conflict_cols):
                            existing = r
                            break
                if existing is not None:
                    existing.update(row)
                    existing["updated_at"] = now
                    result_rows.append(dict(existing))
                else:
                    new_row = dict(row)
                    new_row.setdefault("id", str(uuid.uuid4()))
                    new_row.setdefault("created_at", now)
                    new_row.setdefault("updated_at", now)
                    rows.append(new_row)
                    result_rows.append(dict(new_row))
            return _Result(result_rows)

        if self._mode == "delete":
            matched = [r for r in rows if self._matches(r)]
            for r in matched:
                rows.remove(r)
            return _Result([dict(r) for r in matched])

        raise AssertionError(f"Unsupported query mode: {self._mode}")


class FakeDB:
    """Minimal Supabase-client stand-in: db.table(name) -> chainable query."""

    def __init__(self):
        self._store: dict[str, list[dict]] = {}

    def table(self, name):
        return _FakeQuery(self._store, name)

    def seed(self, table, rows):
        self._store.setdefault(table, []).extend(dict(r) for r in rows)


@pytest.fixture()
def fake_db():
    return FakeDB()


_CLIENT_ID = "11111111-1111-1111-1111-111111111111"


def _make_place(place_id="place-1", name="Ace Plumbing", website="https://ace-plumbing.example.com"):
    return {
        "id": place_id,
        "displayName": {"text": name},
        "formattedAddress": "123 Main St, Austin, TX",
        "nationalPhoneNumber": "(512) 555-0100",
        "websiteUri": website,
        "businessStatus": "OPERATIONAL",
        "rating": 4.6,
        "userRatingCount": 120,
        "primaryType": "plumber",
    }


# ---------------------------------------------------------------------------
# discover() — upsert + dedup
# ---------------------------------------------------------------------------


def test_discover_raises_not_configured_when_no_api_key(fake_db, monkeypatch):
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "")
    with pytest.raises(prospecting.ProspectingNotConfigured):
        run(prospecting.discover(fake_db, client_id=_CLIENT_ID, query="plumber", location="Austin, TX"))


def test_discover_upserts_places_into_prospects(fake_db, monkeypatch):
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "test-key")

    async def fake_search(text_query, api_key, page_size):
        assert api_key == "test-key"
        return [_make_place()]

    monkeypatch.setattr(prospecting, "_search_places_text", fake_search)

    rows = run(
        prospecting.discover(fake_db, client_id=_CLIENT_ID, query="plumber", location="Austin, TX", limit=10)
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["client_id"] == _CLIENT_ID
    assert row["source"] == "places_api"
    assert row["external_ref"] == "place-1"
    assert row["business_name"] == "Ace Plumbing"
    assert row["status"] == "new"
    assert row["city"] == "Austin"
    assert row["region"] == "TX"
    assert row["enrichment"]["rating"] == 4.6


def test_discover_dedups_on_second_call(fake_db, monkeypatch):
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "test-key")

    async def fake_search(text_query, api_key, page_size):
        return [_make_place()]

    monkeypatch.setattr(prospecting, "_search_places_text", fake_search)

    run(prospecting.discover(fake_db, client_id=_CLIENT_ID, query="plumber", location="Austin, TX"))
    run(prospecting.discover(fake_db, client_id=_CLIENT_ID, query="plumber", location="Austin, TX"))

    all_rows = fake_db._store.get("prospects", [])
    assert len(all_rows) == 1


def test_discover_skips_places_without_id(fake_db, monkeypatch):
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "test-key")

    async def fake_search(text_query, api_key, page_size):
        broken = _make_place()
        broken["id"] = ""
        return [broken]

    monkeypatch.setattr(prospecting, "_search_places_text", fake_search)

    rows = run(prospecting.discover(fake_db, client_id=_CLIENT_ID, query="plumber", location="Austin, TX"))
    assert rows == []


# ---------------------------------------------------------------------------
# enrich_prospect() — regex extraction from fixture HTML
# ---------------------------------------------------------------------------

_FIXTURE_HTML = """
<html><body>
<p>Call us at (512) 555-0199 or email info@ace-plumbing.example.com</p>
<p>Error tracking: errors@sentry.io</p>
</body></html>
"""


def test_enrich_prospect_extracts_email_and_phone(fake_db, monkeypatch):
    fake_db.seed(
        "prospects",
        [
            {
                "id": "p1",
                "client_id": _CLIENT_ID,
                "website": "https://ace-plumbing.example.com",
                "email": None,
                "phone": None,
                "enrichment": {},
                "status": "new",
            }
        ],
    )

    async def fake_fetch(url):
        assert url == "https://ace-plumbing.example.com"
        return _FIXTURE_HTML

    monkeypatch.setattr(prospecting, "_fetch_page_text", fake_fetch)

    updated = run(prospecting.enrich_prospect(fake_db, client_id=_CLIENT_ID, prospect_id="p1"))
    assert updated["email"] == "info@ace-plumbing.example.com"
    assert updated["phone"] == "(512) 555-0199"
    assert updated["status"] == "enriched"
    assert updated["enrichment"]["page_fetched"] is True


def test_enrich_prospect_skips_junk_email(fake_db, monkeypatch):
    fake_db.seed(
        "prospects",
        [
            {
                "id": "p2",
                "client_id": _CLIENT_ID,
                "website": "https://sentry-only.example.com",
                "email": None,
                "phone": None,
                "enrichment": {},
                "status": "new",
            }
        ],
    )

    async def fake_fetch(url):
        return "<p>Only contact: errors@sentry.io</p>"

    monkeypatch.setattr(prospecting, "_fetch_page_text", fake_fetch)

    updated = run(prospecting.enrich_prospect(fake_db, client_id=_CLIENT_ID, prospect_id="p2"))
    assert updated["email"] is None
    assert updated["status"] == "enriched"


def test_enrich_prospect_returns_none_for_missing_prospect(fake_db, monkeypatch):
    result = run(prospecting.enrich_prospect(fake_db, client_id=_CLIENT_ID, prospect_id="ghost"))
    assert result is None


def test_enrich_prospect_never_crashes_on_fetch_failure(fake_db, monkeypatch):
    fake_db.seed(
        "prospects",
        [
            {
                "id": "p3",
                "client_id": _CLIENT_ID,
                "website": "https://down.example.com",
                "email": None,
                "phone": None,
                "enrichment": {},
                "status": "new",
            }
        ],
    )

    async def fake_fetch(url):
        return ""  # _fetch_page_text degrades to "" on any failure

    monkeypatch.setattr(prospecting, "_fetch_page_text", fake_fetch)

    updated = run(prospecting.enrich_prospect(fake_db, client_id=_CLIENT_ID, prospect_id="p3"))
    assert updated["status"] == "enriched"
    assert updated["email"] is None


# ---------------------------------------------------------------------------
# verify_email() — fail-open provider abstraction
# ---------------------------------------------------------------------------


def test_verify_email_syntax_only_accepts_valid(monkeypatch):
    monkeypatch.setattr(prospecting.settings, "email_verify_provider", "none")
    assert prospecting.verify_email("owner@example.com") is True


def test_verify_email_syntax_only_rejects_invalid(monkeypatch):
    monkeypatch.setattr(prospecting.settings, "email_verify_provider", "none")
    assert prospecting.verify_email("not-an-email") is False


def test_verify_email_empty_string_is_false(monkeypatch):
    assert prospecting.verify_email("") is False


def test_verify_email_zerobounce_fails_open_on_network_error(monkeypatch):
    monkeypatch.setattr(prospecting.settings, "email_verify_provider", "zerobounce")
    monkeypatch.setattr(prospecting.settings, "email_verify_api_key", "zb-key")

    def boom(*a, **k):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(prospecting.httpx, "get", boom)

    assert prospecting.verify_email("owner@example.com") is False


def test_verify_email_zerobounce_missing_key_falls_back_to_syntax(monkeypatch):
    monkeypatch.setattr(prospecting.settings, "email_verify_provider", "zerobounce")
    monkeypatch.setattr(prospecting.settings, "email_verify_api_key", "")
    assert prospecting.verify_email("owner@example.com") is True
    assert prospecting.verify_email("not-an-email") is False


# ---------------------------------------------------------------------------
# score_prospect() — deterministic rubric
# ---------------------------------------------------------------------------


def test_score_prospect_full_marks():
    row = {
        "website": "https://example.com",
        "phone": "(512) 555-0100",
        "email": "owner@example.com",
        "email_verified": True,
        "category": "plumber",
        "enrichment": {"rating": 4.8},
    }
    # Rubric max: website 20 + phone 15 + verified email 30 + category 10 + high rating 15 = 90
    assert prospecting.score_prospect(row) == 90.0


def test_score_prospect_bare_row_scores_zero():
    assert prospecting.score_prospect({}) == 0.0


def test_score_prospect_unverified_email_scores_lower_than_verified():
    base = {"website": "https://x.com", "phone": "555", "category": "hvac", "enrichment": {}}
    unverified = prospecting.score_prospect({**base, "email": "a@b.com", "email_verified": False})
    verified = prospecting.score_prospect({**base, "email": "a@b.com", "email_verified": True})
    assert verified > unverified


def test_score_prospect_is_deterministic():
    row = {"website": "https://x.com", "phone": "555", "category": "hvac", "enrichment": {"rating": 3.5}}
    assert prospecting.score_prospect(row) == prospecting.score_prospect(row)


def test_score_prospect_mid_rating_scores_less_than_high_rating():
    base = {"website": "https://x.com"}
    mid = prospecting.score_prospect({**base, "enrichment": {"rating": 3.2}})
    high = prospecting.score_prospect({**base, "enrichment": {"rating": 4.5}})
    assert high > mid


# ---------------------------------------------------------------------------
# promote_to_lead() — creates lead, idempotent
# ---------------------------------------------------------------------------


def test_promote_to_lead_creates_lead_with_prospecting_source(fake_db):
    fake_db.seed(
        "prospects",
        [
            {
                "id": "p10",
                "client_id": _CLIENT_ID,
                "business_name": "Ace Plumbing",
                "email": "owner@ace-plumbing.example.com",
                "phone": "(512) 555-0100",
                "category": "plumber",
                "status": "qualified",
                "promoted_lead_id": None,
            }
        ],
    )

    lead = run(prospecting.promote_to_lead(fake_db, client_id=_CLIENT_ID, prospect_id="p10"))
    assert lead is not None
    assert lead["client_id"] == _CLIENT_ID
    assert lead["source"] == "prospecting"
    assert lead["name"] == "Ace Plumbing"
    assert lead["email"] == "owner@ace-plumbing.example.com"
    assert lead["status"] == "new"

    prospect_rows = [r for r in fake_db._store["prospects"] if r["id"] == "p10"]
    assert prospect_rows[0]["status"] == "promoted"
    assert prospect_rows[0]["promoted_lead_id"] == lead["id"]


def test_promote_to_lead_is_idempotent(fake_db):
    fake_db.seed(
        "prospects",
        [
            {
                "id": "p11",
                "client_id": _CLIENT_ID,
                "business_name": "Beta HVAC",
                "email": "owner@beta-hvac.example.com",
                "phone": "555",
                "category": "hvac",
                "status": "qualified",
                "promoted_lead_id": None,
            }
        ],
    )

    first = run(prospecting.promote_to_lead(fake_db, client_id=_CLIENT_ID, prospect_id="p11"))
    second = run(prospecting.promote_to_lead(fake_db, client_id=_CLIENT_ID, prospect_id="p11"))

    assert first["id"] == second["id"]
    leads = [r for r in fake_db._store["leads"] if r["client_id"] == _CLIENT_ID]
    assert len(leads) == 1


def test_promote_to_lead_dedupes_against_existing_lead_by_email(fake_db):
    fake_db.seed(
        "leads",
        [
            {
                "id": "existing-lead",
                "client_id": _CLIENT_ID,
                "email": "shared@example.com",
                "name": "Already A Lead",
                "status": "new",
            }
        ],
    )
    fake_db.seed(
        "prospects",
        [
            {
                "id": "p12",
                "client_id": _CLIENT_ID,
                "business_name": "Gamma Roofing",
                "email": "shared@example.com",
                "phone": "555",
                "category": "roofing",
                "status": "qualified",
                "promoted_lead_id": None,
            }
        ],
    )

    lead = run(prospecting.promote_to_lead(fake_db, client_id=_CLIENT_ID, prospect_id="p12"))
    assert lead["id"] == "existing-lead"
    leads = [r for r in fake_db._store["leads"] if r["client_id"] == _CLIENT_ID]
    assert len(leads) == 1


def test_promote_to_lead_returns_none_for_missing_prospect(fake_db):
    result = run(prospecting.promote_to_lead(fake_db, client_id=_CLIENT_ID, prospect_id="ghost"))
    assert result is None


# ---------------------------------------------------------------------------
# run_pipeline() — orchestration + auto-promote
# ---------------------------------------------------------------------------


def test_run_pipeline_discovers_enriches_and_scores(fake_db, monkeypatch):
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "test-key")
    monkeypatch.setattr(prospecting.settings, "email_verify_provider", "none")

    async def fake_search(text_query, api_key, page_size):
        return [_make_place()]

    async def fake_fetch(url):
        return "<p>info@ace-plumbing.example.com (512) 555-0199</p>"

    monkeypatch.setattr(prospecting, "_search_places_text", fake_search)
    monkeypatch.setattr(prospecting, "_fetch_page_text", fake_fetch)

    summary = run(
        prospecting.run_pipeline(
            fake_db, client_id=_CLIENT_ID, query="plumber", location="Austin, TX", limit=5
        )
    )
    assert summary["discovered"] == 1
    assert summary["enriched"] == 1
    assert summary["scored"] == 1
    assert summary["promoted"] == 0
    assert summary["prospects"][0]["score"] > 0


def test_run_pipeline_auto_promotes_above_threshold(fake_db, monkeypatch):
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "test-key")
    monkeypatch.setattr(prospecting.settings, "email_verify_provider", "none")

    async def fake_search(text_query, api_key, page_size):
        return [_make_place()]

    async def fake_fetch(url):
        return "<p>info@ace-plumbing.example.com (512) 555-0199</p>"

    monkeypatch.setattr(prospecting, "_search_places_text", fake_search)
    monkeypatch.setattr(prospecting, "_fetch_page_text", fake_fetch)

    summary = run(
        prospecting.run_pipeline(
            fake_db,
            client_id=_CLIENT_ID,
            query="plumber",
            location="Austin, TX",
            limit=5,
            auto_promote_threshold=0.0,
        )
    )
    assert summary["promoted"] == 1
    leads = [r for r in fake_db._store.get("leads", []) if r["client_id"] == _CLIENT_ID]
    assert len(leads) == 1
    assert leads[0]["source"] == "prospecting"


# ---------------------------------------------------------------------------
# Router — auth, plan gate, not-configured 422 (never 500)
# ---------------------------------------------------------------------------


@pytest.fixture()
def prospecting_app():
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(prospecting_router.router)
    return app


@pytest.fixture()
def prospecting_client(prospecting_app):
    test_client = SyncASGITestClient(prospecting_app)
    try:
        yield test_client
    finally:
        test_client.close()


def _wire_fake_db(monkeypatch, fake_db):
    monkeypatch.setattr(_db_module, "_service_client", fake_db)


def test_status_endpoint_requires_auth(prospecting_client):
    resp = prospecting_client.get("/api/v1/prospecting/status")
    # No Authorization header at all -> FastAPI's own required-Header
    # validation fires before get_current_tenant's body runs (422, not 401).
    assert resp.status_code == 422


def test_search_blocked_for_non_agent_os_plan(
    prospecting_client, fake_db, monkeypatch, auth_headers_for
):
    fake_db.seed("tenants", [{"id": _CLIENT_ID, "plan": "chatbot"}])
    _wire_fake_db(monkeypatch, fake_db)

    resp = prospecting_client.post(
        f"/api/v1/prospecting/search?tenant_id={_CLIENT_ID}",
        json={"query": "plumber", "location": "Austin, TX"},
        headers=auth_headers_for(_CLIENT_ID),
    )
    assert resp.status_code == 402


def test_search_returns_422_not_500_when_not_configured(
    prospecting_client, fake_db, monkeypatch, auth_headers_for
):
    fake_db.seed("tenants", [{"id": _CLIENT_ID, "plan": "agent_os"}])
    _wire_fake_db(monkeypatch, fake_db)
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "")

    resp = prospecting_client.post(
        f"/api/v1/prospecting/search?tenant_id={_CLIENT_ID}",
        json={"query": "plumber", "location": "Austin, TX"},
        headers=auth_headers_for(_CLIENT_ID),
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["error"] == "prospecting_not_configured"


def test_search_succeeds_for_agent_os_plan(
    prospecting_client, fake_db, monkeypatch, auth_headers_for
):
    fake_db.seed("tenants", [{"id": _CLIENT_ID, "plan": "agent_os"}])
    _wire_fake_db(monkeypatch, fake_db)
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "test-key")

    async def fake_search(text_query, api_key, page_size):
        return [_make_place()]

    async def fake_fetch(url):
        return ""

    monkeypatch.setattr(prospecting, "_search_places_text", fake_search)
    monkeypatch.setattr(prospecting, "_fetch_page_text", fake_fetch)

    resp = prospecting_client.post(
        f"/api/v1/prospecting/search?tenant_id={_CLIENT_ID}",
        json={"query": "plumber", "location": "Austin, TX", "limit": 5},
        headers=auth_headers_for(_CLIENT_ID),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["discovered"] == 1


def test_status_endpoint_reports_configured_flag(
    prospecting_client, fake_db, monkeypatch, auth_headers_for
):
    fake_db.seed("tenants", [{"id": _CLIENT_ID, "plan": "agent_os"}])
    _wire_fake_db(monkeypatch, fake_db)
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "test-key")

    resp = prospecting_client.get(
        "/api/v1/prospecting/status", headers=auth_headers_for(_CLIENT_ID)
    )
    assert resp.status_code == 200
    assert resp.json() == {"configured": True}


def test_reject_prospect_not_found_returns_404(
    prospecting_client, fake_db, monkeypatch, auth_headers_for
):
    fake_db.seed("tenants", [{"id": _CLIENT_ID, "plan": "agent_os"}])
    _wire_fake_db(monkeypatch, fake_db)

    resp = prospecting_client.post(
        f"/api/v1/prospecting/prospects/ghost/reject?tenant_id={_CLIENT_ID}",
        headers=auth_headers_for(_CLIENT_ID),
    )
    assert resp.status_code == 404


def test_prospecting_router_registered_in_main_app():
    """The build lane kept this router unregistered; the integration pass
    (same PR) registered it in main.py alongside migration 191 being applied.
    Contract flipped from not-registered to registered at integration time —
    see plans/nexlify-capabilities-roadmap_plan.md Phase 5."""
    from backend.main import app as main_app

    paths = {route.path for route in main_app.routes}
    assert "/api/v1/prospecting/status" in paths
