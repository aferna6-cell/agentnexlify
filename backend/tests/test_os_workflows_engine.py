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
    eng.record_running_outcome(
        CLIENT, "list", outcome="succeeded", verification_state="passed"
    )
    steps = eng.recover(CLIENT, wf["id"])["steps"]
    by_id = {s["id"]: s for s in steps}
    assert by_id["list"]["state"] == "succeeded"
    assert by_id["email"]["state"] == "ready"

    eng.queue_ready_for_execution(CLIENT, wf["id"])
    eng.approve_step(CLIENT, "email")
    eng.record_running_outcome(
        CLIENT,
        "email",
        outcome="succeeded",
        execution_id="exec-1",
        verification_state="passed",
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


def test_reject_step_cancels_pending_approval():
    eng = _engine()
    wf = eng.create(
        client_id=CLIENT,
        owner_goal="x",
        steps=[{"id": "s1", "description": "email", "risk_level": 2}],
    )
    eng.queue_ready_for_execution(CLIENT, wf["id"])
    rejected = eng.reject_step(CLIENT, "s1", reason="owner said no")
    assert rejected["state"] == "cancelled"
    assert rejected["error"] == "owner said no"


def test_verifying_then_failed_outcome():
    eng = _engine()
    wf = eng.create(
        client_id=CLIENT,
        owner_goal="x",
        steps=[{"id": "s1", "description": "y", "risk_level": 0}],
    )
    eng.queue_ready_for_execution(CLIENT, wf["id"])
    mid = eng.record_running_outcome(CLIENT, "s1", outcome="verifying")
    assert mid["state"] == "verifying"
    failed = eng.record_running_outcome(
        CLIENT, "s1", outcome="failed", error="verify miss"
    )
    assert failed["state"] == "failed"


def test_unsupported_outcome_rejected():
    eng = _engine()
    wf = eng.create(
        client_id=CLIENT,
        owner_goal="x",
        steps=[{"id": "s1", "description": "y", "risk_level": 0}],
    )
    eng.queue_ready_for_execution(CLIENT, wf["id"])
    with pytest.raises(WorkflowStoreError, match="unsupported outcome"):
        eng.record_running_outcome(CLIENT, "s1", outcome="exploded")


def test_invalid_outcome_from_ready_raises():
    eng = _engine()
    wf = eng.create(
        client_id=CLIENT,
        owner_goal="x",
        steps=[{"id": "s1", "description": "y", "risk_level": 0}],
    )
    with pytest.raises(InvalidWorkflowTransition):
        eng.record_running_outcome(CLIENT, "s1", outcome="succeeded")


def test_failed_workflow_aggregation():
    eng = _engine()
    wf = eng.create(
        client_id=CLIENT,
        owner_goal="x",
        steps=[{"id": "s1", "description": "y", "risk_level": 1, "max_retries": 0}],
    )
    eng.queue_ready_for_execution(CLIENT, wf["id"])
    eng.record_running_outcome(CLIENT, "s1", outcome="failed")
    with pytest.raises(WorkflowStoreError, match="exhausted retries"):
        eng.retry_failed_step(CLIENT, "s1")
    done = eng.recover(CLIENT, wf["id"])
    assert done["status"] == "failed"


def test_all_cancelled_aggregates():
    from backend.services.os_workflows.engine import derive_workflow_status

    assert derive_workflow_status([]) == "planned"
    assert (
        derive_workflow_status(
            [{"state": "cancelled"}, {"state": "cancelled"}]
        )
        == "cancelled"
    )
    assert (
        derive_workflow_status(
            [{"state": "succeeded"}, {"state": "cancelled"}]
        )
        == "succeeded"
    )


def test_self_dependency_rejected():
    with pytest.raises(WorkflowGraphError, match="itself"):
        validate_dependency_graph(
            [{"id": "a", "dependencies": ["a"], "state": "planned"}]
        )


def test_missing_workflow_and_step_errors():
    eng = _engine()
    with pytest.raises(WorkflowStoreError, match="workflow"):
        eng.recover(CLIENT, "00000000-0000-0000-0000-000000000000")
    with pytest.raises(WorkflowStoreError, match="step"):
        eng.approve_step(CLIENT, "00000000-0000-0000-0000-000000000000")


def test_inmemory_duplicate_ids_and_patch():
    store = InMemoryWorkflowStore()
    store.create_workflow(
        client_id=CLIENT,
        owner_goal="x",
        steps=[{"id": "s1", "description": "y"}],
        workflow_id="wf1",
    )
    with pytest.raises(WorkflowStoreError, match="already exists"):
        store.create_workflow(
            client_id=CLIENT,
            owner_goal="x",
            steps=[{"id": "s2", "description": "y"}],
            workflow_id="wf1",
        )
    with pytest.raises(WorkflowStoreError, match="already exists"):
        store.create_workflow(
            client_id=CLIENT,
            owner_goal="z",
            steps=[{"id": "s1", "description": "y"}],
            workflow_id="wf2",
        )
    patched = store.patch_step(
        client_id=CLIENT,
        step_id="s1",
        expected_version=1,
        patch={"error": "note", "id": "ignored"},
    )
    assert patched["error"] == "note"
    assert patched["id"] == "s1"
    with pytest.raises(ConcurrentModification):
        store.patch_step(
            client_id=CLIENT,
            step_id="s1",
            expected_version=1,
            patch={"error": "stale"},
        )


def test_supabase_store_cas_roundtrip():
    from backend.services.os_workflows.store import SupabaseWorkflowStore
    from backend.services.tenant_scope import tenant_scope_column
    from backend.tests.fake_supabase_store import FakeSupabase

    assert tenant_scope_column("os_workflows") == "client_id"
    assert tenant_scope_column("os_workflow_steps") == "client_id"

    db = FakeSupabase({"os_workflows": [], "os_workflow_steps": []})
    store = SupabaseWorkflowStore(db)
    created = store.create_workflow(
        client_id=CLIENT,
        owner_goal="goal",
        steps=[
            {
                "id": "s1",
                "description": "step",
                "risk_level": 2,
                "tool_intent": {"tool_name": "send_email", "arguments": {}},
            }
        ],
        workflow_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    )
    assert created["id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert store.get_workflow(CLIENT, created["id"])["owner_goal"] == "goal"
    assert store.get_workflow("other", created["id"]) is None
    steps = store.list_steps(CLIENT, created["id"])
    assert len(steps) == 1
    step = store.get_step(CLIENT, "s1")
    assert step["risk_level"] == 2

    moved = store.transition_step_cas(
        client_id=CLIENT,
        step_id="s1",
        expected_state="planned",
        expected_version=1,
        target_state="ready",
        risk_level=2,
    )
    assert moved["state"] == "ready"
    assert moved["row_version"] == 2

    with pytest.raises(ConcurrentModification):
        store.transition_step_cas(
            client_id=CLIENT,
            step_id="s1",
            expected_state="planned",
            expected_version=1,
            target_state="ready",
            risk_level=2,
        )

    wf = store.transition_workflow_cas(
        client_id=CLIENT,
        workflow_id=created["id"],
        expected_status="planned",
        expected_version=1,
        target_status="running",
    )
    assert wf["status"] == "running"
    with pytest.raises(ConcurrentModification):
        store.transition_workflow_cas(
            client_id=CLIENT,
            workflow_id=created["id"],
            expected_status="planned",
            expected_version=1,
            target_status="running",
        )

    patched = store.patch_step(
        client_id=CLIENT,
        step_id="s1",
        expected_version=2,
        patch={"error": "holding", "state": "should-ignore"},
    )
    assert patched["error"] == "holding"
    assert patched["state"] == "ready"
    with pytest.raises(ConcurrentModification):
        store.patch_step(
            client_id=CLIENT,
            step_id="s1",
            expected_version=2,
            patch={"error": "stale"},
        )

    assert store.get_step(CLIENT, "missing") is None


def test_retryable_failure_keeps_workflow_running():
    """First failure with retries remaining must not terminalize the workflow."""
    eng = _engine()
    wf = eng.create(
        client_id=CLIENT,
        owner_goal="x",
        steps=[{"id": "s1", "description": "y", "risk_level": 1, "max_retries": 2}],
    )
    eng.queue_ready_for_execution(CLIENT, wf["id"])
    eng.record_running_outcome(CLIENT, "s1", outcome="failed", error="boom")
    mid = eng.recover(CLIENT, wf["id"])
    assert mid["status"] == "running"
    by_id = {s["id"]: s for s in mid["steps"]}
    assert by_id["s1"]["state"] == "failed"
    assert by_id["s1"]["retry_count"] == 0
    assert by_id["s1"]["max_retries"] == 2


def test_exhausted_failure_marks_workflow_failed():
    eng = _engine()
    wf = eng.create(
        client_id=CLIENT,
        owner_goal="x",
        steps=[{"id": "s1", "description": "y", "risk_level": 1, "max_retries": 1}],
    )
    eng.queue_ready_for_execution(CLIENT, wf["id"])
    eng.record_running_outcome(CLIENT, "s1", outcome="failed", error="boom")
    assert eng.recover(CLIENT, wf["id"])["status"] == "running"
    eng.retry_failed_step(CLIENT, "s1")
    eng.queue_ready_for_execution(CLIENT, wf["id"])
    eng.record_running_outcome(CLIENT, "s1", outcome="failed", error="boom2")
    done = eng.recover(CLIENT, wf["id"])
    assert done["status"] == "failed"
    with pytest.raises(WorkflowStoreError, match="exhausted retries"):
        eng.retry_failed_step(CLIENT, "s1")


def test_execution_success_without_verifier_stays_verifying():
    eng = _engine()
    wf = eng.create(
        client_id=CLIENT,
        owner_goal="x",
        steps=[{"id": "s1", "description": "y", "risk_level": 0}],
    )
    eng.queue_ready_for_execution(CLIENT, wf["id"])
    mid = eng.record_running_outcome(CLIENT, "s1", outcome="succeeded")
    assert mid["state"] == "verifying"
    assert mid["verification_state"] == "pending"
    refreshed = eng.recover(CLIENT, wf["id"])
    assert refreshed["status"] == "running"
    assert refreshed["steps"][0]["state"] == "verifying"


def test_explicit_verification_pass_succeeds():
    eng = _engine()
    wf = eng.create(
        client_id=CLIENT,
        owner_goal="x",
        steps=[{"id": "s1", "description": "y", "risk_level": 0}],
    )
    eng.queue_ready_for_execution(CLIENT, wf["id"])
    mid = eng.record_running_outcome(CLIENT, "s1", outcome="succeeded")
    assert mid["state"] == "verifying"
    done = eng.record_running_outcome(
        CLIENT, "s1", outcome="succeeded", verification_state="passed"
    )
    assert done["state"] == "succeeded"
    assert done["verification_state"] == "passed"
    assert eng.recover(CLIENT, wf["id"])["status"] == "succeeded"


def test_not_required_verification_can_succeed_inline():
    eng = _engine()
    wf = eng.create(
        client_id=CLIENT,
        owner_goal="x",
        steps=[{"id": "s1", "description": "y", "risk_level": 0}],
    )
    eng.queue_ready_for_execution(CLIENT, wf["id"])
    done = eng.record_running_outcome(
        CLIENT, "s1", outcome="succeeded", verification_state="not_required"
    )
    assert done["state"] == "succeeded"
    assert done["verification_state"] == "not_required"


def test_l0_unknown_cannot_exceed_max_retries():
    eng = _engine()
    wf = eng.create(
        client_id=CLIENT,
        owner_goal="x",
        steps=[{"id": "s1", "description": "read", "risk_level": 0, "max_retries": 1}],
    )
    eng.queue_ready_for_execution(CLIENT, wf["id"])
    eng.record_running_outcome(CLIENT, "s1", outcome="unknown")
    recovered = eng.retry_failed_step(CLIENT, "s1")
    assert recovered["state"] == "ready"
    assert recovered["retry_count"] == 1
    eng.queue_ready_for_execution(CLIENT, wf["id"])
    eng.record_running_outcome(CLIENT, "s1", outcome="unknown")
    with pytest.raises(WorkflowStoreError, match="exhausted retries"):
        eng.retry_failed_step(CLIENT, "s1")


def test_cross_tenant_workflow_step_pair_rejected():
    from backend.tests.fake_supabase_store import FakeSupabase

    db = FakeSupabase({"os_workflows": [], "os_workflow_steps": []})
    wf = db.rpc(
        "create_os_workflow",
        {
            "p_client_id": CLIENT,
            "p_owner_goal": "goal",
            "p_steps": [{"id": "s1", "description": "ok"}],
            "p_workflow_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        },
    ).execute().data[0]
    other = "22222222-2222-2222-2222-222222222222"
    with pytest.raises(RuntimeError, match="workflow_client_fkey"):
        db.insert_step_enforcing_tenant_fk(
            {
                "id": "s-cross",
                "workflow_id": wf["id"],
                "client_id": other,
                "ordinal": 1,
                "description": "cross-tenant",
                "state": "planned",
            }
        )


def test_failed_step_insert_leaves_no_partial_workflow():
    from backend.services.os_workflows.store import SupabaseWorkflowStore
    from backend.tests.fake_supabase_store import FakeSupabase

    db = FakeSupabase({"os_workflows": [], "os_workflow_steps": []})
    db.fail_create_os_workflow = True
    store = SupabaseWorkflowStore(db)
    with pytest.raises(WorkflowStoreError, match="atomic create_os_workflow"):
        store.create_workflow(
            client_id=CLIENT,
            owner_goal="goal",
            steps=[
                {"id": "s1", "description": "one"},
                {"id": "s2", "description": "two"},
            ],
            workflow_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
        )
    assert db.rows("os_workflows") == []
    assert db.rows("os_workflow_steps") == []


def test_inmemory_create_is_atomic_on_duplicate_step():
    store = InMemoryWorkflowStore()
    store.create_workflow(
        client_id=CLIENT,
        owner_goal="first",
        steps=[{"id": "keep", "description": "ok"}],
        workflow_id="dddddddd-dddd-dddd-dddd-dddddddddddd",
    )
    with pytest.raises(WorkflowStoreError, match="already exists"):
        store.create_workflow(
            client_id=CLIENT,
            owner_goal="second",
            steps=[
                {"id": "new", "description": "ok"},
                {"id": "keep", "description": "dup"},
            ],
            workflow_id="eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        )
    assert store.get_workflow(CLIENT, "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee") is None
    assert store.get_step(CLIENT, "new") is None
    assert store.get_step(CLIENT, "keep") is not None
