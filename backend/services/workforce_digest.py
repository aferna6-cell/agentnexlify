"""Weekly "Your AI Workforce" digest section (suite - governance pillar).

Owners now have agents doing standing work (scheduled tasks, projects,
auto-drafts) while they are away - this section makes that visible in the
existing Friday weekly digest email: what ran, what is waiting for their
approval (and how stale the oldest wait is), and what actually went out.

Deterministic count queries only; every value is real. Returns None when the
tenant has no Agent OS activity at all so chatbot-only tenants keep their
current digest unchanged. All content is system-generated (department names,
counts) - no customer-typed text ever enters the HTML.
"""

import logging
from datetime import datetime, timedelta, timezone

from backend.services.tenant_scope import tenant_select

logger = logging.getLogger(__name__)

_DEPARTMENT_CAP = 8


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _week_ago() -> str:
    return (_now() - timedelta(days=7)).isoformat()


def _runs_by_department(db, tenant_id: str) -> dict[str, int]:
    rows = (
        tenant_select(db, "os_agent_runs", tenant_id, "agent_name")
        .gte("created_at", _week_ago())
        .limit(500)
        .execute()
    ).data or []
    counts: dict[str, int] = {}
    for row in rows:
        name = str(row.get("agent_name") or "agent").replace("_", " ")
        counts[name] = counts.get(name, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: kv[1], reverse=True))


def _pending_approvals(db, tenant_id: str) -> tuple[int, int]:
    """(count, oldest_age_days) of drafts waiting at the approval gate."""
    rows = (
        tenant_select(db, "os_agent_runs", tenant_id, "created_at")
        .eq("deliverable_status", "pending_approval")
        .order("created_at", desc=False)
        .limit(100)
        .execute()
    ).data or []
    if not rows:
        return 0, 0
    oldest = str(rows[0].get("created_at") or "")
    age_days = 0
    try:
        oldest_dt = datetime.fromisoformat(oldest.replace("Z", "+00:00"))
        age_days = max(0, (_now() - oldest_dt).days)
    except ValueError:
        pass
    return len(rows), age_days


def _count_since(db, table: str, tenant_id: str, date_col: str = "created_at") -> int:
    rows = (
        tenant_select(db, table, tenant_id, "id")
        .gte(date_col, _week_ago())
        .limit(500)
        .execute()
    ).data or []
    return len(rows)


def _scheduled_task_runs(db, tenant_id: str) -> int:
    rows = (
        tenant_select(db, "os_scheduled_tasks", tenant_id, "last_run_at")
        .gte("last_run_at", _week_ago())
        .limit(50)
        .execute()
    ).data or []
    return len(rows)


def _active_projects(db, tenant_id: str) -> int:
    rows = (
        tenant_select(db, "os_projects", tenant_id, "id")
        .in_("status", ["approved", "running"])
        .limit(10)
        .execute()
    ).data or []
    return len(rows)


def build_workforce_html(db, tenant_id: str) -> str | None:
    """Pre-formatted HTML block for the weekly digest, or None when idle.

    Best-effort: any read failure inside a stat degrades that stat to 0;
    a total failure returns None and the digest renders without the section.
    """
    try:
        by_dept = _runs_by_department(db, tenant_id)
        pending, oldest_days = _pending_approvals(db, tenant_id)
        sent = _count_since(db, "os_outbound_log", tenant_id)
        task_runs = _scheduled_task_runs(db, tenant_id)
        projects = _active_projects(db, tenant_id)
    except Exception:
        logger.warning(
            "workforce_digest: build failed tenant=%s", tenant_id, exc_info=True
        )
        return None

    total_runs = sum(by_dept.values())
    if total_runs == 0 and pending == 0 and task_runs == 0 and projects == 0:
        return None

    lines: list[str] = []
    if total_runs:
        dept_bits = ", ".join(
            f"{name} ({count})" for name, count in list(by_dept.items())[:_DEPARTMENT_CAP]
        )
        lines.append(
            f"<li>Your agents completed <b>{total_runs}</b> task(s): {dept_bits}.</li>"
        )
    if task_runs:
        lines.append(
            f"<li><b>{task_runs}</b> recurring task(s) ran on schedule.</li>"
        )
    if sent:
        lines.append(f"<li><b>{sent}</b> approved message(s) went out.</li>")
    if projects:
        lines.append(
            f"<li><b>{projects}</b> multi-step project(s) are in motion.</li>"
        )
    if pending:
        staleness = (
            f" - the oldest has waited {oldest_days} day(s)" if oldest_days >= 2 else ""
        )
        lines.append(
            f"<li style='color:#b45309;'><b>{pending}</b> draft(s) are waiting for "
            f"your approval{staleness}. "
            f"<a href='https://app.agentnexlify.com/dashboard/agent-os' "
            f"style='color:#6366f1;'>Review them</a>.</li>"
        )

    return "<ul style='padding-left:18px;margin:8px 0;'>" + "".join(lines) + "</ul>"
