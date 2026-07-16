"""Expire stale pending-approval drafts (approval-queue hygiene).

Prod evidence (2026-07): tenants had drafts sitting in
``os_agent_runs.deliverable_status='pending_approval'`` since June — the
owner never actioned them, the sidebar badge stayed lit for weeks, and the
AI staff looked stalled. A month-old "friendly check-in" draft is also just
wrong to send: the moment has passed.

Nightly sweep (wired into the main.py automation loop's 30-min block):

  - Any draft still pending after ``_STALE_DAYS`` days without a touch
    (``updated_at`` — edits and retries keep a draft alive) is marked
    ``deliverable_status='expired'``.
  - The owner gets ONE digest email per sweep per tenant listing what was
    cleared and reassuring that nothing was sent. Drafts never vanish
    silently — that would erode the exact trust the approval flow builds.

Expired is terminal like rejected: the pending list filters it out, and the
approve/edit/reject routes 409 via ``_require_pending``. Idempotent by
construction — once expired, a draft never matches the sweep again.

Deterministic-first: no LLM. Every step is fault-tolerant; a failure for
one tenant never breaks the sweep for the rest.

WARNING: imported near FastAPI code — do NOT add
``from __future__ import annotations`` here.
"""

import html
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.config import settings
from backend.models.database import get_service_supabase
from backend.services.email_sender import mask_email, send_email
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

# Two weeks pending without a touch = the owner isn't going to action it,
# and the draft's content (check-ins, reminders) has gone stale anyway.
_STALE_DAYS = 14
# Per-sweep cap per tenant; anything beyond rolls into the next nightly run.
_MAX_EXPIRE_PER_TENANT = 50
_TENANT_BATCH = 200


def _iso_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def expire_stale_drafts(db: Any, client_id: str) -> list[dict[str, Any]]:
    """Expire this tenant's stale pending drafts. Returns the expired rows.

    Selection keys on ``updated_at`` — an edit, recipient fix, or retry
    bumps it, so actively-worked drafts never expire under the owner.
    """
    try:
        stale = (
            tenant_table(db, "os_agent_runs", client_id)
            .select("id, agent_name, deliverable, updated_at")
            .eq("deliverable_status", "pending_approval")
            .lt("updated_at", _iso_days_ago(_STALE_DAYS))
            .order("updated_at", desc=False)
            .limit(_MAX_EXPIRE_PER_TENANT)
            .execute()
        ).data or []
    except Exception:
        logger.warning(
            "os_draft_expiry: stale query failed client_id=%s",
            client_id,
            exc_info=True,
        )
        return []
    if not stale:
        return []

    expired: list[dict[str, Any]] = []
    for row in stale:
        try:
            # Guard the status in the WHERE too: if the owner approves or
            # rejects between our read and this write, we lose the race on
            # purpose and touch nothing.
            updated = (
                tenant_table(db, "os_agent_runs", client_id)
                .update({"deliverable_status": "expired", "updated_at": _now()})
                .eq("id", row["id"])
                .eq("deliverable_status", "pending_approval")
                .execute()
            )
            if updated.data:
                expired.append(row)
        except Exception:
            logger.warning(
                "os_draft_expiry: update failed client_id=%s run_id=%s",
                client_id,
                row.get("id"),
                exc_info=True,
            )
    return expired


async def _notify_owner_digest(
    db: Any, client_id: str, expired: list[dict[str, Any]]
) -> bool:
    """One digest email per sweep per tenant. Never raises."""
    try:
        rows = (
            db.table("tenants")
            .select("owner_email, owner_name")
            .eq("id", client_id)
            .limit(1)
            .execute()
        ).data or []
        owner_email = rows[0].get("owner_email") if rows else None
        if not owner_email:
            return False

        count = len(expired)
        safe_owner = html.escape((rows[0].get("owner_name") or "there"))
        titles = []
        for row in expired[:5]:
            deliverable = row.get("deliverable") or {}
            titles.append(html.escape(deliverable.get("title") or "Untitled draft"))
        listed = "".join(f"<li>{t}</li>" for t in titles)
        more = (
            f"<p>&hellip;and {count - len(titles)} more.</p>"
            if count > len(titles)
            else ""
        )
        await send_email(
            to=owner_email,
            subject=(
                f"{count} old draft{'s' if count != 1 else ''} expired "
                "— nothing was sent"
            ),
            body_html=(
                f"<p>Hi {safe_owner},</p>"
                f"<p>Your AI staff cleared {count} draft"
                f"{'s' if count != 1 else ''} that sat waiting for approval "
                f"for over {_STALE_DAYS} days. Nothing was ever sent to your "
                "customers — the drafts just aged out of your queue.</p>"
                f"<ul>{listed}</ul>"
                f"{more}"
                "<p>Want fresh ones? Ask any agent in your dashboard and it "
                "will re-draft with current data.</p>"
                f'<p><a href="{settings.frontend_url}/dashboard/agent-os" '
                'style="background:#3b82f6;color:#fff;padding:10px 20px;'
                'border-radius:6px;text-decoration:none;font-weight:600;">'
                "Open Agent OS &rarr;</a></p>"
            ),
            tenant_id=client_id,
        )
        logger.info(
            "os_draft_expiry: digest emailed %s for tenant %s (expired=%d)",
            mask_email(owner_email),
            client_id,
            count,
        )
        return True
    except Exception:
        logger.warning(
            "os_draft_expiry: digest failed client_id=%s — expiry already applied",
            client_id,
            exc_info=True,
        )
        return False


async def run_draft_expiry_sweep() -> int:
    """Nightly: expire stale drafts for every active paid tenant.

    Returns count of drafts expired across all tenants.
    """
    db = get_service_supabase()
    try:
        tenants = (
            db.table("tenants")
            .select("id")
            .neq("plan", "free")
            .eq("plan_status", "active")
            .limit(_TENANT_BATCH)
            .execute()
        ).data or []
    except Exception:
        logger.exception("os_draft_expiry: tenant query failed")
        return 0

    total = 0
    for t in tenants:
        expired = expire_stale_drafts(db, t["id"])
        if expired:
            total += len(expired)
            await _notify_owner_digest(db, t["id"], expired)
    if total:
        logger.info("os_draft_expiry: expired %d stale drafts", total)
    return total
