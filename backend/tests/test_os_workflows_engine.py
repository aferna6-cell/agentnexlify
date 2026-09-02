"""M9.2 deterministic workflow engine + persistence tests."""

import pytest

from backend.services.os_workflows import (
    ConcurrentModification,
    InMemoryWorkflowStore,
    InvalidWorkflowTransition,
    WorkflowEngine,
    WorkflowGraphError,
    WorkflowStoreError,
    compute_ready_step_ids,
    validate_dependency_graph,
)


CLIENT = "11111111-1111-1111-1111-111111111111"


def _engine():
    return WorkflowEngine(InMemoryWorkflowStore())


def test_rejects_missing_dependency():
    with pytest.raises(WorkflowGraphError, match="missing dependency"):
        validate_dependency_graph(
            [
                {"id": "a", "dependencies": ["missing"], "state": "planned"},
            ]
        )


def test_rejects_cycle():
    with pytest.raises(WorkflowGraphError, match="cycle"):
        validate_dependency_graph(
            [
                {"id": "a", "dependencies": ["b"], "state": "planned"},
                {"id": "b", "dependencies": ["a"], "state": "planned"},
            ]
        )


def test_create_marks_root_ready_and_blocks_dependents():
    eng = _engine()
    wf = eng.create(
        client_id=CLIENT,
        owner_goal="Follow up unpaid invoices",
        steps=[
            {
                "id": "list",
                "description": "List unpaid >30d",
                "risk_level": 0,
            },
            {
                "id": "email",
                "description": "Email debtors",
                "risk_level": 2,
                "dependencies": ["list"],
            },
        ],
    )
    by_id = {s["id"]: s for s in wf["steps"]}
    assert by_id["list"]["state"] == "ready"
    assert by_id["email"]["state"] == "planned"
    assert wf["status"] in {"planned", "running"}


def test_l2_queues_to_pending_approval_and_pauses_workflow():
    eng = _engine()
    wf = eng.create(
        client_id=CLIENT,
        owner_goal="Send reminder",
        steps=[{"id": "s1", "description": "Email", "risk_level": 2}],
    )
    queued = eng.queue_ready_for_execution(CLIENT, wf["id"])
    assert queued[0]["state"] == "pending_approval"
    refreshed = eng.recover(CLIENT, wf["id"])
    assert refreshed["status"] == "paused"


def test_l0_queues_to_running_without_approval():
    eng = _engine()
    wf = eng.create(
        client_id=CLIENT,
        owner_goal="Read invoices",
        steps=[{"id": "s1", "description": "List", "risk_level": 0}],
    )
    queued = eng.queue_ready_for_execution(CLIENT, wf["id"])
    assert queued[0]["state"] == "running"


def test_approve_then_succeed_unlocks_dependent():
    eng = _engine()
    wf = eng.create(
        client_id=CLIENT,
        owner_goal="Invoice follow-up",
        steps=[
            {"id": "list", "description": "List", "risk_level": 0},
            {
                "id": "email",
                "description": "Email",
                "risk_level": 2,
                "dependencies": ["list"],
            },
        ],
    )
    eng.queue_ready_for_execution(CLIENT, wf["id"])
    eng.record_running_outcome(CLIENT, "list", outcome="succeeded")
    steps = eng.recover(CLIENT, wf["id"])["steps"]
    by_id = {s["id"]: s for s in steps}
    assert by_id["list"]["state"] == "succeeded"
    assert by_id["email"]["state"] == "ready"

    eng.queue_ready_for_execution(CLIENT, wf["id"])
    eng.approve_step(CLIENT, "email")
    eng.record_running_outcome(
        CLIENT, "email", outcome="succeeded", execution_id="exec-1"
    )
    done = eng.recover(CLIENT, wf["id"])
    assert done["status"] == "succeeded"
    assert {s["state"] for s in done["steps"]} == {"succeeded"}


