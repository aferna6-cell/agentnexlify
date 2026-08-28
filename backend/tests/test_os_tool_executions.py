"""Data-plane tests for the Agent OS action layer.

The engine owns the tool registry, the risk policy and the executor (tested in
``agent-service/src/agent-os/actions/*.test.ts``). These tests cover the half
that lives here: persisting the audit trail, applying an action's internal
writes and verifying them against the database, and the approval pathway —
where "approve runs it exactly once" is actually enforced.
"""

import os
from unittest.mock import patch

os.environ.setdefault("TESTING", "1")

import pytest

from backend.dependencies import _get_current_tenant
from backend.main import app
from backend.routers import os_tool_executions as router_mod
from backend.services import os_tool_executions as svc
from backend.services.agent_os_gate import require_agent_os_access
from backend.tests.conftest import SyncASGITestClient
from backend.tests.fake_supabase_store import FakeSupabase

CLIENT = "11111111-1111-1111-1111-111111111111"
EXEC_ID = "22222222-2222-2222-2222-222222222222"
RUN_ID = "33333333-3333-3333-3333-333333333333"
OWNER_CLAIMS = {"tenant_id": CLIENT, "role": "owner", "email": "maya@sunsetauto.test"}
STAFF_CLAIMS = {"tenant_id": CLIENT, "role": "staff", "email": "sam@sunsetauto.test"}


def _execution(**overrides):
    """One engine execution record, as /orchestrate returns it."""
    record = {
        "id": EXEC_ID,
        "accountId": CLIENT,
        "runId": "engine_run_1",
        "agentId": "admin_records",
        "toolId": "add_customer_note",
        "riskLevel": 1,
        "mutating": True,
        "requiresApproval": False,
        "approvalState": "not_required",
        "status": "succeeded",
        "input": {"customer_id": "lead_1", "note": "Prefers texts after 5pm."},
        "result": {"noteId": "note_1", "customerId": "lead_1", "note": "Prefers texts after 5pm."},
        "verificationState": "passed",
        "verificationDetail": "note note_1 confirmed",
        "policyReason": "risk level 1 is below this business's approval threshold (2)",
        "attempts": 1,
        "effect": {"port": "agent_service_bundle", "durable": True},
        "createdAt": "2026-08-28T10:00:00Z",
    }
    record.update(overrides)
    return record


def _note(**overrides):
    note = {
        "id": "note_1",
        "customerId": "lead_1",
        "customerName": "Sarah Chen",
        "note": "Prefers texts after 5pm.",
        "source": "agent:admin_records",
        "createdAt": "2026-08-28T10:00:00Z",
    }
    note.update(overrides)
    return note


def _db_with_lead(notes=None):
    return FakeSupabase(
        {
            "leads": [{"id": "lead_1", "client_id": CLIENT, "name": "Sarah Chen", "notes": notes}],
            "os_tool_executions": [],
        }
    )


# --- persistence -------------------------------------------------------------


def test_persist_writes_an_auditable_row_per_execution():
    db = _db_with_lead()
    record = {"toolExecutions": [_execution()], "customerNotes": [_note()]}

    svc.persist_tool_executions(db, CLIENT, RUN_ID, record)

    rows = db.rows("os_tool_executions")
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == EXEC_ID
    assert row["client_id"] == CLIENT
    assert row["agent_run_id"] == RUN_ID
    assert row["engine_run_id"] == "engine_run_1"
    assert row["tool_id"] == "add_customer_note"
    assert row["risk_level"] == 1
    assert row["status"] == "succeeded"
    assert row["verification_state"] == "passed"
    assert row["input"]["note"] == "Prefers texts after 5pm."
    assert row["effect"] == {"port": "agent_service_bundle", "durable": True}


def test_persist_applies_the_note_to_the_customer_record():
    db = _db_with_lead(notes="Existing note.")
    record = {"toolExecutions": [_execution()], "customerNotes": [_note()]}

    svc.persist_tool_executions(db, CLIENT, RUN_ID, record)

    lead = db.rows("leads")[0]
    assert "Existing note." in lead["notes"]
    assert "Prefers texts after 5pm." in lead["notes"]
    assert "(agent:admin_records)" in lead["notes"]
    assert db.rows("os_tool_executions")[0]["status"] == "succeeded"


def test_a_note_that_cannot_be_applied_downgrades_its_execution():
    """A write that does not land must never remain in the history as success."""
    db = FakeSupabase({"leads": [], "os_tool_executions": []})
    record = {"toolExecutions": [_execution()], "customerNotes": [_note()]}

    svc.persist_tool_executions(db, CLIENT, RUN_ID, record)

    row = db.rows("os_tool_executions")[0]
    assert row["status"] == "verification_failed"
    assert row["verification_state"] == "failed"
    assert "no longer exists" in row["verification_detail"]


