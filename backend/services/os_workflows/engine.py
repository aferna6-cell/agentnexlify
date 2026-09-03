"""M9.2 deterministic workflow engine — no LLM, no tool execution.

The engine advances durable Workflow / WorkflowStep state. Side effects stay
on the existing Action Executor path; this module only prepares readiness,
enforces approvals, retries eligible failures, and aggregates terminal status.

Non-negotiable: do not import Action Executor, provider, or tool modules here.
CI enforces that boundary via ``check_project_invariants``.
"""

from typing import Any, Dict, List, Optional, Set

from backend.services.os_workflows.contract import (
    RISK_FAIL_CLOSED,
    InvalidWorkflowTransition,
    is_workflow_terminal,
)
from backend.services.os_workflows.store import (
    ConcurrentModification,
    WorkflowStore,
    WorkflowStoreError,
)

DEFAULT_MAX_RETRIES = 2

# Active / non-finished step states that keep a workflow running.
_ACTIVE_STEP_STATES = frozenset(
    {
        "planned",
        "ready",
        "pending_approval",
        "running",
        "verifying",
        "blocked",
        "failed",  # retryable — not yet terminal for aggregation
        "unknown",  # sticky until cancelled (L2/L3) or recovered (L0/L1)
    }
)


class WorkflowGraphError(ValueError):
    """Dependency graph is invalid (missing dep, cycle, cross-workflow)."""


