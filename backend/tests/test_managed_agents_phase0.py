"""Phase 0 E2E matrix for the Managed Agents surface (#33 / rollout plan).

Covers the acceptance matrix from issue #33 + plans/managed-agents-rollout_plan.md
§Phase 0:

- unconfigured 503 stub shape for EVERY run endpoint (backward-compat contract)
- health endpoints report "planned" when nothing is provisioned
- tenant isolation (403 for a mismatched tenant path)
- run-log recording on success + unavailable paths (migration 188 wiring)
- managed_agent_run_log service semantics (mock supabase, fail-open, TESTING)
- plan gate interaction: chatbot plan blocked from document drafting

Run with:
    TESTING=1 python -m pytest backend/tests/test_managed_agents_phase0.py --noconftest -q
"""

import contextlib
import os
from unittest.mock import MagicMock, patch

os.environ.setdefault("TESTING", "1")

import pytest
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.config import settings
from backend.dependencies import _get_current_tenant
from backend.limiter import limiter
from backend.routers import managed_agent_runs as mar
from backend.services import managed_agent_run_log as run_log
from backend.services.document_drafting import DocumentDraftingError, draft_document
from backend.services.managed_agents import ManagedAgentsError, SessionTerminalState
from backend.services.managed_agents_registry import ManagedAgentNotConfigured
from backend.tests.conftest import SyncASGITestClient

TENANT = "11111111-1111-1111-1111-111111111111"
CLAIMS = {"tenant_id": TENANT}

_ALL_AGENT_SETTINGS = {
    "managed_agents_environment_id": "",
    "lead_qualifier_agent_id": "",
    "document_drafter_agent_id": "",
    "codebase_reviewer_agent_id": "",
    "support_agent_id": "",
    "structured_extractor_agent_id": "",
    "deep_researcher_agent_id": "",
    "field_monitor_agent_id": "",
    "data_analyst_agent_id": "",
}

LEAD_QUALIFY_BODY = {"lead_name": "Bob Vance"}
DRAFT_BODY = {
    "kind": "quote",
    "customer": {"name": "Bob Vance"},
    "line_items": [{"description": "Refrigeration", "qty": 1, "unit_price": 100.0}],
}
SUPPORT_BODY = {"question": "How do I reset my widget?"}
EXTRACT_BODY = {"raw_text": "Bob Vance, bob@vance.example", "target_schema": "lead"}


@contextlib.contextmanager
def _settings(**overrides):
    """Pin every managed-agent setting to '' then apply overrides."""
    values = {**_ALL_AGENT_SETTINGS, **overrides}
    with contextlib.ExitStack() as stack:
        for key, value in values.items():
            stack.enter_context(patch.object(settings, key, value))
        yield


def _client(claims=CLAIMS):
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.include_router(mar.router)
    app.dependency_overrides[_get_current_tenant] = lambda: claims
    return SyncASGITestClient(app)


def _assert_503_contract(resp, missing_config):
    """The structured 503 stub shape #33 requires us to keep."""
    assert resp.status_code == 503
    detail = resp.json()["detail"]
    assert detail["error"] == "managed_agents_unavailable"
    assert detail["planned_update"] is True
    assert detail["missing_config"] == missing_config
    assert "future update" in detail["message"]


# ---------------------------------------------------------------------------
# Unconfigured 503 contract — every run endpoint
# ---------------------------------------------------------------------------


class TestUnconfigured503Matrix:
    def test_lead_qualify_503(self):
        client = _client()
        with _settings():
            resp = client.post(
                f"/api/v1/managed-agents/{TENANT}/lead-qualify",
                json=LEAD_QUALIFY_BODY,
            )
        _assert_503_contract(resp, "LEAD_QUALIFIER_AGENT_ID")

    def test_draft_document_503(self):
        client = _client()
        with patch.object(
            mar,
            "draft_document",
            side_effect=ManagedAgentNotConfigured("DOCUMENT_DRAFTER_AGENT_ID"),
        ):
            resp = client.post(
                f"/api/v1/managed-agents/{TENANT}/draft-document",
                json=DRAFT_BODY,
            )
        _assert_503_contract(resp, "DOCUMENT_DRAFTER_AGENT_ID")

    def test_support_query_503(self):
        client = _client()
        with patch.object(
            mar,
            "run_support_query",
            side_effect=ManagedAgentNotConfigured("SUPPORT_AGENT_ID"),
        ):
            resp = client.post(
                f"/api/v1/managed-agents/{TENANT}/support-query",
                json=SUPPORT_BODY,
            )
        _assert_503_contract(resp, "SUPPORT_AGENT_ID")

    def test_extract_503(self):
        client = _client()
        with patch.object(
            mar,
            "extract_structured",
            side_effect=ManagedAgentNotConfigured("STRUCTURED_EXTRACTOR_AGENT_ID"),
        ):
            resp = client.post(
                f"/api/v1/managed-agents/{TENANT}/extract",
                json=EXTRACT_BODY,
            )
        _assert_503_contract(resp, "STRUCTURED_EXTRACTOR_AGENT_ID")

    def test_lead_qualify_503_missing_environment_only(self):
        """Agent ID set but environment unset → 503 names the env var."""
        client = _client()
        with _settings(lead_qualifier_agent_id="agent_1"):
            resp = client.post(
                f"/api/v1/managed-agents/{TENANT}/lead-qualify",
                json=LEAD_QUALIFY_BODY,
            )
        _assert_503_contract(resp, "MANAGED_AGENTS_ENVIRONMENT_ID")