def test_persist_is_a_no_op_when_the_turn_used_no_tools():
    db = _db_with_lead()
    assert svc.persist_tool_executions(db, CLIENT, RUN_ID, {"toolExecutions": []}) == []
    assert db.rows("os_tool_executions") == []


def test_an_unknown_risk_level_is_stored_as_the_highest():
    """A record the engine could not classify is never filed as low risk."""
    db = _db_with_lead()
    record = {"toolExecutions": [_execution(riskLevel=None, result=None, customerNotes=None)]}

    svc.persist_tool_executions(db, CLIENT, RUN_ID, record)

    assert db.rows("os_tool_executions")[0]["risk_level"] == 3


# --- the at-most-once claim ----------------------------------------------------


def _pending_db():
    return FakeSupabase(
        {
            "os_tool_executions": [
                {
                    "id": EXEC_ID,
                    "client_id": CLIENT,
                    "tool_id": "add_customer_note",
                    "status": "pending_approval",
                    "approval_state": "pending",
                    "risk_level": 2,
                    "mutating": True,
                    "requires_approval": True,
                    "input": {"customer_id": "lead_1", "note": "Prefers texts."},
                    "policy_reason": "requires approval",
                    "attempts": 0,
                    "created_at": "2026-08-28T10:00:00Z",
                }
            ],
            "leads": [{"id": "lead_1", "client_id": CLIENT, "name": "Sarah Chen", "notes": None}],
        }
    )


def test_only_the_first_claim_wins():
    db = _pending_db()

    first = svc.claim_for_execution(db, CLIENT, EXEC_ID)
    second = svc.claim_for_execution(db, CLIENT, EXEC_ID)

    assert first is not None and first["status"] == "running"
    assert second is None, "a second approval must not claim an already-claimed action"


def test_a_claim_cannot_cross_tenants():
    db = _pending_db()
    assert svc.claim_for_execution(db, "99999999-9999-9999-9999-999999999999", EXEC_ID) is None
    assert db.rows("os_tool_executions")[0]["status"] == "pending_approval"


def test_recording_the_outcome_keeps_the_row_s_identity():
    db = _pending_db()
    svc.claim_for_execution(db, CLIENT, EXEC_ID)

    svc.record_execution_outcome(
        db, CLIENT, _execution(status="succeeded", approvalState="approved", approvedBy="maya@sunsetauto.test")
    )

    row = db.rows("os_tool_executions")[0]
    assert row["status"] == "succeeded"
    assert row["approval_state"] == "approved"
    assert row["approved_by"] == "maya@sunsetauto.test"
    assert row["client_id"] == CLIENT


# --- rejection -----------------------------------------------------------------


def test_rejecting_a_pending_action_denies_it():
    db = _pending_db()

    row = svc.reject_tool_execution(db, CLIENT, EXEC_ID, rejected_by="maya", reason="wrong customer")

    assert row["status"] == "denied"
    assert row["approval_state"] == "rejected"
    assert row["rejection_reason"] == "wrong customer"


def test_rejecting_twice_is_idempotent():
    db = _pending_db()
    svc.reject_tool_execution(db, CLIENT, EXEC_ID, rejected_by="maya")
    again = svc.reject_tool_execution(db, CLIENT, EXEC_ID, rejected_by="maya")
    assert again["status"] == "denied"


def test_an_action_that_already_ran_cannot_be_rejected():
    db = _pending_db()
    svc.claim_for_execution(db, CLIENT, EXEC_ID)
    svc.record_execution_outcome(db, CLIENT, _execution(status="succeeded"))

    with pytest.raises(svc.ToolExecutionStateError) as err:
        svc.reject_tool_execution(db, CLIENT, EXEC_ID, rejected_by="maya")
    assert err.value.status == "succeeded"


def test_rejecting_an_unknown_execution_raises():
    with pytest.raises(LookupError):
        svc.reject_tool_execution(_pending_db(), CLIENT, "no-such-id", rejected_by="maya")


# --- the approval endpoint -------------------------------------------------------


def _client(claims=OWNER_CLAIMS):
    """Authenticated client on a plan that includes Agent OS."""
    app.dependency_overrides[_get_current_tenant] = lambda: claims
    app.dependency_overrides[require_agent_os_access] = lambda: claims
    return SyncASGITestClient(app)


def _teardown():
    app.dependency_overrides.pop(_get_current_tenant, None)
    app.dependency_overrides.pop(require_agent_os_access, None)


def _engine_response(**overrides):
    return {
        "execution": _execution(status="succeeded", approvalState="approved", **overrides),
        "customerNotes": [_note()],
    }