def validate_dependency_graph(steps: List[Dict[str, Any]]) -> None:
    """Reject missing dependencies, self-deps, and cycles."""
    by_id = {str(s["id"]): s for s in steps}
    for step in steps:
        sid = str(step["id"])
        for dep in step.get("dependencies") or []:
            dep_id = str(dep)
            if dep_id == sid:
                raise WorkflowGraphError(f"step {sid} depends on itself")
            if dep_id not in by_id:
                raise WorkflowGraphError(
                    f"step {sid} missing dependency {dep_id}"
                )

    visiting: Set[str] = set()
    visited: Set[str] = set()

    def dfs(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            raise WorkflowGraphError(f"dependency cycle involving {node}")
        visiting.add(node)
        for dep in by_id[node].get("dependencies") or []:
            dfs(str(dep))
        visiting.remove(node)
        visited.add(node)

    for sid in by_id:
        dfs(sid)


def dependencies_satisfied(step: Dict[str, Any], by_id: Dict[str, Dict[str, Any]]) -> bool:
    for dep in step.get("dependencies") or []:
        dep_row = by_id.get(str(dep))
        if dep_row is None or dep_row.get("state") != "succeeded":
            return False
    return True


def compute_ready_step_ids(steps: List[Dict[str, Any]]) -> List[str]:
    """Return planned step ids whose dependencies have all succeeded."""
    validate_dependency_graph(steps)
    by_id = {str(s["id"]): s for s in steps}
    ready = []
    for step in steps:
        if step.get("state") != "planned":
            continue
        if dependencies_satisfied(step, by_id):
            ready.append(str(step["id"]))
    return ready


def _retries_exhausted(step: Dict[str, Any]) -> bool:
    retry_count = int(step.get("retry_count", 0))
    max_retries = int(step.get("max_retries", DEFAULT_MAX_RETRIES))
    return retry_count >= max_retries


def _planned_blocked_by_exhausted_failure(
    step: Dict[str, Any],
    by_id: Dict[str, Dict[str, Any]],
    visiting: Optional[Set[str]] = None,
) -> bool:
    """True when a planned step depends on an exhausted failure (directly or transitively)."""
    sid = str(step.get("id") or "")
    visiting = visiting if visiting is not None else set()
    if sid:
        if sid in visiting:
            return False
        visiting = visiting | {sid}
    for dep_id in step.get("dependencies") or []:
        dep = by_id.get(str(dep_id))
        if dep is None:
            continue
        dep_state = str(dep.get("state"))
        if dep_state == "failed" and _retries_exhausted(dep):
            return True
        if dep_state == "planned" and _planned_blocked_by_exhausted_failure(
            dep, by_id, visiting
        ):
            return True
    return False


def derive_workflow_status(steps: List[Dict[str, Any]]) -> str:
    """Aggregate step states into a workflow status recommendation.

    A ``failed`` step keeps the workflow ``running`` while retries remain.
    Workflow ``failed`` only when every failed step has exhausted max_retries
    (and no other active work remains). Unreachable ``planned`` dependents of
    exhausted failures do not count as active work.
    """
    if not steps:
        return "planned"
    states = [str(s.get("state")) for s in steps]
    if any(s == "pending_approval" for s in states):
        return "paused"

    by_id = {str(s["id"]): s for s in steps if s.get("id") is not None}
    has_retryable_failure = any(
        str(s.get("state")) == "failed" and not _retries_exhausted(s) for s in steps
    )
    has_exhausted_failure = any(
        str(s.get("state")) == "failed" and _retries_exhausted(s) for s in steps
    )
    has_active = has_retryable_failure or any(
        (
            state in {"ready", "running", "verifying", "blocked", "unknown"}
            or (
                state == "planned"
                and not _planned_blocked_by_exhausted_failure(step, by_id)
            )
        )
        for step, state in zip(steps, states)
    )

    if has_active:
        return "running"

    # No active / retryable work left.
    if has_exhausted_failure:
        return "failed"
    if all(s == "cancelled" for s in states):
        return "cancelled"
    if all(s in {"succeeded", "cancelled"} for s in states) and any(
        s == "succeeded" for s in states
    ):
        return "succeeded"
    return "running"


class WorkflowEngine:
    """Deterministic state machine over a WorkflowStore."""

    def __init__(self, store: WorkflowStore):
        self._store = store

    def create(
        self,
        *,
        client_id: str,
        owner_goal: str,
        steps: List[Dict[str, Any]],
        workflow_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        # Assign stable ids first, then fail closed on graph errors before write.
        from backend.services.os_workflows.store import _new_id

        normalized = []
        for index, raw in enumerate(steps):
            item = dict(raw)
            if not item.get("id"):
                item["id"] = _new_id()
            if "ordinal" not in item:
                item["ordinal"] = index
            normalized.append(item)
        validate_dependency_graph(normalized)
        created = self._store.create_workflow(
            client_id=client_id,
            owner_goal=owner_goal,
            steps=normalized,
            workflow_id=workflow_id,
        )
        return self.recover(client_id, created["id"])

    def recover(self, client_id: str, workflow_id: str) -> Dict[str, Any]:
        """Restart-safe: recompute readiness and workflow status from storage."""
        workflow = self._require_workflow(client_id, workflow_id)
        if is_workflow_terminal(workflow["status"]):
            steps = self._store.list_steps(client_id, workflow_id)
            out = dict(workflow)
            out["steps"] = steps
            return out

        self.mark_ready_steps(client_id, workflow_id)
        self.sync_workflow_status(client_id, workflow_id)
        workflow = self._require_workflow(client_id, workflow_id)
        steps = self._store.list_steps(client_id, workflow_id)
        out = dict(workflow)
        out["steps"] = steps
        return out

    def mark_ready_steps(self, client_id: str, workflow_id: str) -> List[Dict[str, Any]]:
        steps = self._store.list_steps(client_id, workflow_id)
        validate_dependency_graph(steps)
        advanced = []
        for step_id in compute_ready_step_ids(steps):
            step = next(s for s in steps if str(s["id"]) == step_id)
            try:
                updated = self._store.transition_step_cas(
                    client_id=client_id,
                    step_id=step_id,
                    expected_state="planned",
                    expected_version=int(step["row_version"]),
                    target_state="ready",
                    risk_level=int(step.get("risk_level", 1)),
                )
                advanced.append(updated)
            except ConcurrentModification:
                continue
        return advanced

    def queue_ready_for_execution(
        self, client_id: str, workflow_id: str
    ) -> List[Dict[str, Any]]:
        """Move ready steps to pending_approval (L2/L3) or running (L0/L1).

        Does **not** call tools. Caller must hand ``running`` steps to the
        Action Executor via the typed Tool/Action boundary.
        """
        steps = self._store.list_steps(client_id, workflow_id)
        queued = []
        for step in steps:
            if step.get("state") != "ready":
                continue
            risk = int(step.get("risk_level", 1))
            target = "pending_approval" if risk >= RISK_FAIL_CLOSED else "running"
            try:
                updated = self._store.transition_step_cas(
                    client_id=client_id,
                    step_id=str(step["id"]),
                    expected_state="ready",
                    expected_version=int(step["row_version"]),
                    target_state=target,
                    risk_level=risk,
                )
                queued.append(updated)
            except (ConcurrentModification, InvalidWorkflowTransition):
                continue
        self.sync_workflow_status(client_id, workflow_id)
        return queued

    def approve_step(self, client_id: str, step_id: str) -> Dict[str, Any]:
        step = self._require_step(client_id, step_id)
        updated = self._store.transition_step_cas(
            client_id=client_id,
            step_id=step_id,
            expected_state="pending_approval",
            expected_version=int(step["row_version"]),
            target_state="running",
            risk_level=int(step.get("risk_level", 1)),
        )
        self.sync_workflow_status(client_id, str(updated["workflow_id"]))
        return updated

    def reject_step(
        self, client_id: str, step_id: str, *, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        step = self._require_step(client_id, step_id)
        patch = {"error": reason} if reason else None
        updated = self._store.transition_step_cas(
            client_id=client_id,
            step_id=step_id,
            expected_state="pending_approval",
            expected_version=int(step["row_version"]),
            target_state="cancelled",
            risk_level=int(step.get("risk_level", 1)),
            patch=patch,
        )
        self.sync_workflow_status(client_id, str(updated["workflow_id"]))
        return updated

    def record_running_outcome(
        self,
        client_id: str,
        step_id: str,
        *,
        outcome: str,
        execution_id: Optional[str] = None,
        verification_state: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record executor/provider outcome without calling providers.

        ``outcome`` is one of: verifying | succeeded | failed | unknown |
        cancelled.

        Execution success and verification success are separate:
        - ``running`` + ``succeeded`` with no verifier result → ``verifying``
          and ``verification_state="pending"`` (does **not** auto-succeed).
        - ``running`` + ``succeeded`` with ``verification_state`` in
          ``{passed, not_required}`` → ``verifying`` then ``succeeded``.
        - ``verifying`` + ``succeeded`` requires an explicit verifier result
          (``passed`` or ``not_required``).
        """
        if outcome not in {
            "verifying",
            "succeeded",
            "failed",
            "unknown",
            "cancelled",
        }:
            raise WorkflowStoreError(f"unsupported outcome {outcome!r}")
        step = self._require_step(client_id, step_id)
        risk = int(step.get("risk_level", 1))
        state = str(step["state"])
        patch: Dict[str, Any] = {}
        if execution_id is not None:
            patch["execution_id"] = execution_id
        if verification_state is not None:
            patch["verification_state"] = verification_state
        if error is not None:
            patch["error"] = error

        if state == "running" and outcome == "verifying":
            if "verification_state" not in patch:
                patch["verification_state"] = "pending"
            updated = self._store.transition_step_cas(
                client_id=client_id,
                step_id=step_id,
                expected_state="running",
                expected_version=int(step["row_version"]),
                target_state="verifying",
                risk_level=risk,
                patch=patch or None,
            )
        elif state == "running" and outcome in {"failed", "unknown", "cancelled"}:
            updated = self._store.transition_step_cas(
                client_id=client_id,
                step_id=step_id,
                expected_state="running",
                expected_version=int(step["row_version"]),
                target_state=outcome,
                risk_level=risk,
                patch=patch or None,
            )
        elif state == "running" and outcome == "succeeded":
            # Execution success ≠ verification success.
            vstate = verification_state if verification_state is not None else "pending"
            mid_patch = dict(patch)
            mid_patch["verification_state"] = vstate
            mid = self._store.transition_step_cas(
                client_id=client_id,
                step_id=step_id,
                expected_state="running",
                expected_version=int(step["row_version"]),
                target_state="verifying",
                risk_level=risk,
                patch=mid_patch,
            )
            if vstate in {"passed", "not_required"}:
                updated = self._store.transition_step_cas(
                    client_id=client_id,
                    step_id=step_id,
                    expected_state="verifying",
                    expected_version=int(mid["row_version"]),
                    target_state="succeeded",
                    risk_level=risk,
                    patch={"verification_state": vstate},
                )
            else:
                updated = mid
        elif state == "verifying" and outcome == "succeeded":
            vstate = (
                verification_state
                if verification_state is not None
                else step.get("verification_state")
            )
            if vstate not in {"passed", "not_required"}:
                raise WorkflowStoreError(
                    "explicit verification result required "
                    "(passed|not_required) to leave verifying"
                )
            verify_patch = dict(patch)
            verify_patch["verification_state"] = vstate
            updated = self._store.transition_step_cas(
                client_id=client_id,
                step_id=step_id,
                expected_state="verifying",
                expected_version=int(step["row_version"]),
                target_state="succeeded",
                risk_level=risk,
                patch=verify_patch,
            )
        elif state == "verifying" and outcome in {"failed", "unknown"}:
            updated = self._store.transition_step_cas(
                client_id=client_id,
                step_id=step_id,
                expected_state="verifying",
                expected_version=int(step["row_version"]),
                target_state=outcome,
                risk_level=risk,
                patch=patch or None,
            )
        else:
            raise InvalidWorkflowTransition("step", state, outcome)

        wf_id = str(updated["workflow_id"])
        if updated.get("state") == "succeeded":
            self.mark_ready_steps(client_id, wf_id)
        self.sync_workflow_status(client_id, wf_id)
        return updated

    def retry_failed_step(self, client_id: str, step_id: str) -> Dict[str, Any]:
        """Bounded retry for ``failed`` / L0-L1 ``unknown``. Never replays L2/L3 unknown."""
        step = self._require_step(client_id, step_id)
        state = str(step["state"])
        risk = int(step.get("risk_level", 1))
        retry_count = int(step.get("retry_count", 0))
        max_retries = int(step.get("max_retries", DEFAULT_MAX_RETRIES))

        if state == "unknown":
            if risk >= RISK_FAIL_CLOSED:
                raise InvalidWorkflowTransition("step", "unknown", "ready")
            if retry_count >= max_retries:
                raise WorkflowStoreError(
                    f"step {step_id} exhausted retries ({retry_count}/{max_retries})"
                )
            # L0/L1 controlled recovery — same bound as failed retries.
            updated = self._store.transition_step_cas(
                client_id=client_id,
                step_id=step_id,
                expected_state="unknown",
                expected_version=int(step["row_version"]),
                target_state="ready",
                risk_level=risk,
                patch={
                    "retry_count": retry_count + 1,
                    "error": None,
                    "execution_id": None,
                    "verification_state": None,
                },
            )
            self.sync_workflow_status(client_id, str(updated["workflow_id"]))
            return updated

        if state != "failed":
            raise InvalidWorkflowTransition("step", state, "ready")

        if retry_count >= max_retries:
            raise WorkflowStoreError(
                f"step {step_id} exhausted retries ({retry_count}/{max_retries})"
            )
        updated = self._store.transition_step_cas(
            client_id=client_id,
            step_id=step_id,
            expected_state="failed",
            expected_version=int(step["row_version"]),
            target_state="ready",
            risk_level=risk,
            patch={
                "retry_count": retry_count + 1,
                "error": None,
                "execution_id": None,
                "verification_state": None,
            },
        )
        self.sync_workflow_status(client_id, str(updated["workflow_id"]))
        return updated

    def cancel_unknown_l2(self, client_id: str, step_id: str) -> Dict[str, Any]:
        step = self._require_step(client_id, step_id)
        updated = self._store.transition_step_cas(
            client_id=client_id,
            step_id=step_id,
            expected_state="unknown",
            expected_version=int(step["row_version"]),
            target_state="cancelled",
            risk_level=int(step.get("risk_level", 1)),
        )
        self.sync_workflow_status(client_id, str(updated["workflow_id"]))
        return updated

    def sync_workflow_status(self, client_id: str, workflow_id: str) -> Dict[str, Any]:
        workflow = self._require_workflow(client_id, workflow_id)
        if is_workflow_terminal(workflow["status"]):
            return workflow
        steps = self._store.list_steps(client_id, workflow_id)
        desired = derive_workflow_status(steps)
        current = str(workflow["status"])
        if desired == current:
            return workflow
        # Only apply legal transitions; ignore if derive suggests impossible edge.
        try:
            return self._store.transition_workflow_cas(
                client_id=client_id,
                workflow_id=workflow_id,
                expected_status=current,
                expected_version=int(workflow["row_version"]),
                target_status=desired,
            )
        except (InvalidWorkflowTransition, ConcurrentModification):
            # Multi-hop: planned→running→paused etc.
            if current == "planned" and desired in {"paused", "succeeded", "failed"}:
                mid = self._store.transition_workflow_cas(
                    client_id=client_id,
                    workflow_id=workflow_id,
                    expected_status="planned",
                    expected_version=int(workflow["row_version"]),
                    target_status="running",
                )
                if desired == "running":
                    return mid
                try:
                    return self._store.transition_workflow_cas(
                        client_id=client_id,
                        workflow_id=workflow_id,
                        expected_status="running",
                        expected_version=int(mid["row_version"]),
                        target_status=desired,
                    )
                except (InvalidWorkflowTransition, ConcurrentModification):
                    return mid
            if current == "paused" and desired == "running":
                try:
                    return self._store.transition_workflow_cas(
                        client_id=client_id,
                        workflow_id=workflow_id,
                        expected_status="paused",
                        expected_version=int(workflow["row_version"]),
                        target_status="running",
                    )
                except ConcurrentModification:
                    return workflow
            return workflow

    def _require_workflow(self, client_id: str, workflow_id: str) -> Dict[str, Any]:
        row = self._store.get_workflow(client_id, workflow_id)
        if not row:
            raise WorkflowStoreError(f"workflow {workflow_id} not found")
        return row

    def _require_step(self, client_id: str, step_id: str) -> Dict[str, Any]:
        row = self._store.get_step(client_id, step_id)
        if not row:
            raise WorkflowStoreError(f"step {step_id} not found")
        return row
