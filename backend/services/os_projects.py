"""Multi-department OS Projects (suite item 4 - orchestration pillar).

One owner ask ("launch a spring promo") becomes a visible, approvable PLAN of
department steps, then executes across departments one step at a time through
the EXACT same engine path as a typed ask (`os_thread_runner.process_user_turn`)
- so routing, approvals, the never-auto-send set, and the outbound guard all
apply unchanged to every step deliverable. A project approval is NOT an
auto-send grant.

Spec: specs/os-projects_spec.md. Runner fires from the 5-minute tier of
main._automation_loop behind the `os_projects_enabled` platform flag.
"""

import json
import logging
from datetime import datetime, timezone

from backend.services.os_routing_memory import KNOWN_DEPARTMENTS
from backend.services.tenant_scope import tenant_select, tenant_table

logger = logging.getLogger(__name__)

MAX_ASK_LEN = 2000
MAX_STEPS = 6
MIN_STEPS = 2
MAX_ACTIVE_PROJECTS = 3
_RUNNER_BATCH_CAP = 5
_SUMMARY_BODY_CHARS = 300

# "planning" rows (chat/SQL-queued, awaiting the background planner) count as
# active so a tenant can't queue unlimited projects past MAX_ACTIVE_PROJECTS.
ACTIVE_STATUSES = ("planning", "draft", "approved", "running")

_PLANNER_MODEL = "claude-sonnet-5"

# Anthropic structured output requires additionalProperties: false on every
# object level - the prod planner smoke (2026-07-21) failed with a 400
# without it (local tests mock the LLM call and cannot catch this).
_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "department": {"type": "string"},
                    "objective": {"type": "string"},
                },
                "required": ["department", "objective"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "steps"],
    "additionalProperties": False,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _planner_system(departments: list[str]) -> str:
    return (
        "You are the project planner for a small-business AI workforce. "
        "Break the owner's ask into a short, sequential plan of department "
        f"steps. Use ONLY these departments: {', '.join(departments)}. "
        f"Return {MIN_STEPS}-{MAX_STEPS} steps. Each step objective is one "
        "concrete instruction that department can complete on its own, in "
        "order, building on earlier steps. Also return a short project title."
    )


def parse_plan(raw_text: str) -> dict:
    """Parse and validate the planner's JSON. Raises ValueError on bad plans.

    Never accepts a half-plan: unknown departments, too few/many steps, or
    unparseable output all reject the whole plan.
    """
    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        data = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"planner output not JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("planner output not an object")
    steps_in = data.get("steps")
    if not isinstance(steps_in, list) or not (MIN_STEPS <= len(steps_in) <= MAX_STEPS):
        raise ValueError(f"plan must have {MIN_STEPS}-{MAX_STEPS} steps")
    steps = []
    for raw in steps_in:
        if not isinstance(raw, dict):
            raise ValueError("step is not an object")
        department = str(raw.get("department") or "").strip().lower()
        objective = str(raw.get("objective") or "").strip()
        if department not in KNOWN_DEPARTMENTS:
            raise ValueError(f"unknown department: {department}")
        if len(objective) < 5:
            raise ValueError("step objective too short")
        steps.append({"department": department, "objective": objective[:500]})
    title = str(data.get("title") or "").strip()[:120] or "Project"
    return {"title": title, "steps": steps}


async def plan_project(db, client_id: str, ask: str) -> dict:
    """Create a draft project: planner call -> validated steps persisted.

    Planner failure leaves the project as a draft with an error note and NO
    steps (never a half-plan), matching the spec invariant.
    """
    ask = (ask or "").strip()[:MAX_ASK_LEN]
    if len(ask) < 10:
        raise ValueError("ask too short")

    active = (
        tenant_select(db, "os_projects", client_id, "id")
        .in_("status", list(ACTIVE_STATUSES))
        .limit(MAX_ACTIVE_PROJECTS)
        .execute()
    ).data or []
    if len(active) >= MAX_ACTIVE_PROJECTS:
        raise ValueError("active project limit reached")

    project = (
        tenant_table(db, "os_projects", client_id)
        .insert({"title": ask[:60], "ask": ask, "status": "draft"})
        .execute()
    ).data[0]
    return await generate_and_persist_plan(db, project)


