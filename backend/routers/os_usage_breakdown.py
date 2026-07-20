"""Per-department usage breakdown (enterprise-audit item 3).

GET /api/v1/os/usage/breakdown answers the owner's "what am I paying for?"
question: this billing cycle's agent runs and token spend grouped by
department, assembled from os_agent_runs + os_model_call_log. Token counts
only — no dollar figures on customer-facing surfaces (same policy as
ai_usage_guard.get_ai_usage_status).
"""

import logging

from fastapi import APIRouter, Depends

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services.tenant_scope import tenant_table
from backend.services.usage_meter import current_cycle_start

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/os", tags=["agent-os"])

_ROW_CAP = 5000


def build_breakdown(runs: list[dict], calls: list[dict]) -> list[dict]:
    """Aggregate runs + model calls into per-department rows.

    Model calls join to runs via run_id; calls with no persisted run (answer /
    decline turns) group under "routing" so their tokens are still visible.
    """
    dept_by_run: dict[str, str] = {}
    stats: dict[str, dict] = {}

    def _bucket(name: str) -> dict:
        return stats.setdefault(
            name,
            {"department": name, "runs": 0, "input_tokens": 0, "output_tokens": 0},
        )

    for run in runs:
        run_id = run.get("id")
        department = run.get("agent_name") or "unknown"
        if run_id:
            dept_by_run[run_id] = department
        _bucket(department)["runs"] += 1

    for call in calls:
        department = dept_by_run.get(call.get("run_id") or "", "routing")
        bucket = _bucket(department)
        bucket["input_tokens"] += int(call.get("input_tokens") or 0)
        bucket["output_tokens"] += int(call.get("output_tokens") or 0)

    return sorted(
        stats.values(),
        key=lambda b: (b["input_tokens"] + b["output_tokens"], b["runs"]),
        reverse=True,
    )


@router.get("/usage/breakdown")
async def usage_breakdown(claims: dict = Depends(_get_current_tenant)):
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    cycle_start = current_cycle_start()
    try:
        runs = (
            tenant_table(db, "os_agent_runs", client_id)
            .select("id, agent_name")
            .gte("created_at", cycle_start)
            .limit(_ROW_CAP)
            .execute()
        ).data or []
        calls = (
            tenant_table(db, "os_model_call_log", client_id)
            .select("run_id, input_tokens, output_tokens")
            .gte("created_at", cycle_start)
            .limit(_ROW_CAP)
            .execute()
        ).data or []
    except Exception:
        logger.warning(
            "usage breakdown read failed client_id=%s", client_id, exc_info=True
        )
        runs, calls = [], []

    return {
        "cycle_start": cycle_start,
        "departments": build_breakdown(runs, calls),
    }