def test_approving_runs_the_action_and_persists_its_outcome():
    db = _pending_db()
    client = _client()
    try:
        with patch.object(router_mod, "get_service_supabase", return_value=db), patch.object(
            router_mod.agent_os_bridge, "assemble_shared_context", return_value={}
        ), patch.object(
            router_mod.agent_sdk_client, "approve_action_sync", return_value=_engine_response()
        ):
            resp = client.post(f"/api/v1/os/tool-executions/{EXEC_ID}/approve")
    finally:
        _teardown()

    assert resp.status_code == 200
    body = resp.json()
    assert body["already_decided"] is False
    assert body["execution"]["status"] == "succeeded"
    assert "Prefers texts after 5pm." in db.rows("leads")[0]["notes"]


def test_approving_twice_does_not_run_the_action_twice():
    db = _pending_db()
    client = _client()
    calls = []

    def _engine(*args, **kwargs):
        calls.append(kwargs.get("approved_by"))
        return _engine_response()

    try:
        with patch.object(router_mod, "get_service_supabase", return_value=db), patch.object(
            router_mod.agent_os_bridge, "assemble_shared_context", return_value={}
        ), patch.object(router_mod.agent_sdk_client, "approve_action_sync", _engine):
            first = client.post(f"/api/v1/os/tool-executions/{EXEC_ID}/approve")
            second = client.post(f"/api/v1/os/tool-executions/{EXEC_ID}/approve")
    finally:
        _teardown()

    assert first.json()["already_decided"] is False
    assert second.json()["already_decided"] is True
    assert len(calls) == 1, "the engine was asked to run the action exactly once"
    assert db.rows("leads")[0]["notes"].count("Prefers texts after 5pm.") == 1


def test_a_rejected_action_is_never_executed_by_a_later_approval():
    db = _pending_db()
    svc.reject_tool_execution(db, CLIENT, EXEC_ID, rejected_by="maya")
    client = _client()
    calls = []

    def _engine(*args, **kwargs):
        calls.append(kwargs.get("approved_by"))
        return _engine_response()

    try:
        with patch.object(router_mod, "get_service_supabase", return_value=db), patch.object(
            router_mod.agent_os_bridge, "assemble_shared_context", return_value={}
        ), patch.object(router_mod.agent_sdk_client, "approve_action_sync", _engine):
            resp = client.post(f"/api/v1/os/tool-executions/{EXEC_ID}/approve")
    finally:
        _teardown()

    assert resp.json()["execution"]["status"] == "denied"
    assert calls == []
    assert db.rows("leads")[0]["notes"] is None


def test_an_unreachable_engine_leaves_the_action_unfinished_rather_than_guessing():
    db = _pending_db()
    client = _client()
    try:
        with patch.object(router_mod, "get_service_supabase", return_value=db), patch.object(
            router_mod.agent_os_bridge, "assemble_shared_context", return_value={}
        ), patch.object(router_mod.agent_sdk_client, "approve_action_sync", return_value=None):
            resp = client.post(f"/api/v1/os/tool-executions/{EXEC_ID}/approve")
    finally:
        _teardown()

    assert resp.status_code == 502
    row = db.rows("os_tool_executions")[0]
    assert row["status"] == "running", "no terminal state is invented for an unknown outcome"
    assert row["error"]["code"] == "engine_unavailable"


def test_only_an_owner_may_approve_or_reject():
    client = _client(STAFF_CLAIMS)
    try:
        with patch.object(router_mod, "get_service_supabase", return_value=_pending_db()):
            approve = client.post(f"/api/v1/os/tool-executions/{EXEC_ID}/approve")
            reject = client.post(f"/api/v1/os/tool-executions/{EXEC_ID}/reject", json={})
    finally:
        _teardown()

    assert approve.status_code == 403
    assert reject.status_code == 403


def test_approving_an_execution_that_does_not_exist_is_a_404():
    client = _client()
    try:
        with patch.object(
            router_mod, "get_service_supabase", return_value=FakeSupabase({"os_tool_executions": []})
        ):
            resp = client.post(f"/api/v1/os/tool-executions/{EXEC_ID}/approve")
    finally:
        _teardown()

    assert resp.status_code == 404


def test_the_history_is_readable_and_filterable():
    db = _pending_db()
    client = _client()
    try:
        with patch.object(router_mod, "get_service_supabase", return_value=db):
            listed = client.get("/api/v1/os/tool-executions?status=pending_approval")
            one = client.get(f"/api/v1/os/tool-executions/{EXEC_ID}")
            bad = client.get("/api/v1/os/tool-executions?status=nonsense")
    finally:
        _teardown()

    assert listed.json()["count"] == 1
    assert listed.json()["items"][0]["tool_id"] == "add_customer_note"
    assert one.json()["id"] == EXEC_ID
    assert bad.status_code == 400