async def generate_and_persist_plan(db, project: dict) -> dict:
    """Run the Sonnet planner for one project row and persist the steps.

    Shared by the interactive endpoint (plan_project) and the background
    runner (plan_pending_projects). Planner failure leaves the project as a
    draft with an error note and NO steps - never a half-plan.
    """
    client_id = project["client_id"]
    ask = str(project.get("ask") or "")
    try:
        from backend.services.llm_runtime import call_claude_messages

        result = await call_claude_messages(
            operation="os_project_plan",
            model=_PLANNER_MODEL,
            max_tokens=1200,
            temperature=None,
            system=_planner_system(sorted(KNOWN_DEPARTMENTS)),
            messages=[{"role": "user", "content": ask}],
            response_schema=_PLAN_SCHEMA,
            timeout=45.0,
            metadata={"client_id": client_id, "project_id": project["id"]},
        )
        plan = parse_plan(result.text)
    except Exception as exc:
        logger.warning(
            "os_projects: planner failed project=%s tenant=%s",
            project["id"],
            client_id,
            exc_info=True,
        )
        tenant_table(db, "os_projects", client_id).update(
            {
                "status": "draft",
                "error": f"planner failed: {exc}"[:500],
                "updated_at": _now(),
            }
        ).eq("id", project["id"]).execute()
        project["error"] = f"planner failed: {exc}"[:500]
        project["status"] = "draft"
        return {"project": project, "steps": []}

    rows = [
        {
            "client_id": client_id,
            "project_id": project["id"],
            "position": idx,
            "department": step["department"],
            "objective": step["objective"],
            "status": "pending",
        }
        for idx, step in enumerate(plan["steps"], start=1)
    ]
    steps = (db.table("os_project_steps").insert(rows).execute()).data or rows
    tenant_table(db, "os_projects", client_id).update(
        {"title": plan["title"], "status": "draft", "updated_at": _now()}
    ).eq("id", project["id"]).execute()
    project["title"] = plan["title"]
    project["status"] = "draft"
    return {"project": project, "steps": steps}


_PLANNING_BATCH_CAP = 3


async def plan_pending_projects(db) -> int:
    """Plan projects created with status='planning' (chat/SQL-originated).

    Lets a project be requested from any surface that can insert a row -
    the runner turns the ask into an approvable draft plan through the same
    validated planner path the endpoint uses. Returns projects planned.
    """
    try:
        pending = (
            db.table("os_projects")
            .select("*")
            .eq("status", "planning")
            .order("created_at", desc=False)
            .limit(_PLANNING_BATCH_CAP)
            .execute()
        ).data or []
    except Exception:
        logger.warning("os_projects: planning read failed", exc_info=True)
        return 0
    planned = 0
    for project in pending:
        try:
            await generate_and_persist_plan(db, project)
            planned += 1
        except Exception:
            logger.warning(
                "os_projects: background plan failed project=%s",
                project.get("id"),
                exc_info=True,
            )
    return planned


def project_steps(db, client_id: str, project_id: str) -> list[dict]:
    return (
        tenant_select(db, "os_project_steps", client_id, "*")
        .eq("project_id", project_id)
        .order("position", desc=False)
        .limit(MAX_STEPS)
        .execute()
    ).data or []


def _set_step(db, client_id: str, step_id: str, fields: dict) -> None:
    tenant_table(db, "os_project_steps", client_id).update(
        {**fields, "updated_at": _now()}
    ).eq("id", step_id).execute()


def _set_project(db, client_id: str, project_id: str, fields: dict) -> None:
    tenant_table(db, "os_projects", client_id).update(
        {**fields, "updated_at": _now()}
    ).eq("id", project_id).execute()


def _completed_summaries(db, client_id: str, steps: list[dict]) -> list[str]:
    """Title + first 300 chars of each done step's deliverable - never raw
    PII dumps (spec invariant)."""
    summaries = []
    for step in steps:
        if step.get("status") != "done" or not step.get("agent_run_id"):
            continue
        try:
            runs = (
                tenant_select(db, "os_agent_runs", client_id, "deliverable")
                .eq("id", step["agent_run_id"])
                .limit(1)
                .execute()
            ).data or []
        except Exception:
            continue
        deliverable = (runs[0].get("deliverable") or {}) if runs else {}
        if isinstance(deliverable, dict) and deliverable.get("title"):
            body = str(deliverable.get("body") or "")[:_SUMMARY_BODY_CHARS]
            summaries.append(
                f"Step {step['position']} ({step['department']}) produced: "
                f"{deliverable['title']} - {body}"
            )
    return summaries


def _step_prompt(project: dict, step: dict, summaries: list[str]) -> str:
    parts = [
        f"You are executing step {step['position']} of the project: "
        f"{project.get('title') or project.get('ask', '')[:60]}.",
        f"Overall goal: {project.get('ask', '')}",
    ]
    if summaries:
        parts.append("Completed so far:\n" + "\n".join(summaries))
    parts.append(f"Your objective for this step: {step['objective']}")
    return "\n\n".join(parts)