# ---------------------------------------------------------------------------
# Health — "planned" until provisioned, "configured" after
# ---------------------------------------------------------------------------


class TestHealthPlannedState:
    def test_public_health_planned_when_unconfigured(self):
        client = _client()
        with _settings():
            resp = client.get("/api/v1/managed-agents/health")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["status"] == "ok"
        assert payload["managed_agents_status"] == "planned"
        assert payload["any_configured"] is False
        assert payload["environment"] is False
        assert payload["lead_qualifier"] is False

    def test_public_health_configured_when_one_agent_set(self):
        client = _client()
        with _settings(
            managed_agents_environment_id="env_1",
            lead_qualifier_agent_id="agent_1",
        ):
            resp = client.get("/api/v1/managed-agents/health")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["managed_agents_status"] == "configured"
        assert payload["any_configured"] is True
        assert payload["lead_qualifier"] is True
        assert payload["document_drafter"] is False

    def test_authed_health_planned(self):
        client = _client()
        with _settings():
            resp = client.get(f"/api/v1/managed-agents/{TENANT}/health")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["status"] == "planned"
        assert payload["any_configured"] is False

    def test_authed_health_wrong_tenant_403(self):
        client = _client()
        resp = client.get(
            "/api/v1/managed-agents/22222222-2222-2222-2222-222222222222/health"
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Tenant isolation — path tenant must match claims
# ---------------------------------------------------------------------------


class TestTenantIsolation:
    OTHER = "22222222-2222-2222-2222-222222222222"

    @pytest.mark.parametrize(
        "path,body",
        [
            ("lead-qualify", LEAD_QUALIFY_BODY),
            ("draft-document", DRAFT_BODY),
            ("support-query", SUPPORT_BODY),
            ("extract", EXTRACT_BODY),
        ],
    )
    def test_run_endpoints_403_for_other_tenant(self, path, body):
        client = _client()
        resp = client.post(
            f"/api/v1/managed-agents/{self.OTHER}/{path}", json=body,
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Not authorized for this tenant"


# ---------------------------------------------------------------------------
# Run-log wiring — success + unavailable paths record; contract unchanged
# ---------------------------------------------------------------------------


class TestRunLogWiring:
    def test_lead_qualify_success_records_run(self):
        client = _client()
        terminal = SessionTerminalState(
            terminated=True,
            stop_reason_type=None,
            last_event_id="evt_1",
            session_id="sess_1",
        )
        transcript = [{"role": "assistant", "content": [], "id": "msg_1"}]
        with _settings(
            managed_agents_environment_id="env_1",
            lead_qualifier_agent_id="agent_1",
        ), patch.object(mar, "ManagedAgentsClient"), patch.object(
            mar, "_qualify_lead_blocking", return_value=(terminal, transcript),
        ), patch.object(mar, "record_run") as mock_record:
            resp = client.post(
                f"/api/v1/managed-agents/{TENANT}/lead-qualify",
                json=LEAD_QUALIFY_BODY,
            )

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["session_id"] == "sess_1"
        assert payload["terminated"] is True

        mock_record.assert_called_once()
        args, kwargs = mock_record.call_args
        assert args[0] == TENANT
        assert args[1] == "lead_qualifier"
        assert args[2] == "success"
        assert isinstance(kwargs["duration_ms"], int)
        assert kwargs["duration_ms"] >= 0
        assert kwargs["request_summary"] == "lead-qualify"

    def test_lead_qualify_unavailable_records_run(self):
        client = _client()
        with _settings(), patch.object(mar, "record_run") as mock_record:
            resp = client.post(
                f"/api/v1/managed-agents/{TENANT}/lead-qualify",
                json=LEAD_QUALIFY_BODY,
            )

        _assert_503_contract(resp, "LEAD_QUALIFIER_AGENT_ID")
        mock_record.assert_called_once_with(
            TENANT, "lead_qualifier", "unavailable",
            error="LEAD_QUALIFIER_AGENT_ID",
        )

    def test_lead_qualify_upstream_error_returns_502_without_success_log(self):
        client = _client()
        with _settings(
            managed_agents_environment_id="env_1",
            lead_qualifier_agent_id="agent_1",
        ), patch.object(mar, "ManagedAgentsClient"), patch.object(
            mar,
            "_qualify_lead_blocking",
            side_effect=ManagedAgentsError("upstream down", status=500),
        ), patch.object(mar, "record_run") as mock_record:
            resp = client.post(
                f"/api/v1/managed-agents/{TENANT}/lead-qualify",
                json=LEAD_QUALIFY_BODY,
            )

        assert resp.status_code == 502
        mock_record.assert_not_called()

    def test_draft_document_success_records_run(self):
        client = _client()
        persisted = {
            "id": "doc_1",
            "title": "Quote — Bob Vance",
            "kind": "quote",
            "file_type": "docx",
            "file_name": "quote.docx",
            "draft_metadata": {"file_size_bytes": 1234},
        }
        with patch.object(
            mar, "draft_document", return_value=persisted,
        ), patch.object(mar, "record_run") as mock_record:
            resp = client.post(
                f"/api/v1/managed-agents/{TENANT}/draft-document",
                json=DRAFT_BODY,
            )

        assert resp.status_code == 200
        assert resp.json()["document_id"] == "doc_1"
        args, kwargs = mock_record.call_args
        assert args[:3] == (TENANT, "document_drafter", "success")
        assert kwargs["request_summary"] == "draft-document quote"

    def test_draft_document_unavailable_records_run(self):
        client = _client()
        with patch.object(
            mar,
            "draft_document",
            side_effect=ManagedAgentNotConfigured("DOCUMENT_DRAFTER_AGENT_ID"),
        ), patch.object(mar, "record_run") as mock_record:
            resp = client.post(
                f"/api/v1/managed-agents/{TENANT}/draft-document",
                json=DRAFT_BODY,
            )

        _assert_503_contract(resp, "DOCUMENT_DRAFTER_AGENT_ID")
        mock_record.assert_called_once_with(
            TENANT, "document_drafter", "unavailable",
            error="DOCUMENT_DRAFTER_AGENT_ID",
        )

    def test_support_query_success_records_run(self):
        client = _client()
        result = {"answer": "Reset via dashboard.", "confidence": "high",
                  "escalate_reason": None}
        with patch.object(
            mar, "run_support_query", return_value=result,
        ), patch.object(mar, "record_run") as mock_record:
            resp = client.post(
                f"/api/v1/managed-agents/{TENANT}/support-query",
                json=SUPPORT_BODY,
            )

        assert resp.status_code == 200
        assert resp.json()["answer"] == "Reset via dashboard."
        args, kwargs = mock_record.call_args
        assert args[:3] == (TENANT, "support_agent", "success")
        assert kwargs["request_summary"] == "support-query"

    def test_extract_success_records_run(self):
        client = _client()
        with patch.object(
            mar, "extract_structured", return_value={"name": "Bob Vance"},
        ), patch.object(mar, "record_run") as mock_record:
            resp = client.post(
                f"/api/v1/managed-agents/{TENANT}/extract",
                json=EXTRACT_BODY,
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == {"name": "Bob Vance"}
        args, kwargs = mock_record.call_args
        assert args[:3] == (TENANT, "structured_extractor", "success")
        assert kwargs["request_summary"] == "extract lead"

    def test_run_log_failure_never_breaks_success_response(self):
        """record_run is fail-open in the service; even a mock that returns
        False must leave the 200 untouched."""
        client = _client()
        with patch.object(
            mar, "extract_structured", return_value={"name": "Bob"},
        ), patch.object(mar, "record_run", return_value=False):
            resp = client.post(
                f"/api/v1/managed-agents/{TENANT}/extract",
                json=EXTRACT_BODY,
            )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# managed_agent_run_log service — mock supabase
# ---------------------------------------------------------------------------


def _mock_db():
    db = MagicMock()
    db.table.return_value.insert.return_value.execute.return_value = MagicMock()
    return db


class TestRunLogService:
    def test_success_inserts_expected_row(self):
        db = _mock_db()
        ok = run_log.record_run(
            TENANT, "lead_qualifier", "success",
            tokens_in=100, tokens_out=200, duration_ms=1500,
            request_summary="lead-qualify", db=db,
        )
        assert ok is True
        db.table.assert_called_once_with("managed_agent_runs")
        payload = db.table.return_value.insert.call_args.args[0]
        assert payload == {
            "tenant_id": TENANT,
            "agent_key": "lead_qualifier",
            "status": "success",
            "tokens_in": 100,
            "tokens_out": 200,
            "duration_ms": 1500,
            "request_summary": "lead-qualify",
            "error": None,
        }

    def test_unavailable_row_carries_error(self):
        db = _mock_db()
        ok = run_log.record_run(
            TENANT, "support_agent", "unavailable",
            error="SUPPORT_AGENT_ID", db=db,
        )
        assert ok is True
        payload = db.table.return_value.insert.call_args.args[0]
        assert payload["status"] == "unavailable"
        assert payload["error"] == "SUPPORT_AGENT_ID"
        assert payload["tokens_in"] == 0
        assert payload["duration_ms"] == 0

    def test_db_failure_is_fail_open(self):
        db = MagicMock()
        db.table.side_effect = Exception("relation does not exist")
        ok = run_log.record_run(TENANT, "lead_qualifier", "error",
                                error="boom", db=db)
        assert ok is False  # logged + swallowed, never raised

    def test_invalid_status_rejected_before_db(self):
        db = _mock_db()
        ok = run_log.record_run(TENANT, "lead_qualifier", "exploded", db=db)
        assert ok is False
        db.table.assert_not_called()

    def test_testing_short_circuit_skips_db(self):
        assert os.environ.get("TESTING") == "1"
        with patch(
            "backend.models.database.get_service_supabase"
        ) as mock_get_db:
            ok = run_log.record_run(TENANT, "lead_qualifier", "success")
        assert ok is True
        mock_get_db.assert_not_called()

    def test_long_fields_truncated(self):
        db = _mock_db()
        run_log.record_run(
            TENANT, "lead_qualifier", "error",
            request_summary="s" * 2000, error="e" * 5000, db=db,
        )
        payload = db.table.return_value.insert.call_args.args[0]
        assert len(payload["request_summary"]) == 500
        assert len(payload["error"]) == 2000


# ---------------------------------------------------------------------------
# Plan gate interaction — chatbot plan blocked from document drafting
# ---------------------------------------------------------------------------


class TestChatbotPlanGate:
    def _tenant_db(self, plan):
        db = MagicMock()
        result = MagicMock()
        result.data = [{
            "id": TENANT,
            "business_name": "Vance Refrigeration",
            "business_phone": None,
            "business_address": None,
            "plan": plan,
        }]
        (
            db.table.return_value.select.return_value.eq.return_value
            .limit.return_value.execute.return_value
        ) = result
        return db

    def test_chatbot_plan_blocked_by_drafting_service(self):
        """The service-level gate fires before any agent handle is resolved."""
        db = self._tenant_db("chatbot")
        with patch(
            "backend.services.document_drafting.get_service_supabase",
            return_value=db,
        ):
            with pytest.raises(DocumentDraftingError) as excinfo:
                draft_document(
                    tenant_id=TENANT,
                    lead_id=None,
                    kind="quote",
                    customer={"name": "Bob Vance"},
                    line_items=[{"description": "x", "qty": 1, "unit_price": 2}],
                )
        assert "not eligible" in str(excinfo.value)

    def test_agent_os_plan_passes_gate_then_hits_config_check(self):
        """agent_os clears the plan gate; next stop is the (unset) agent
        handle, which surfaces as a DocumentDraftingError pointing at the
        provision script — proving the gate itself did not block."""
        db = self._tenant_db("agent_os")
        with patch(
            "backend.services.document_drafting.get_service_supabase",
            return_value=db,
        ), _settings():
            with pytest.raises(DocumentDraftingError) as excinfo:
                draft_document(
                    tenant_id=TENANT,
                    lead_id=None,
                    kind="quote",
                    customer={"name": "Bob Vance"},
                    line_items=[{"description": "x", "qty": 1, "unit_price": 2}],
                )
        message = str(excinfo.value)
        assert "not eligible" not in message
        assert "DOCUMENT_DRAFTER_AGENT_ID" in message

    def test_router_maps_plan_gate_to_400(self):
        client = _client()
        with patch.object(
            mar,
            "draft_document",
            side_effect=DocumentDraftingError(
                "plan 'chatbot' is not eligible for document drafting"
            ),
        ):
            resp = client.post(
                f"/api/v1/managed-agents/{TENANT}/draft-document",
                json=DRAFT_BODY,
            )
        assert resp.status_code == 400
        assert "not eligible" in resp.json()["detail"]
