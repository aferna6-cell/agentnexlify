"""Daily approval-queue rollup (round-3 item 4 - trust/governance).

The per-draft email (os_approval_notify) covers the moment a draft parks;
this covers the queue that sits. Live tenants carry 10-30 pending drafts -
an ignored approval queue quietly kills the propose-only trust model. Once
a day, a tenant whose oldest pending draft is 24h+ old gets one rollup:
"N drafts waiting, oldest X day(s) - review them."

Deterministic counts only; deduped per tenant per day via activity_log.
Best-effort throughout - a failure for one tenant never blocks the rest.
"""

import logging
from datetime import datetime, timedelta, timezone

from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

_MIN_OLDEST_HOURS = 24
_TENANT_BATCH = 200


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _age_hours(created_at: str) -> float:
    try:
        dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
        return (_now() - dt).total_seconds() / 3600
    except ValueError:
        return 0.0


async def send_approval_rollups() -> int:
    """One rollup email per tenant with a stale pending queue. Returns sent."""
    from backend.services.activity import log_activity
    from backend.services.email_sender import send_email, mask_email

    db = get_service_supabase()
    day_tag = f"approval_rollup_{_now().date().isoformat()}"

    try:
        runs = (
            db.table("os_agent_runs")
            .select("client_id, created_at")
            .eq("deliverable_status", "pending_approval")
            .order("created_at", desc=False)
            .limit(1000)
            .execute()
        ).data or []
    except Exception:
        logger.warning("approval_rollup: pending read failed", exc_info=True)
        return 0

    queues: dict[str, dict] = {}
    for run in runs:
        cid = run.get("client_id")
        if not cid:
            continue
        q = queues.setdefault(cid, {"count": 0, "oldest": run.get("created_at")})
        q["count"] += 1

    sent = 0
    for cid, q in list(queues.items())[:_TENANT_BATCH]:
        oldest_hours = _age_hours(q["oldest"])
        if oldest_hours < _MIN_OLDEST_HOURS:
            continue
        try:
            already = (
                db.table("activity_log")
                .select("id", count="exact")
                .eq("tenant_id", cid)
                .eq("activity_type", day_tag)
                .limit(1)
                .execute()
            )
            if already.count and already.count > 0:
                continue
            tenant_rows = (
                db.table("tenants")
                .select("business_name, owner_email, owner_name")
                .eq("id", cid)
                .limit(1)
                .execute()
            ).data or []
            email = (tenant_rows[0].get("owner_email") or "") if tenant_rows else ""
            if not email:
                continue
            owner = (tenant_rows[0].get("owner_name") or "there").strip() or "there"
            oldest_days = max(1, int(oldest_hours // 24))
            body_html = (
                f"<div style='font-family:sans-serif;max-width:600px;margin:0 auto;'>"
                f"<h2 style='color:#1e293b;'>Hi {owner},</h2>"
                f"<p style='color:#374151;'>Your AI staff has <b>{q['count']} "
                f"draft{'s' if q['count'] != 1 else ''}</b> waiting for your "
                f"approval - the oldest has waited {oldest_days} "
                f"day{'s' if oldest_days != 1 else ''}. Nothing sends until "
                f"you approve it.</p>"
                f"<p><a href='https://app.agentnexlify.com/dashboard/agent-os' "
                f"style='color:#6366f1;font-weight:600;text-decoration:none;'>"
                f"Review your drafts &rarr;</a></p>"
                f"</div>"
            )
            result = await send_email(
                to=email,
                subject=f"{q['count']} draft(s) waiting for your approval",
                body_html=body_html,
                tenant_id=cid,
            )
            if result.get("success"):
                sent += 1
                logger.info(
                    "approval_rollup: sent to %s tenant=%s count=%d",
                    mask_email(email),
                    cid,
                    q["count"],
                )
                log_activity(
                    tenant_id=cid,
                    activity_type=day_tag,
                    description=(
                        f"Approval rollup sent: {q['count']} pending, "
                        f"oldest {oldest_days}d"
                    ),
                )
        except Exception:
            logger.warning(
                "approval_rollup: failed for tenant %s", cid, exc_info=True
            )
    return sent