async def _run_step(db, project: dict, step: dict, summaries: list[str]) -> None:
    """Drive one engine turn for a step; set awaiting_approval or done."""
    from backend.services.os_thread_runner import process_user_turn

    client_id = project["client_id"]
    prompt = _step_prompt(project, step, summaries)
    thread = (
        tenant_table(db, "os_threads", client_id)
        .insert({"title": f"Project step {step['position']}: {step['objective'][:50]}"})
        .execute()
    ).data[0]
    message = (
        tenant_table(db, "os_messages", client_id)
        .insert({"thread_id": thread["id"], "role": "user", "content": prompt})
        .execute()
    ).data[0]
    out = await process_user_turn(
        db,
        client_id,
        thread["id"],
        message,
        None,
        force_agent_id=step["department"],
        request_origin="system",
    )
    runs = out.get("agent_runs") or []
    run = runs[0] if runs and isinstance(runs[0], dict) else None
    fields: dict = {"thread_id": thread["id"]}
    if run and run.get("id"):
        fields["agent_run_id"] = run["id"]
    if run and run.get("deliverable_status") == "pending_approval":
        fields["status"] = "awaiting_approval"
    else:
        # Auto-approved deliverable, or an answer with nothing outbound.
        fields["status"] = "done"
    _set_step(db, client_id, step["id"], fields)
    step.update(fields)


def _resolve_awaiting(db, client_id: str, step: dict) -> str:
    """Map an awaiting step's deliverable status -> done | failed | waiting."""
    try:
        runs = (
            tenant_select(db, "os_agent_runs", client_id, "deliverable_status")
            .eq("id", step.get("agent_run_id"))
            .limit(1)
            .execute()
        ).data or []
    except Exception:
        logger.warning("os_projects: run read failed step=%s", step.get("id"))
        return "waiting"
    status = (runs[0].get("deliverable_status") or "") if runs else ""
    if status == "approved":
        return "done"
    if status == "rejected":
        return "failed"
    return "waiting"


async def advance_project(db, project: dict) -> None:
    """Advance one project by at most one engine step per tick."""
    client_id = project["client_id"]
    steps = project_steps(db, client_id, project["id"])
    if not steps:
        _set_project(
            db, client_id, project["id"], {"status": "failed", "error": "no steps"}
        )
        return

    for step in steps:
        if step.get("status") == "awaiting_approval":
            outcome = _resolve_awaiting(db, client_id, step)
            if outcome == "waiting":
                return
            _set_step(db, client_id, step["id"], {"status": outcome})
            step["status"] = outcome
            if outcome == "failed":
                _set_project(
                    db,
                    client_id,
                    project["id"],
                    {
                        "status": "failed",
                        "error": f"step {step['position']} deliverable rejected",
                    },
                )
                return

    next_step = next((s for s in steps if s.get("status") == "pending"), None)
    if next_step is None:
        if all(s.get("status") == "done" for s in steps):
            _set_project(db, client_id, project["id"], {"status": "done"})
        return

    if project.get("status") != "running":
        _set_project(db, client_id, project["id"], {"status": "running"})

    try:
        summaries = _completed_summaries(db, client_id, steps)
        await _run_step(db, project, next_step, summaries)
    except Exception as exc:
        logger.warning(
            "os_projects: step run failed project=%s step=%s",
            project["id"],
            next_step["id"],
            exc_info=True,
        )
        _set_step(db, client_id, next_step["id"], {"status": "failed"})
        _set_project(
            db,
            client_id,
            project["id"],
            {"status": "failed", "error": f"step {next_step['position']}: {exc}"[:500]},
        )
        return

    steps = project_steps(db, client_id, project["id"])
    if steps and all(s.get("status") == "done" for s in steps):
        _set_project(db, client_id, project["id"], {"status": "done"})


async def run_project_ticks(db) -> int:
    """Advance every approved/running project by one step. Returns count.

    Also plans any 'planning'-status projects first, so chat/SQL-originated
    asks become approvable drafts on the same tick cadence.
    """
    try:
        await plan_pending_projects(db)
    except Exception:
        logger.warning("os_projects: plan_pending_projects failed", exc_info=True)
    try:
        projects = (
            db.table("os_projects")
            .select("*")
            .in_("status", ["approved", "running"])
            .order("updated_at", desc=False)
            .limit(_RUNNER_BATCH_CAP)
            .execute()
        ).data or []
    except Exception:
        logger.warning("os_projects: runner read failed", exc_info=True)
        return 0
    advanced = 0
    for project in projects:
        try:
            await advance_project(db, project)
            advanced += 1
        except Exception:
            logger.warning(
                "os_projects: advance failed project=%s",
                project.get("id"),
                exc_info=True,
            )
    return advanced
