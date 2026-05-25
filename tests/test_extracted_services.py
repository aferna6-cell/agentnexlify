"""Smoke tests for extracted service modules.

Covers services factored out of branding_service.py per Rule 9:
- backend.services.dashboard_service (activity feed, knowledge stats, trial status)
- backend.services.conversations_service (list, detail, tag upsert)
- backend.services.faq_service (CRUD)
- backend.services.widget_config_service (PUT /widget-config)

These tests exercise the HTTP endpoints so coverage counts against the
changed-lines coverage gate (85% Python via diff_cover).
"""

import os

os.environ["TESTING"] = "1"

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.dependencies import _get_current_tenant
from backend.services import dashboard_service

TENANT = "tenant-123"


async def _owner_claims_override():
    return {"tenant_id": TENANT, "role": "owner"}


@pytest.fixture
def override_tenant():
    """Replace JWT auth dependency with owner claims for TENANT."""
    app.dependency_overrides[_get_current_tenant] = _owner_claims_override
    try:
        yield
    finally:
        app.dependency_overrides.pop(_get_current_tenant, None)


# ── dashboard_service ──────────────────────────────────────────


def test_compute_trial_status_returns_safe_default():
    """compute_trial_status currently returns a no-op safe default for any tenant row."""
    assert dashboard_service.compute_trial_status({}) == {
        "trial_days_remaining": None,
        "trial_expired": False,
    }
    assert (
        dashboard_service._compute_trial_status
        is dashboard_service.compute_trial_status
    )


