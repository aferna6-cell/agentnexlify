"""Lead attribution — unit tests.

Contracts:
  - _sanitize_attribution keeps only known string keys
  - values are truncated to 300 chars
  - unknown keys and non-string values are dropped
  - None / non-dict input -> None
  - a dict with no usable keys after filtering -> None
  - POST /api/v1/widget/lead: sanitized attribution lands in the leads
    insert payload when present, is omitted when absent, and a malformed
    attribution payload never breaks lead capture (200 still returned).
"""

import os
os.environ["TESTING"] = "1"

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.attribution import _sanitize_attribution


# ---------------------------------------------------------------------------
# _sanitize_attribution — pure helper
# ---------------------------------------------------------------------------


def test_sanitize_keeps_known_keys():
    raw = {
        "source": "google_ads",
        "utm_source": "google",
        "utm_medium": "cpc",
        "utm_campaign": "spring_sale",
        "referrer": "https://google.com/search",
        "landing_path": "/plumbing/emergency",
    }
    result = _sanitize_attribution(raw)
    assert result == raw


def test_sanitize_truncates_long_values_to_300_chars():
    raw = {"referrer": "x" * 500}
    result = _sanitize_attribution(raw)
    assert len(result["referrer"]) == 300
    assert result["referrer"] == "x" * 300


def test_sanitize_drops_unknown_keys():
    raw = {"source": "widget", "malicious_key": "drop me", "__proto__": "nope"}
    result = _sanitize_attribution(raw)
    assert result == {"source": "widget"}
    assert "malicious_key" not in result
    assert "__proto__" not in result


def test_sanitize_drops_nonstring_values():
    raw = {
        "source": "widget",
        "utm_source": 12345,
        "utm_medium": {"nested": "dict"},
        "utm_campaign": ["a", "list"],
        "referrer": None,
    }
    result = _sanitize_attribution(raw)
    assert result == {"source": "widget"}


def test_sanitize_drops_empty_string_values():
    raw = {"source": "", "utm_source": "google"}
    result = _sanitize_attribution(raw)
    assert result == {"utm_source": "google"}


def test_sanitize_none_returns_none():
    assert _sanitize_attribution(None) is None


def test_sanitize_garbage_input_returns_none():
    assert _sanitize_attribution("not a dict") is None
    assert _sanitize_attribution(["not", "a", "dict"]) is None
    assert _sanitize_attribution(12345) is None


def test_sanitize_dict_with_no_usable_keys_returns_none():
    raw = {"unknown_key": "value", "another_bad_key": 123}
    assert _sanitize_attribution(raw) is None


# ---------------------------------------------------------------------------
# POST /api/v1/widget/lead — attribution lands in the insert payload
# ---------------------------------------------------------------------------

API_KEY = "anx_attribution_test_key"
TENANT_ID = "tenant-attribution-001"


@pytest.fixture
def test_client(mock_settings):
    """FastAPI TestClient with mocked Supabase, mirroring
    tests/test_lead_scoring_on_capture.py's fixture wiring."""
    mock_settings.sentry_dsn = None
    mock_settings.supabase_service_key = "fake-key"

    db_mock = MagicMock()
    patches = [
        patch("backend.models.database.get_supabase", return_value=db_mock),
        patch("backend.routers.widget_chat.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_config.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_lead.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_booking.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_chat_helpers.get_service_supabase", return_value=db_mock),
        patch("backend.services.activity.get_service_supabase", return_value=db_mock),
        patch("backend.services.webhook_dispatcher.get_service_supabase", return_value=db_mock),
        patch("backend.services.lead_scoring.get_service_supabase", return_value=db_mock),
        # Keep background work inert — this test only cares about the insert payload.
        patch("backend.routers.widget_lead.qualify_lead_background"),
        patch("backend.routers.widget_lead._run_new_lead_followups"),
    ]
    for p in patches:
        p.start()

    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)

    yield client, db_mock

    try:
        from backend.routers.widget_chat_helpers import _cache
        _cache.clear()
    except Exception:
        pass

    try:
        from backend.limiter import limiter
        limiter.reset()
    except Exception:
        pass

    for p in patches:
        p.stop()


