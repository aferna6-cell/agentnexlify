"""M9.2 durable store for workflows / steps.

Persistence only — no tool execution. All mutations are tenant-scoped via
``client_id``. Conditional updates use ``state`` + ``row_version`` for
at-most-once transitions (same idea as os_tool_executions approval claims).
"""

import copy
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol

from backend.services.os_workflows.contract import (
    transition_step,
    transition_workflow,
)
from backend.services.tenant_scope import tenant_insert, tenant_select, tenant_update


class WorkflowStoreError(RuntimeError):
    """Store-level failure (missing row, CAS miss, validation)."""


class ConcurrentModification(WorkflowStoreError):
    """Conditional update did not match expected state/version."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


class WorkflowStore(Protocol):
    def create_workflow(
        self,
        *,
        client_id: str,
        owner_goal: str,
        steps: List[Dict[str, Any]],
        workflow_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        ...

    def get_workflow(self, client_id: str, workflow_id: str) -> Optional[Dict[str, Any]]:
        ...

    def list_steps(self, client_id: str, workflow_id: str) -> List[Dict[str, Any]]:
        ...

    def get_step(self, client_id: str, step_id: str) -> Optional[Dict[str, Any]]:
        ...

    def transition_step_cas(
        self,
        *,
        client_id: str,
        step_id: str,
        expected_state: str,
        expected_version: int,
        target_state: str,
        risk_level: int,
        patch: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ...

    def transition_workflow_cas(
        self,
        *,
        client_id: str,
        workflow_id: str,
        expected_status: str,
        expected_version: int,
        target_status: str,
    ) -> Dict[str, Any]:
        ...

    def patch_step(
        self,
        *,
        client_id: str,
        step_id: str,
        expected_version: int,
        patch: Dict[str, Any],
    ) -> Dict[str, Any]:
        ...


class InMemoryWorkflowStore:
    """Deterministic in-process store for engine tests and local recovery."""

    def __init__(self) -> None:
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.steps: Dict[str, Dict[str, Any]] = {}

    def create_workflow(
        self,
        *,
        client_id: str,
        owner_goal: str,
        steps: List[Dict[str, Any]],
        workflow_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        wf_id = workflow_id or _new_id()
        if wf_id in self.workflows:
            raise WorkflowStoreError(f"workflow {wf_id} already exists")
        now = _now()
        workflow = {
            "id": wf_id,
            "client_id": client_id,
            "owner_goal": owner_goal,
            "status": "planned",
            "row_version": 1,
            "created_at": now,
            "updated_at": now,
        }
        created_steps = []
        for index, raw in enumerate(steps):
            step_id = str(raw.get("id") or _new_id())
            if step_id in self.steps:
                raise WorkflowStoreError(f"step {step_id} already exists")
            step = {
                "id": step_id,
                "workflow_id": wf_id,
                "client_id": client_id,
                "ordinal": int(raw.get("ordinal", index)),
                "description": str(raw["description"]),
                "dependencies": [str(d) for d in (raw.get("dependencies") or [])],
                "department": raw.get("department"),
                "tool_intent": copy.deepcopy(raw.get("tool_intent")),
                "state": str(raw.get("state") or "planned"),
                "risk_level": int(raw.get("risk_level", 1)),
                "execution_id": raw.get("execution_id"),
                "verification_state": raw.get("verification_state"),
                "error": raw.get("error"),
                "retry_count": int(raw.get("retry_count", 0)),
                "max_retries": int(raw.get("max_retries", 2)),
                "row_version": 1,
                "created_at": now,
                "updated_at": now,
            }
            self.steps[step_id] = step
            created_steps.append(copy.deepcopy(step))
        self.workflows[wf_id] = workflow
        out = copy.deepcopy(workflow)
        out["steps"] = created_steps
        return out

    def get_workflow(self, client_id: str, workflow_id: str) -> Optional[Dict[str, Any]]:
        row = self.workflows.get(workflow_id)
        if not row or row["client_id"] != client_id:
            return None
        return copy.deepcopy(row)

    def list_steps(self, client_id: str, workflow_id: str) -> List[Dict[str, Any]]:
        rows = [
            copy.deepcopy(s)
            for s in self.steps.values()
            if s["client_id"] == client_id and s["workflow_id"] == workflow_id
        ]
        rows.sort(key=lambda s: (s["ordinal"], s["id"]))
        return rows

    def get_step(self, client_id: str, step_id: str) -> Optional[Dict[str, Any]]:
        row = self.steps.get(step_id)
        if not row or row["client_id"] != client_id:
            return None
        return copy.deepcopy(row)

    def transition_step_cas(
        self,
        *,
        client_id: str,
        step_id: str,
        expected_state: str,
        expected_version: int,
        target_state: str,
        risk_level: int,
        patch: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        transition_step(expected_state, target_state, risk_level=risk_level)
        row = self.steps.get(step_id)
        if not row or row["client_id"] != client_id:
            raise WorkflowStoreError(f"step {step_id} not found")
        if row["state"] != expected_state or int(row["row_version"]) != expected_version:
            raise ConcurrentModification(
                f"step {step_id} CAS miss "
                f"(have {row['state']}@{row['row_version']}, "
                f"expected {expected_state}@{expected_version})"
            )
        row["state"] = target_state
        row["row_version"] = expected_version + 1
        row["updated_at"] = _now()
        if patch:
            for key, value in patch.items():
                if key in {"id", "workflow_id", "client_id"}:
                    continue
                row[key] = copy.deepcopy(value)
        return copy.deepcopy(row)

    def transition_workflow_cas(
        self,
        *,
        client_id: str,
        workflow_id: str,
        expected_status: str,
        expected_version: int,
        target_status: str,
    ) -> Dict[str, Any]:
        transition_workflow(expected_status, target_status)
        row = self.workflows.get(workflow_id)
        if not row or row["client_id"] != client_id:
            raise WorkflowStoreError(f"workflow {workflow_id} not found")
        if row["status"] != expected_status or int(row["row_version"]) != expected_version:
            raise ConcurrentModification(
                f"workflow {workflow_id} CAS miss "
                f"(have {row['status']}@{row['row_version']}, "
                f"expected {expected_status}@{expected_version})"
            )
        row["status"] = target_status
        row["row_version"] = expected_version + 1
        row["updated_at"] = _now()
        return copy.deepcopy(row)

    def patch_step(
        self,
        *,
        client_id: str,
        step_id: str,
        expected_version: int,
        patch: Dict[str, Any],
    ) -> Dict[str, Any]:
        row = self.steps.get(step_id)
        if not row or row["client_id"] != client_id:
            raise WorkflowStoreError(f"step {step_id} not found")
        if int(row["row_version"]) != expected_version:
            raise ConcurrentModification(
                f"step {step_id} version miss "
                f"(have {row['row_version']}, expected {expected_version})"
            )
        for key, value in patch.items():
            if key in {"id", "workflow_id", "client_id", "state"}:
                continue
            row[key] = copy.deepcopy(value)
        row["row_version"] = expected_version + 1
        row["updated_at"] = _now()
        return copy.deepcopy(row)


class SupabaseWorkflowStore:
    """Supabase-backed store (service role + tenant_scope filters)."""

    def __init__(self, db: Any) -> None:
        self._db = db

    def create_workflow(
        self,
        *,
        client_id: str,
        owner_goal: str,
        steps: List[Dict[str, Any]],
        workflow_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        wf_id = workflow_id or _new_id()
        now = _now()
        workflow = {
            "id": wf_id,
            "client_id": client_id,
            "owner_goal": owner_goal,
            "status": "planned",
            "row_version": 1,
            "created_at": now,
            "updated_at": now,
        }
        tenant_insert(self._db, "os_workflows", client_id, workflow).execute()
        created_steps = []
        for index, raw in enumerate(steps):
            step = {
                "id": str(raw.get("id") or _new_id()),
                "workflow_id": wf_id,
                "client_id": client_id,
                "ordinal": int(raw.get("ordinal", index)),
                "description": str(raw["description"]),
                "dependencies": [str(d) for d in (raw.get("dependencies") or [])],
                "department": raw.get("department"),
                "tool_intent": raw.get("tool_intent"),
                "state": str(raw.get("state") or "planned"),
                "risk_level": int(raw.get("risk_level", 1)),
                "execution_id": raw.get("execution_id"),
                "verification_state": raw.get("verification_state"),
                "error": raw.get("error"),
                "retry_count": int(raw.get("retry_count", 0)),
                "max_retries": int(raw.get("max_retries", 2)),
                "row_version": 1,
                "created_at": now,
                "updated_at": now,
            }
            tenant_insert(self._db, "os_workflow_steps", client_id, step).execute()
            created_steps.append(step)
        out = dict(workflow)
        out["steps"] = created_steps
        return out

    def get_workflow(self, client_id: str, workflow_id: str) -> Optional[Dict[str, Any]]:
        result = (
            tenant_select(self._db, "os_workflows", client_id)
            .eq("id", workflow_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None

    def list_steps(self, client_id: str, workflow_id: str) -> List[Dict[str, Any]]:
        result = (
            tenant_select(self._db, "os_workflow_steps", client_id)
            .eq("workflow_id", workflow_id)
            .order("ordinal")
            .execute()
        )
        return list(result.data or [])

    def get_step(self, client_id: str, step_id: str) -> Optional[Dict[str, Any]]:
        result = (
            tenant_select(self._db, "os_workflow_steps", client_id)
            .eq("id", step_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None

    def transition_step_cas(
        self,
        *,
        client_id: str,
        step_id: str,
        expected_state: str,
        expected_version: int,
        target_state: str,
        risk_level: int,
        patch: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        transition_step(expected_state, target_state, risk_level=risk_level)
        values = {
            "state": target_state,
            "row_version": expected_version + 1,
            "updated_at": _now(),
        }
        if patch:
            for key, value in patch.items():
                if key in {"id", "workflow_id", "client_id", "state", "row_version"}:
                    continue
                values[key] = value
        result = (
            tenant_update(self._db, "os_workflow_steps", client_id, values)
            .eq("id", step_id)
            .eq("state", expected_state)
            .eq("row_version", expected_version)
            .execute()
        )
        rows = result.data or []
        if not rows:
            raise ConcurrentModification(
                f"step {step_id} CAS miss "
                f"(expected {expected_state}@{expected_version})"
            )
        return rows[0]

    def transition_workflow_cas(
        self,
        *,
        client_id: str,
        workflow_id: str,
        expected_status: str,
        expected_version: int,
        target_status: str,
    ) -> Dict[str, Any]:
        transition_workflow(expected_status, target_status)
        values = {
            "status": target_status,
            "row_version": expected_version + 1,
            "updated_at": _now(),
        }
        result = (
            tenant_update(self._db, "os_workflows", client_id, values)
            .eq("id", workflow_id)
            .eq("status", expected_status)
            .eq("row_version", expected_version)
            .execute()
        )
        rows = result.data or []
        if not rows:
            raise ConcurrentModification(
                f"workflow {workflow_id} CAS miss "
                f"(expected {expected_status}@{expected_version})"
            )
        return rows[0]

    def patch_step(
        self,
        *,
        client_id: str,
        step_id: str,
        expected_version: int,
        patch: Dict[str, Any],
    ) -> Dict[str, Any]:
        values = {
            "row_version": expected_version + 1,
            "updated_at": _now(),
        }
        for key, value in patch.items():
            if key in {"id", "workflow_id", "client_id", "state", "row_version"}:
                continue
            values[key] = value
        result = (
            tenant_update(self._db, "os_workflow_steps", client_id, values)
            .eq("id", step_id)
            .eq("row_version", expected_version)
            .execute()
        )
        rows = result.data or []
        if not rows:
            raise ConcurrentModification(
                f"step {step_id} version miss (expected {expected_version})"
            )
        return rows[0]