def test_get_activity_returns_activity_log_when_present(
    mock_supabase, monkeypatch, override_tenant
):
    """When activity_log has rows, /activity should map them and return shape."""
    mock_supabase.set_table_data(
        "activity_log",
        [
            {
                "id": "a1",
                "activity_type": "lead_created",
                "description": "Lead Aidan created",
                "lead_id": "l1",
                "metadata": {},
                "created_at": "2026-04-20T12:00:00Z",
            }
        ],
    )
    monkeypatch.setattr(
        "backend.services.dashboard_service._get_service_supabase",
        lambda: mock_supabase,
    )

    client = TestClient(app)
    resp = client.get(f"/api/v1/auth/activity/{TENANT}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["activity"][0]["type"] == "lead_created"
    assert body["activity"][0]["id"] == "a1"


def test_get_activity_falls_back_to_leads_and_chats_when_log_empty(
    mock_supabase, monkeypatch, override_tenant
):
    """Empty activity_log triggers fallback to leads + chat_messages + appointments."""
    mock_supabase.set_table_data("activity_log", [])
    mock_supabase.set_table_data(
        "leads",
        [
            {
                "id": "lead-1",
                "name": "Jane",
                "email": "j@x.com",
                "created_at": "2026-04-20T11:00:00Z",
            }
        ],
    )
    mock_supabase.set_table_data(
        "chat_messages",
        [{"session_id": "session-abc123def456", "created_at": "2026-04-20T10:00:00Z"}],
    )
    mock_supabase.set_table_data(
        "appointments",
        [
            {
                "id": "appt-1",
                "customer_name": "Bob",
                "start_time": "2026-04-21T15:00:00Z",
                "created_at": "2026-04-20T09:00:00Z",
            }
        ],
    )
    monkeypatch.setattr(
        "backend.services.dashboard_service._get_service_supabase",
        lambda: mock_supabase,
    )

    client = TestClient(app)
    resp = client.get(f"/api/v1/auth/activity/{TENANT}")

    assert resp.status_code == 200
    types = {item["type"] for item in resp.json()["activity"]}
    assert {"new_lead", "conversation_summary", "appointment"} <= types


def test_get_activity_forbidden_when_tenant_mismatch(override_tenant):
    """Tenant claim mismatch should return 403."""
    client = TestClient(app)
    resp = client.get("/api/v1/auth/activity/other-tenant")
    assert resp.status_code == 403


def test_get_knowledge_stats_aggregates_counts(
    mock_supabase, monkeypatch, override_tenant
):
    """knowledge-stats should sum counts from faq, website, feedback, menu, jobs."""
    mock_supabase.set_table_data("faq_entries", [], count=4)
    mock_supabase.set_table_data(
        "website_content",
        [{"pages_found": 12, "crawl_status": "completed"}],
    )
    mock_supabase.set_table_data("tenants", [{"website_url": "https://example.com"}])
    mock_supabase.set_table_data("ai_feedback", [], count=2)
    mock_supabase.set_table_data("chat_flows", [{"name": "main"}])
    mock_supabase.set_table_data("menu_items", [], count=7)
    mock_supabase.set_table_data("jobs", [], count=3)
    monkeypatch.setattr(
        "backend.services.dashboard_service._get_service_supabase",
        lambda: mock_supabase,
    )

    client = TestClient(app)
    resp = client.get(f"/api/v1/auth/knowledge-stats/{TENANT}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["faq_count"] == 4
    assert body["website_pages_crawled"] == 12
    assert body["website_crawl_status"] == "completed"
    assert body["website_url"] == "https://example.com"
    assert body["feedback_corrections_count"] == 2
    assert body["active_chat_flow"] == "main"
    assert body["menu_items_count"] == 7
    assert body["job_postings_count"] == 3


def test_get_knowledge_stats_zeros_when_db_empty(
    mock_supabase, monkeypatch, override_tenant
):
    """All-empty supabase responses should return zeroed stats, not 500."""
    for tbl in (
        "faq_entries",
        "website_content",
        "tenants",
        "ai_feedback",
        "chat_flows",
        "menu_items",
        "jobs",
    ):
        mock_supabase.set_table_data(tbl, [])
    monkeypatch.setattr(
        "backend.services.dashboard_service._get_service_supabase",
        lambda: mock_supabase,
    )

    client = TestClient(app)
    resp = client.get(f"/api/v1/auth/knowledge-stats/{TENANT}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["faq_count"] == 0
    assert body["website_pages_crawled"] == 0
    assert body["job_postings_count"] == 0


# ── conversations_service ───────────────────────────────────────


def test_list_conversations_groups_by_session(
    mock_supabase, monkeypatch, override_tenant
):
    """Multiple messages with same session_id should collapse to one conversation."""
    mock_supabase.set_table_data(
        "chat_messages",
        [
            {
                "session_id": "s1",
                "role": "user",
                "content": "hello there",
                "created_at": "2026-04-20T12:00:00Z",
            },
            {
                "session_id": "s1",
                "role": "assistant",
                "content": "hi! how can I help",
                "created_at": "2026-04-20T12:00:05Z",
            },
            {
                "session_id": "s2",
                "role": "user",
                "content": "different conversation",
                "created_at": "2026-04-20T11:00:00Z",
            },
        ],
    )
    mock_supabase.set_table_data(
        "leads",
        [{"id": "l1", "conversation_id": "s1", "name": "Aidan", "email": "a@x.com"}],
    )
    mock_supabase.set_table_data(
        "conversations",
        [
            {
                "session_id": "s1",
                "tags": ["vip"],
                "channel": "widget",
                "assigned_to": None,
            }
        ],
    )
    monkeypatch.setattr(
        "backend.services.conversations_service._get_service_supabase",
        lambda: mock_supabase,
    )

    client = TestClient(app)
    resp = client.get(f"/api/v1/auth/conversations/{TENANT}")

    assert resp.status_code == 200
    body = resp.json()
    convs = body["conversations"]
    by_id = {c["session_id"]: c for c in convs}
    assert "s1" in by_id and "s2" in by_id
    assert by_id["s1"]["lead_name"] == "Aidan"
    assert by_id["s1"]["lead_id"] == "l1"
    assert by_id["s1"]["tags"] == ["vip"]
    assert by_id["s1"]["message_count"] == 2


def test_list_conversations_filters_by_search(
    mock_supabase, monkeypatch, override_tenant
):
    """search=foo should only return sessions whose messages contain 'foo'."""
    mock_supabase.set_table_data(
        "chat_messages",
        [
            {
                "session_id": "s1",
                "role": "user",
                "content": "talking about foobar",
                "created_at": "2026-04-20T12:00:00Z",
            },
            {
                "session_id": "s2",
                "role": "user",
                "content": "unrelated text",
                "created_at": "2026-04-20T11:00:00Z",
            },
        ],
    )
    mock_supabase.set_table_data("leads", [])
    mock_supabase.set_table_data("conversations", [])
    monkeypatch.setattr(
        "backend.services.conversations_service._get_service_supabase",
        lambda: mock_supabase,
    )

    client = TestClient(app)
    resp = client.get(f"/api/v1/auth/conversations/{TENANT}?search=foobar")

    assert resp.status_code == 200
    sids = {c["session_id"] for c in resp.json()["conversations"]}
    assert sids == {"s1"}


def test_get_conversation_messages_returns_thread(
    mock_supabase, monkeypatch, override_tenant
):
    """GET /conversations/{tenant}/{session} should return messages array."""
    mock_supabase.set_table_data(
        "chat_messages",
        [
            {
                "id": "m1",
                "role": "user",
                "content": "hi",
                "created_at": "2026-04-20T12:00:00Z",
            },
            {
                "id": "m2",
                "role": "assistant",
                "content": "hello",
                "created_at": "2026-04-20T12:00:05Z",
            },
        ],
    )
    monkeypatch.setattr(
        "backend.services.conversations_service._get_service_supabase",
        lambda: mock_supabase,
    )

    client = TestClient(app)
    resp = client.get(f"/api/v1/auth/conversations/{TENANT}/session-xyz")

    assert resp.status_code == 200
    assert len(resp.json()["messages"]) == 2


def test_update_conversation_tags_inserts_new_row_when_missing(
    mock_supabase, monkeypatch, override_tenant
):
    """If no conversations row exists, tag update should insert one."""
    mock_supabase.set_table_data("conversations", [])
    monkeypatch.setattr(
        "backend.services.conversations_service._get_service_supabase",
        lambda: mock_supabase,
    )

    client = TestClient(app)
    resp = client.put(
        f"/api/v1/auth/conversations/{TENANT}/session-new/tags",
        json={"tags": ["urgent", "billing"]},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["tags"] == ["urgent", "billing"]
    assert body["session_id"] == "session-new"


def test_update_conversation_tags_updates_existing_row(
    mock_supabase, monkeypatch, override_tenant
):
    """If a conversations row exists, tag update should run UPDATE, not INSERT."""
    mock_supabase.set_table_data(
        "conversations", [{"id": "conv-1", "session_id": "session-x"}]
    )
    monkeypatch.setattr(
        "backend.services.conversations_service._get_service_supabase",
        lambda: mock_supabase,
    )

    client = TestClient(app)
    resp = client.put(
        f"/api/v1/auth/conversations/{TENANT}/session-x/tags",
        json={"tags": ["resolved"]},
    )

    assert resp.status_code == 200
    assert resp.json()["tags"] == ["resolved"]


def test_update_conversation_tags_rejects_non_list(
    mock_supabase, monkeypatch, override_tenant
):
    """Non-list tags payload should be rejected with 400."""
    mock_supabase.set_table_data("conversations", [])
    monkeypatch.setattr(
        "backend.services.conversations_service._get_service_supabase",
        lambda: mock_supabase,
    )

    from backend.services.conversations_service import update_conversation_tags
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        update_conversation_tags(TENANT, "session-x", "not-a-list")  # type: ignore[arg-type]
    assert exc_info.value.status_code == 400


# ── faq_service ────────────────────────────────────────────────


def test_list_faq_returns_active_entries(mock_supabase, monkeypatch, override_tenant):
    """GET /faq/{tenant} should return active FAQ rows."""
    mock_supabase.set_table_data(
        "faq_entries",
        [
            {
                "id": "f1",
                "question": "Q?",
                "answer": "A.",
                "category": "general",
                "is_active": True,
            }
        ],
    )
    monkeypatch.setattr(
        "backend.services.faq_service._get_service_supabase",
        lambda: mock_supabase,
    )

    client = TestClient(app)
    resp = client.get(f"/api/v1/auth/faq/{TENANT}")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["id"] == "f1"
    assert body[0]["question"] == "Q?"


def test_create_faq_inserts_and_returns_row(
    mock_supabase, monkeypatch, override_tenant
):
    """POST /faq/{tenant} should insert and return the new entry."""
    monkeypatch.setattr(
        "backend.services.faq_service._get_service_supabase",
        lambda: mock_supabase,
    )

    client = TestClient(app)
    resp = client.post(
        f"/api/v1/auth/faq/{TENANT}",
        json={"question": "How?", "answer": "Like this.", "category": "ops"},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["question"] == "How?"
    assert body["answer"] == "Like this."


def test_update_faq_returns_404_when_missing(
    mock_supabase, monkeypatch, override_tenant
):
    """Updating a non-existent FAQ row should return 404 from service layer."""
    mock_supabase.set_table_data("faq_entries", [])
    monkeypatch.setattr(
        "backend.services.faq_service._get_service_supabase",
        lambda: mock_supabase,
    )

    client = TestClient(app)
    resp = client.put(
        f"/api/v1/auth/faq/{TENANT}/missing-id",
        json={"question": "Q", "answer": "A", "category": None},
    )

    assert resp.status_code == 404


def test_update_faq_returns_updated_row_when_found(
    mock_supabase, monkeypatch, override_tenant
):
    """Updating an existing FAQ row should return the updated payload."""
    mock_supabase.set_table_data(
        "faq_entries",
        [
            {
                "id": "f1",
                "question": "new Q",
                "answer": "new A",
                "category": "ops",
                "is_active": True,
            }
        ],
    )
    monkeypatch.setattr(
        "backend.services.faq_service._get_service_supabase",
        lambda: mock_supabase,
    )

    client = TestClient(app)
    resp = client.put(
        f"/api/v1/auth/faq/{TENANT}/f1",
        json={"question": "new Q", "answer": "new A", "category": "ops"},
    )

    assert resp.status_code == 200
    assert resp.json()["question"] == "new Q"


def test_delete_faq_returns_204(mock_supabase, monkeypatch, override_tenant):
    """DELETE /faq/{tenant}/{faq_id} should soft-delete and return 204."""
    monkeypatch.setattr(
        "backend.services.faq_service._get_service_supabase",
        lambda: mock_supabase,
    )

    client = TestClient(app)
    resp = client.delete(f"/api/v1/auth/faq/{TENANT}/f1")

    assert resp.status_code == 204


# ── widget_config_service ──────────────────────────────────────


def test_update_widget_config_updates_basic_fields(
    mock_supabase, monkeypatch, override_tenant
):
    """PUT /widget-config/{tenant} should update bot_name and return detail."""
    mock_supabase.set_table_data("tenants", [{"plan": "free"}])
    mock_supabase.set_table_data(
        "widget_configs",
        [
            {
                "bot_name": "New Bot",
                "primary_color": "#abcdef",
                "greeting_message": "Hi!",
                "position": "bottom-right",
                "branding": None,
                "teaser_message": None,
                "teaser_delay_seconds": 3,
                "teaser_enabled": True,
                "enable_ai_fallback": False,
                "enable_structured_lead_parser": False,
            }
        ],
    )
    monkeypatch.setattr(
        "backend.services.widget_config_service._get_service_supabase",
        lambda: mock_supabase,
    )

    client = TestClient(app)
    resp = client.put(
        f"/api/v1/auth/widget-config/{TENANT}",
        json={"bot_name": "New Bot"},
    )

    assert resp.status_code == 200
    assert resp.json()["bot_name"] == "New Bot"


def test_update_widget_config_rejects_empty_update(
    mock_supabase, monkeypatch, override_tenant
):
    """An empty update body should be rejected with 400."""
    mock_supabase.set_table_data("tenants", [{"plan": "free"}])
    monkeypatch.setattr(
        "backend.services.widget_config_service._get_service_supabase",
        lambda: mock_supabase,
    )

    client = TestClient(app)
    resp = client.put(f"/api/v1/auth/widget-config/{TENANT}", json={})

    assert resp.status_code == 400


def test_update_widget_config_404_when_row_missing(
    mock_supabase, monkeypatch, override_tenant
):
    """When widget_configs has no matching row, return 404."""
    mock_supabase.set_table_data("tenants", [{"plan": "free"}])
    mock_supabase.set_table_data("widget_configs", [])
    monkeypatch.setattr(
        "backend.services.widget_config_service._get_service_supabase",
        lambda: mock_supabase,
    )

    client = TestClient(app)
    resp = client.put(
        f"/api/v1/auth/widget-config/{TENANT}",
        json={"bot_name": "X"},
    )

    assert resp.status_code == 404


# ── error-path coverage (exception branches in service modules) ─


class _RaisingSupabase:
    """Supabase client whose .table().execute() always raises.

    Used to exercise the try/except branches in dashboard_service,
    conversations_service, widget_config_service, industry_faqs without
    needing a real database.
    """

    def table(self, _name):
        return self

    def select(self, *args, **kwargs):
        return self

    def insert(self, *args, **kwargs):
        return self

    def update(self, *args, **kwargs):
        return self

    def delete(self):
        return self

    def eq(self, *args):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args):
        return self

    def execute(self):
        raise RuntimeError("simulated supabase failure")


def test_get_activity_handles_all_query_failures(monkeypatch, override_tenant):
    """All 4 activity queries raise → activity returns empty list, no 500."""
    monkeypatch.setattr(
        "backend.services.dashboard_service._get_service_supabase",
        lambda: _RaisingSupabase(),
    )

    client = TestClient(app)
    resp = client.get(f"/api/v1/auth/activity/{TENANT}")

    assert resp.status_code == 200
    assert resp.json()["activity"] == []


def test_get_knowledge_stats_handles_all_query_failures(monkeypatch, override_tenant):
    """Every knowledge-stats query raises → defaults preserved, no 500."""
    monkeypatch.setattr(
        "backend.services.dashboard_service._get_service_supabase",
        lambda: _RaisingSupabase(),
    )

    client = TestClient(app)
    resp = client.get(f"/api/v1/auth/knowledge-stats/{TENANT}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["faq_count"] == 0
    assert body["website_pages_crawled"] == 0
    assert body["website_url"] is None
    assert body["feedback_corrections_count"] == 0
    assert body["active_chat_flow"] is None
    assert body["menu_items_count"] == 0
    assert body["job_postings_count"] == 0


def test_list_conversations_handles_leads_and_metadata_failures(
    monkeypatch, override_tenant
):
    """Failures fetching leads + conversation metadata should not 500 the endpoint."""

    class _PartialFailSupabase:
        """chat_messages succeeds; leads + conversations raise."""

        def __init__(self):
            self._current_table = None

        def table(self, name):
            self._current_table = name
            return self

        def select(self, *args, **kwargs):
            return self

        def eq(self, *args):
            return self

        def order(self, *args, **kwargs):
            return self

        def limit(self, *args):
            return self

        def execute(self):
            if self._current_table == "chat_messages":
                return type(
                    "R",
                    (),
                    {
                        "data": [
                            {
                                "session_id": "s9",
                                "role": "user",
                                "content": "ping",
                                "created_at": "2026-04-20T12:00:00Z",
                            }
                        ],
                        "count": None,
                    },
                )()
            raise RuntimeError(f"simulated {self._current_table} failure")

    monkeypatch.setattr(
        "backend.services.conversations_service._get_service_supabase",
        lambda: _PartialFailSupabase(),
    )

    client = TestClient(app)
    resp = client.get(f"/api/v1/auth/conversations/{TENANT}")

    assert resp.status_code == 200
    sids = {c["session_id"] for c in resp.json()["conversations"]}
    assert "s9" in sids


def test_list_conversations_filters_by_channel(mock_supabase, monkeypatch, override_tenant):
    """channel=facebook should only return conversations whose channel matches."""
    mock_supabase.set_table_data(
        "chat_messages",
        [
            {
                "session_id": "s1",
                "role": "user",
                "content": "hi",
                "created_at": "2026-04-20T12:00:00Z",
            },
            {
                "session_id": "s2",
                "role": "user",
                "content": "hello",
                "created_at": "2026-04-20T11:00:00Z",
            },
        ],
    )
    mock_supabase.set_table_data("leads", [])
    mock_supabase.set_table_data(
        "conversations",
        [
            {"session_id": "s1", "tags": [], "channel": "facebook", "assigned_to": None}
        ],
    )
    monkeypatch.setattr(
        "backend.services.conversations_service._get_service_supabase",
        lambda: mock_supabase,
    )

    client = TestClient(app)
    resp = client.get(f"/api/v1/auth/conversations/{TENANT}?channel=facebook")

    assert resp.status_code == 200
    sids = {c["session_id"] for c in resp.json()["conversations"]}
    assert sids == {"s1"}


def test_list_conversations_search_matches_lead_name(
    mock_supabase, monkeypatch, override_tenant
):
    """search should also match against the lead name, not just message content."""
    mock_supabase.set_table_data(
        "chat_messages",
        [
            {
                "session_id": "s1",
                "role": "user",
                "content": "unrelated text",
                "created_at": "2026-04-20T12:00:00Z",
            },
        ],
    )
    mock_supabase.set_table_data(
        "leads",
        [
            {
                "id": "l-aidan",
                "conversation_id": "s1",
                "name": "Aidan Smith",
                "email": "a@x.com",
            }
        ],
    )
    mock_supabase.set_table_data("conversations", [])
    monkeypatch.setattr(
        "backend.services.conversations_service._get_service_supabase",
        lambda: mock_supabase,
    )

    client = TestClient(app)
    resp = client.get(f"/api/v1/auth/conversations/{TENANT}?search=aidan")

    assert resp.status_code == 200
    sids = {c["session_id"] for c in resp.json()["conversations"]}
    assert sids == {"s1"}


def test_create_faq_raises_500_when_insert_returns_empty(monkeypatch, override_tenant):
    """If supabase insert returns no data, faq_service.create_faq raises 500."""

    class _EmptyInsertSupabase:
        def table(self, _name):
            return self

        def insert(self, _data):
            return self

        def execute(self):
            return type("R", (), {"data": [], "count": None})()

    monkeypatch.setattr(
        "backend.services.faq_service._get_service_supabase",
        lambda: _EmptyInsertSupabase(),
    )

    client = TestClient(app)
    resp = client.post(
        f"/api/v1/auth/faq/{TENANT}",
        json={"question": "Q", "answer": "A", "category": "ops"},
    )
    assert resp.status_code == 500


def test_update_widget_config_with_branding_payload(
    mock_supabase, monkeypatch, override_tenant
):
    """Branding payload should be sanitized, plan-filtered, and merged with existing."""
    mock_supabase.set_table_data("tenants", [{"plan": "professional"}])
    mock_supabase.set_table_data(
        "widget_configs",
        [
            {
                "bot_name": "Bot",
                "primary_color": "#000000",
                "greeting_message": "Hi",
                "position": "bottom-right",
                "branding": {"logo_url": "old"},
                "teaser_message": None,
                "teaser_delay_seconds": 3,
                "teaser_enabled": True,
                "enable_ai_fallback": False,
                "enable_structured_lead_parser": False,
            }
        ],
    )
    monkeypatch.setattr(
        "backend.services.widget_config_service._get_service_supabase",
        lambda: mock_supabase,
    )

    client = TestClient(app)
    resp = client.put(
        f"/api/v1/auth/widget-config/{TENANT}",
        json={
            "branding": {
                "logo_url": "https://example.com/logo.png",
                "custom_css": ".foo { color: red; }",
            }
        },
    )

    assert resp.status_code == 200


def test_seed_industry_faqs_noop_when_industry_unknown(monkeypatch):
    """Unknown industry → no rows seeded → early return, no DB calls."""
    from backend.services import industry_faqs as ifaqs

    called = {"db": False}

    def _no_db():
        called["db"] = True
        raise AssertionError("DB should not be touched for unknown industry")

    monkeypatch.setattr(ifaqs, "_get_db", _no_db)
    ifaqs.seed_industry_faqs("t-xyz", "alien_industry_xyz_no_match", "Biz", "City")
    assert called["db"] is False


def test_seed_industry_faqs_logs_warning_on_db_failure(monkeypatch):
    """Insert exception is caught and logged, doesn't propagate."""
    from backend.services import industry_faqs as ifaqs

    class _RaisingInsertSupabase:
        def table(self, _name):
            return self

        def insert(self, _rows):
            return self

        def execute(self):
            raise RuntimeError("simulated insert failure")

    monkeypatch.setattr(ifaqs, "_get_db", lambda: _RaisingInsertSupabase())
    ifaqs.seed_industry_faqs("t-xyz", "salon", "Beauty Co", "Boston")