def _widget_and_tenant_tables():
    return {
        "widget_configs": [{
            "tenant_id": TENANT_ID,
            "api_key": API_KEY,
            "bot_name": "Attribution Test Bot",
            "primary_color": "#00BFFF",
            "greeting_message": "Hi!",
            "position": "bottom-right",
            "show_watermark": True,
            "allowed_domains": None,
            "booking_enabled": False,
            "branding": None,
            "is_online": True,
            "offline_message": None,
        }],
        "tenants": [{
            "id": TENANT_ID,
            "business_name": "Attribution Test Biz",
            "business_type": "hvac",
            "city": "Austin",
            "plan": "professional",
            "plan_status": "active",
            "free_trial_started_at": None,
            "conversations_used_this_month": 5,
            "sms_notifications_enabled": False,
            "notification_phone": None,
        }],
        "conversations": [{"id": "conv-attribution-001"}],
        "leads": [],
    }


def _setup_table_mock(db_mock, table_responses, insert_log=None):
    """Same shape as test_lead_scoring_on_capture._setup_table_mock, plus
    an insert_log so tests can inspect what was passed to .insert()."""
    call_counts = {}
    insert_log = insert_log if insert_log is not None else {}

    def mock_table(name):
        call_counts.setdefault(name, 0)
        call_counts[name] += 1

        table = MagicMock()
        data = table_responses.get(name, [])

        if data and isinstance(data[0], list):
            idx = min(call_counts[name] - 1, len(data) - 1)
            current_data = data[idx]
        else:
            current_data = data

        for method in ["select", "delete", "eq", "neq", "gte", "lte", "gt",
                       "lt", "limit", "order", "ilike", "in_", "is_", "or_",
                       "contains", "range", "single", "update"]:
            getattr(table, method).return_value = table

        def _record_insert(payload, _name=name):
            insert_log.setdefault(_name, []).append(payload)
            return table

        table.insert = MagicMock(side_effect=_record_insert)

        result = MagicMock()
        result.data = current_data
        result.count = len(current_data) if current_data else 0
        table.execute.return_value = result

        return table

    db_mock.table = mock_table
    return insert_log


def test_lead_submit_with_attribution_lands_in_insert_payload(test_client):
    client, db_mock = test_client
    tables = _widget_and_tenant_tables()
    tables["leads"] = [
        [],                                  # dedup — no existing lead
        [{"id": "lead-attr-001"}],           # insert result
        [{"id": "lead-attr-001", "client_id": TENANT_ID}],  # score_lead SELECT
    ]
    insert_log = _setup_table_mock(db_mock, tables)

    response = client.post("/api/v1/widget/lead", json={
        "api_key": API_KEY,
        "session_id": "sess-attr-001",
        "email": "attr@example.com",
        "attribution": {
            "source": "google_ads",
            "utm_source": "google",
            "utm_medium": "cpc",
            "malicious_key": "drop me",
        },
    })

    assert response.status_code == 200
    leads_inserts = insert_log.get("leads", [])
    assert leads_inserts, "expected a leads.insert() call"
    inserted = leads_inserts[0]
    assert inserted["attribution"] == {
        "source": "google_ads",
        "utm_source": "google",
        "utm_medium": "cpc",
    }


def test_lead_submit_without_attribution_omits_field(test_client):
    client, db_mock = test_client
    tables = _widget_and_tenant_tables()
    tables["leads"] = [
        [],
        [{"id": "lead-attr-002"}],
        [{"id": "lead-attr-002", "client_id": TENANT_ID}],
    ]
    insert_log = _setup_table_mock(db_mock, tables)

    response = client.post("/api/v1/widget/lead", json={
        "api_key": API_KEY,
        "session_id": "sess-attr-002",
        "email": "noattr@example.com",
    })

    assert response.status_code == 200
    inserted = insert_log["leads"][0]
    assert "attribution" not in inserted


def test_lead_submit_malformed_attribution_never_breaks_capture(test_client):
    client, db_mock = test_client
    tables = _widget_and_tenant_tables()
    tables["leads"] = [
        [],
        [{"id": "lead-attr-003"}],
        [{"id": "lead-attr-003", "client_id": TENANT_ID}],
    ]
    insert_log = _setup_table_mock(db_mock, tables)

    with patch(
        "backend.routers.widget_lead._sanitize_attribution",
        side_effect=RuntimeError("boom — malformed attribution"),
    ):
        response = client.post("/api/v1/widget/lead", json={
            "api_key": API_KEY,
            "session_id": "sess-attr-003",
            "email": "badattr@example.com",
            "attribution": {"source": "google_ads"},
        })

    assert response.status_code == 200
    data = response.json()
    assert data["lead_id"] == "lead-attr-003"
    inserted = insert_log["leads"][0]
    assert "attribution" not in inserted
