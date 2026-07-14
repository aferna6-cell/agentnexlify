"""Tests for synchronous lead scoring on widget capture (POST /api/v1/widget/lead).

Covers the in-chat lead qualification + scoring feature: after a lead is
captured, `score_lead_background()` (rule-based, deterministic — no LLM call,
see backend/services/lead_scoring.py) runs SYNCHRONOUSLY inside the request
instead of being queued as a BackgroundTask, so lead_score + lead_temperature
are already on the row by the time the response is sent. Scoring failure must
never break lead capture.

Uses FastAPI TestClient with mocked Supabase, mirroring the pattern in
tests/test_login_and_chat.py::TestLeadCaptureEdgeCases.
"""

import os
os.environ["TESTING"] = "1"

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


API_KEY = "anx_lead_scoring_test_key"
TENANT_ID = "tenant-scoring-001"


# ---------------------------------------------------------------------------
# Fixture: TestClient with mocked Supabase (same wiring as other widget tests
# — must patch get_service_supabase everywhere the request path touches it,
# including lead_scoring, since scoring now runs inline in this request).
# ---------------------------------------------------------------------------


@pytest.fixture
def test_client(mock_settings):
    """Create a FastAPI TestClient with mocked Supabase everywhere."""
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
        # Lead scoring now runs inline in the request — must share db_mock.
        patch("backend.services.lead_scoring.get_service_supabase", return_value=db_mock),
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
    """Table responses for a valid widget+tenant combo, shared by every test."""
    return {
        "widget_configs": [{
            "tenant_id": TENANT_ID,
            "api_key": API_KEY,
            "bot_name": "Scoring Test Bot",
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
            "business_name": "Scoring Test Biz",
            "business_type": "hvac",
            "city": "Austin",
            "plan": "professional",
            "plan_status": "active",
            "free_trial_started_at": None,
            "conversations_used_this_month": 5,
            "sms_notifications_enabled": False,
            "notification_phone": None,
        }],
        # Not a valid UUID on purpose — submit_lead's UUID() guard then omits
        # conversation_id from the insert, matching the existing test pattern
        # in tests/test_login_and_chat.py::TestLeadCaptureEdgeCases.
        "conversations": [{"id": "conv-scoring-001"}],
        "leads": [],
    }


def _setup_table_mock(db_mock, table_responses, update_log=None):
    """Configure db_mock.table() with per-call cycling select data, and
    record every .update(payload) call (regardless of which per-call table
    instance made it) into update_log[table_name] so tests can assert on
    what lead_scoring._persist_score actually wrote.
    """
    call_counts = {}
    update_log = update_log if update_log is not None else {}

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

        for method in ["select", "insert", "delete", "eq", "neq",
                       "gte", "lte", "gt", "lt", "limit", "order", "ilike",
                       "in_", "is_", "or_", "contains", "range", "single"]:
            getattr(table, method).return_value = table

        def _record_update(payload, _name=name):
            update_log.setdefault(_name, []).append(payload)
            return table

        table.update = MagicMock(side_effect=_record_update)

        result = MagicMock()
        result.data = current_data
        result.count = len(current_data) if current_data else 0
        table.execute.return_value = result

        return table

    db_mock.table = mock_table
    return update_log


class TestLeadScoringOnCapture:
    """POST /api/v1/widget/lead — synchronous scoring on capture."""

    def test_new_lead_capture_persists_score_and_temperature(self, test_client):
        """A newly captured lead gets lead_score + lead_temperature written
        to the leads row before the response is returned (no BackgroundTasks
        involved — the request itself performs the write)."""
        client, db_mock = test_client

        tables = _widget_and_tenant_tables()
        tables["leads"] = [
            [],                                    # 1: email dedup — no existing lead
            [{"id": "lead-score-001"}],             # 2: insert result
            [{                                      # 3: score_lead's own SELECT *
                "id": "lead-score-001",
                "client_id": TENANT_ID,
                "email": "score@example.com",
            }],
        ]
        update_log = _setup_table_mock(db_mock, tables)

        response = client.post("/api/v1/widget/lead", json={
            "api_key": API_KEY,
            "session_id": "sess-scoring-new",
            "email": "score@example.com",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["lead_id"] == "lead-score-001"

        leads_updates = update_log.get("leads", [])
        assert leads_updates, (
            "Expected at least one leads.update() call from lead_scoring "
            "._persist_score — scoring did not run synchronously"
        )
        score_update = next(
            (u for u in leads_updates if "lead_score" in u or "lead_temperature" in u),
            None,
        )
        assert score_update is not None, (
            f"No leads.update() payload contained lead_score/lead_temperature: {leads_updates}"
        )
        assert "lead_score" in score_update
        assert score_update["lead_temperature"] in ("hot", "warm", "cold")

    def test_scoring_failure_does_not_break_lead_capture(self, test_client):
        """If scoring raises, submit_lead must still return 200 with the
        created lead — capture is never sacrificed for scoring."""
        client, db_mock = test_client

        tables = _widget_and_tenant_tables()
        tables["leads"] = [
            [],                                     # dedup — no existing lead
            [{"id": "lead-score-fail-001"}],          # insert result
        ]
        _setup_table_mock(db_mock, tables)

        with patch(
            "backend.routers.widget_lead.score_lead_background",
            side_effect=RuntimeError("boom — scorer exploded"),
        ) as mock_score:
            response = client.post("/api/v1/widget/lead", json={
                "api_key": API_KEY,
                "session_id": "sess-scoring-fail",
                "email": "scorefail@example.com",
            })

        assert mock_score.called
        assert response.status_code == 200
        data = response.json()
        assert data["lead_id"] == "lead-score-fail-001"

    def test_scoring_runs_synchronously_not_as_background_task(self, test_client, monkeypatch):
        """Scoring must execute inline in the request, not via
        BackgroundTasks.add_task — the whole point is the tenant sees the
        score immediately, not after the response has already gone out."""
        client, db_mock = test_client

        tables = _widget_and_tenant_tables()
        tables["leads"] = [
            [],
            [{"id": "lead-sync-001"}],
        ]
        _setup_table_mock(db_mock, tables)

        from starlette.background import BackgroundTasks

        scheduled_funcs = []

        def capture_add_task(self, func, *args, **kwargs):
            scheduled_funcs.append(func)

        monkeypatch.setattr(BackgroundTasks, "add_task", capture_add_task)

        with patch("backend.routers.widget_lead.score_lead_background") as mock_score:
            response = client.post("/api/v1/widget/lead", json={
                "api_key": API_KEY,
                "session_id": "sess-scoring-sync",
                "email": "sync@example.com",
            })

        assert response.status_code == 200
        mock_score.assert_called_once_with("lead-sync-001")
        assert mock_score not in scheduled_funcs, (
            "score_lead_background must be called directly, not scheduled "
            "via background_tasks.add_task"
        )