def test_cas_rejects_stale_version():
    store = InMemoryWorkflowStore()
    eng = WorkflowEngine(store)
    wf = eng.create(
        client_id=CLIENT,
        owner_goal="x",
        steps=[{"id": "s1", "description": "y", "risk_level": 1}],
    )
    step = wf["steps"][0]
    store.transition_step_cas(
        client_id=CLIENT,
        step_id=step["id"],
        expected_state="ready",
        expected_version=int(step["row_version"]),
        target_state="running",
        risk_level=1,
    )
    with pytest.raises(ConcurrentModification):
        store.transition_step_cas(
            client_id=CLIENT,
            step_id=step["id"],
            expected_state="ready",
            expected_version=int(step["row_version"]),
            target_state="running",
            risk_level=1,
        )


def test_bounded_retry_for_failed():
    eng = _engine()
    wf = eng.create(
        client_id=CLIENT,
        owner_goal="x",
        steps=[{"id": "s1", "description": "y", "risk_level": 1, "max_retries": 1}],
    )
    eng.queue_ready_for_execution(CLIENT, wf["id"])
    eng.record_running_outcome(CLIENT, "s1", outcome="failed", error="boom")
    retried = eng.retry_failed_step(CLIENT, "s1")
    assert retried["state"] == "ready"
    assert retried["retry_count"] == 1
    eng.queue_ready_for_execution(CLIENT, wf["id"])
    eng.record_running_outcome(CLIENT, "s1", outcome="failed", error="boom2")
    with pytest.raises(WorkflowStoreError, match="exhausted retries"):
        eng.retry_failed_step(CLIENT, "s1")


def test_l2_unknown_not_replayable():
    eng = _engine()
    wf = eng.create(
        client_id=CLIENT,
        owner_goal="x",
        steps=[{"id": "s1", "description": "email", "risk_level": 2}],
    )
    eng.queue_ready_for_execution(CLIENT, wf["id"])
    eng.approve_step(CLIENT, "s1")
    eng.record_running_outcome(CLIENT, "s1", outcome="unknown")
    with pytest.raises(InvalidWorkflowTransition):
        eng.retry_failed_step(CLIENT, "s1")
    cancelled = eng.cancel_unknown_l2(CLIENT, "s1")
    assert cancelled["state"] == "cancelled"


def test_l0_unknown_may_recover():
    eng = _engine()
    wf = eng.create(
        client_id=CLIENT,
        owner_goal="x",
        steps=[{"id": "s1", "description": "read", "risk_level": 0}],
    )
    eng.queue_ready_for_execution(CLIENT, wf["id"])
    eng.record_running_outcome(CLIENT, "s1", outcome="unknown")
    recovered = eng.retry_failed_step(CLIENT, "s1")
    assert recovered["state"] == "ready"


def test_restart_recovery_is_idempotent():
    eng = _engine()
    wf = eng.create(
        client_id=CLIENT,
        owner_goal="x",
        steps=[
            {"id": "a", "description": "A", "risk_level": 0},
            {"id": "b", "description": "B", "risk_level": 0, "dependencies": ["a"]},
        ],
    )
    first = eng.recover(CLIENT, wf["id"])
    second = eng.recover(CLIENT, wf["id"])
    assert {s["id"]: s["state"] for s in first["steps"]} == {
        s["id"]: s["state"] for s in second["steps"]
    }


def test_compute_ready_helper():
    steps = [
        {"id": "a", "dependencies": [], "state": "succeeded"},
        {"id": "b", "dependencies": ["a"], "state": "planned"},
        {"id": "c", "dependencies": ["b"], "state": "planned"},
    ]
    assert compute_ready_step_ids(steps) == ["b"]


def test_cross_tenant_get_is_none():
    store = InMemoryWorkflowStore()
    eng = WorkflowEngine(store)
    wf = eng.create(
        client_id=CLIENT,
        owner_goal="x",
        steps=[{"id": "s1", "description": "y", "risk_level": 0}],
    )
    assert store.get_workflow("other-tenant", wf["id"]) is None
    assert store.get_step("other-tenant", "s1") is None
