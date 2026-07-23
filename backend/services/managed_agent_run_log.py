"""Fail-open run logging for Managed Agent runs (Phase 0).

Persists one row per run to ``managed_agent_runs`` (migration 188) so the
rollout plan's Phase 0 exit criteria — cost/run measured and logged — have
data to read. Every write here is fail-open: a missing table, a DB blip, or
a bad status is logged as a warning and swallowed. Run logging must never
break the run path.

Under ``TESTING=1`` the DB is never touched unless a ``db`` handle is
injected explicitly (unit tests pass a mock to exercise the insert path).

Cross-refs: plans/managed-agents-rollout_plan.md §Phase 0,
migrations/188_managed_agent_runs_log.sql,
backend/routers/managed_agent_runs.py (call sites).
"""

import logging
import os

logger = logging.getLogger(__name__)

TABLE = "managed_agent_runs"
VALID_STATUSES = frozenset({"success", "error", "unavailable"})

_SUMMARY_MAX_LEN = 500
_ERROR_MAX_LEN = 2000


def _is_testing() -> bool:
    return os.environ.get("TESTING", "").strip() == "1"


def record_run(
    tenant_id: str,
    agent_key: str,
    status: str,
    tokens_in: int = 0,
    tokens_out: int = 0,
    duration_ms: int = 0,
    request_summary: str = "",
    error: str | None = None,
    *,
    db=None,
) -> bool:
    """Persist one Managed Agent run outcome. Returns True on success.

    Fail-open by contract: never raises. Any validation or DB failure is
    logged at WARNING and reported as False. Under TESTING (and no injected
    ``db``) this is a no-op returning True.
    """
    if status not in VALID_STATUSES:
        logger.warning(
            "managed_agent_run_log: invalid status %r for tenant=%s agent=%s "
            "— run not recorded (valid: %s)",
            status, tenant_id, agent_key, sorted(VALID_STATUSES),
        )
        return False

    if db is None and _is_testing():
        return True

    try:
        if db is None:
            # Lazy import so this module stays importable without DB config.
            from backend.models.database import get_service_supabase

            db = get_service_supabase()

        payload = {
            "tenant_id": tenant_id,
            "agent_key": agent_key,
            "status": status,
            "tokens_in": int(tokens_in or 0),
            "tokens_out": int(tokens_out or 0),
            "duration_ms": int(duration_ms or 0),
            "request_summary": (request_summary or "")[:_SUMMARY_MAX_LEN],
            "error": error[:_ERROR_MAX_LEN] if error else None,
        }
        db.table(TABLE).insert(payload).execute()
        return True
    except Exception:
        logger.warning(
            "managed_agent_run_log: record_run failed for tenant=%s agent=%s "
            "status=%s (fail-open, run not recorded)",
            tenant_id, agent_key, status,
        )
        return False
