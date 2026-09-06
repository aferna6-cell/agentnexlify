"""M9.5 shadow planner path — in-memory observation only.

Architectural boundary (non-negotiable for this skeleton):
- Accept an owner request → CandidatePlan (injected planner or refuse)
- Validate in memory → ShadowObservation
- Do **not** import or call WorkflowStore, Action Executor, Gmail/Calendar/CRM
- Do **not** import llm_runtime / Anthropic
- Do **not** persist plans or execute tools

Live mode without an injected planner hard-fails before any provider
invocation when ``ANTHROPIC_API_KEY`` is absent. This skeleton still
refuses to wire a provider even when the key is present.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from backend.services.os_workflows.plan_schema import CandidatePlan, ValidationResult
from backend.services.os_workflows.plan_validator import validate_plan

PlannerFn = Callable[["ShadowRequest"], CandidatePlan]


@dataclass(frozen=True)
class ShadowRequest:
    """Owner request observed by the shadow path. Never persisted."""

    client_id: str
    owner_goal: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ShadowObservation:
    """In-memory shadow result. Flags stay false — this path cannot act."""

    request: ShadowRequest
    plan: Optional[CandidatePlan]
    validation: Optional[ValidationResult]
    persisted: bool = False
    executed: bool = False
    provider_called: bool = False
    error: Optional[str] = None


def run_shadow(
    request: ShadowRequest,
    *,
    planner: Optional[PlannerFn] = None,
    mode: str = "fixture",
    store: Any = None,
    executor: Any = None,
) -> ShadowObservation:
    """Observe a candidate plan without store, executor, or provider I/O.

    ``store`` and ``executor`` are accepted only so tests can prove they
    are never touched. Passing them does not enable persistence or execution.
    """
    del store, executor

    if mode not in ("fixture", "live"):
        raise ValueError(f"unknown shadow mode {mode!r} (use fixture|live)")

    if mode == "live" and planner is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "live shadow requires ANTHROPIC_API_KEY "
                "(or use mode=fixture / inject planner=)"
            )
        raise RuntimeError("M9.5 skeleton has no provider wiring; inject planner=")

    if planner is None:
        raise ValueError("fixture shadow requires planner=")

    plan = planner(request)
    validation = validate_plan(plan, case_client_id=request.client_id)
    return ShadowObservation(
        request=request,
        plan=plan,
        validation=validation,
        persisted=False,
        executed=False,
        provider_called=False,
    )
