"""Background automation loop + scheduled-content tasks.

Extracted from `backend/main.py` per Rule 9 (don't extend god classes — factor
first). Original main.py reached 927 lines.

Public entry: `run_automation_loop()` — long-running coroutine invoked from
the FastAPI lifespan handler. All other names are implementation details kept
module-private.
"""

import asyncio
import logging
import os
import socket
import uuid

from backend.config import is_production
from backend.services.task_utils import safe_create_task

logger = logging.getLogger(__name__)

_LOCK_OWNER = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex}"


def _coerce_rpc_bool(data) -> bool:
    if isinstance(data, bool):
        return data
    if isinstance(data, str):
        return data.strip().lower() == "true"
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, bool):
            return first
        if isinstance(first, dict):
            value = next(iter(first.values()), False)
            return _coerce_rpc_bool(value)
    return bool(data)


async def _safe_run(name: str, fn, timeout: float = 30.0):
    """Run an automation function with a timeout. Logs results and exceptions."""
    try:
        result = await asyncio.wait_for(fn(), timeout=timeout)
        if result:
            logger.info("Automation loop: %s returned %s", name, result)
    except asyncio.TimeoutError:
        logger.warning("Automation loop: %s timed out after %.0fs", name, timeout)
    except Exception:
        logger.exception("Automation loop: %s failed", name)


def _try_acquire_automation_lock(lock_name: str, ttl_seconds: int = 90) -> bool:
    """Acquire a short DB-backed lock so only one worker runs scheduler work."""
    try:
        from backend.models.database import get_service_supabase

        result = (
            get_service_supabase()
            .rpc(
                "try_acquire_automation_lock",
                {
                    "p_name": lock_name,
                    "p_owner": _LOCK_OWNER,
                    "p_ttl_seconds": ttl_seconds,
                },
            )
            .execute()
        )
        return _coerce_rpc_bool(result.data)
    except Exception:
        if is_production():
            logger.exception("Automation lock unavailable in production")
            return False
        logger.warning("Automation lock unavailable; using dev fallback", exc_info=True)
        return True


def _release_automation_lock(lock_name: str) -> None:
    try:
        from backend.models.database import get_service_supabase

        get_service_supabase().rpc(
            "release_automation_lock",
            {"p_name": lock_name, "p_owner": _LOCK_OWNER},
        ).execute()
    except Exception:
        logger.warning("Failed to release automation lock %s", lock_name, exc_info=True)


async def _recover_stalled_campaigns():
    """Mark marketing campaigns stuck in 'sending' for >30 minutes as 'failed'."""
    from datetime import datetime, timedelta, timezone
    from backend.models.database import get_service_supabase

    db = get_service_supabase()
    stale_cutoff = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    try:
        stale_started = (
            db.table("marketing_campaigns")
            .select("id, name, tenant_id")
            .eq("status", "sending")
            .lt("sending_started_at", stale_cutoff)
            .limit(50)
            .execute()
        )
        stale_missing_start = []
        try:
            stale_missing_start = (
                db.table("marketing_campaigns")
                .select("id, name, tenant_id")
                .eq("status", "sending")
                .is_("sending_started_at", "null")
                .lt("created_at", stale_cutoff)
                .limit(50)
                .execute()
            ).data or []
        except Exception:
            stale_missing_start = []

        stalled_rows = (stale_started.data or []) + stale_missing_start
        if not stalled_rows:
            return 0
        stalled_ids = list({row["id"] for row in stalled_rows if row.get("id")})
        db.table("marketing_campaigns").update({"status": "failed"}).in_(
            "id", stalled_ids
        ).execute()
        for cid in stalled_ids:
            logger.warning("Marked stalled campaign %s as failed", cid)
        return len(stalled_ids)
    except Exception:
        logger.exception("_recover_stalled_campaigns failed")
        return 0


async def _process_scheduled_posts():
    """Auto-publish social media posts whose scheduled_for has passed."""
    from datetime import datetime, timezone
    from backend.models.database import get_service_supabase

    db = get_service_supabase()
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        due_posts = (
            db.table("social_posts")
            .select("id, tenant_id, platform, content")
            .eq("status", "scheduled")
            .lte("scheduled_for", now_iso)
            .limit(100)
            .execute()
        )
        if not due_posts.data:
            return 0

        published = 0
        for post in due_posts.data:
            try:
                db.table("social_posts").update(
                    {
                        "status": "published",
                        "published_at": now_iso,
                    }
                ).eq("id", post["id"]).execute()
                published += 1
                logger.info(
                    "Auto-published scheduled social post %s (%s) for tenant %s",
                    post["id"],
                    post["platform"],
                    post["tenant_id"],
                )
            except Exception:
                logger.exception("Failed to auto-publish social post %s", post["id"])

        return published
    except Exception:
        logger.exception("_process_scheduled_posts failed")
        return 0


async def _process_scheduled_campaigns():
    """Auto-send marketing campaigns whose scheduled_for has passed."""
    from datetime import datetime, timezone
    from backend.models.database import get_service_supabase
    from backend.routers.marketing_campaigns import (
        _query_target_leads,
        _send_campaign_background,
    )

    db = get_service_supabase()
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        due_campaigns = (
            db.table("marketing_campaigns")
            .select("*")
            .eq("status", "scheduled")
            .lte("scheduled_for", now_iso)
            .limit(20)
            .execute()
        )
        if not due_campaigns.data:
            return 0

        dispatched = 0
        for campaign in due_campaigns.data:
            campaign_id = campaign["id"]
            tenant_id = campaign["tenant_id"]
            target_filter = campaign.get("target_filter") or {}

            leads = _query_target_leads(db, tenant_id, target_filter)
            if not leads:
                db.table("marketing_campaigns").update(
                    {
                        "status": "sent",
                        "sent_at": now_iso,
                        "total_recipients": 0,
                        "total_sent": 0,
                    }
                ).eq("id", campaign_id).execute()
                logger.info(
                    "Scheduled campaign %s had no matching leads — marked as sent",
                    campaign_id,
                )
                continue

            db.table("marketing_campaigns").update(
                {
                    "status": "sending",
                    "sending_started_at": now_iso,
                }
            ).eq("id", campaign_id).execute()

            safe_create_task(
                _send_campaign_background(campaign_id, tenant_id, leads, campaign),
                name=f"campaign_{campaign_id}",
            )
            dispatched += 1
            logger.info(
                "Auto-dispatched scheduled campaign %s for tenant %s (%d leads)",
                campaign_id,
                tenant_id,
                len(leads),
            )

        return dispatched
    except Exception:
        logger.exception("_process_scheduled_campaigns failed")
        return 0


async def run_automation_loop():
    """Background loop that runs automation tasks on a tiered schedule.

    With multiple Uvicorn workers, each worker runs its own loop. A DB-backed
    short lease ensures only one worker performs scheduler work per tick.

    Tiers:
      - Every 60s  (every tick): core sequences, no-response leads, reminders
      - Every 5min (tick % 5):   notifications, review requests, onboarding,
                                  CSAT, scheduled post publishing, scheduled
                                  campaign sending
      - Every 30min (tick % 30): heavy/infrequent tasks (monthly reports,
                                  briefs, recurring invoices)
    """
    import random

    await asyncio.sleep(random.uniform(0, 30))  # Stagger workers
    from backend.services import email_sequences
    from backend.services.daily_briefing import send_daily_briefings
    from backend.services.noshow_recovery import process_noshow_recovery
    from backend.services.automation_engine import (
        check_new_reviews,
        check_no_response_leads,
        process_pending_steps,
        send_appointment_reminders,
        send_csat_surveys,
        send_invoice_payment_reminders,
        send_monthly_reports,
        process_recurring_invoices,
        send_pending_review_requests,
        send_rebook_suggestions,
        send_onboarding_emails,
        send_portal_links,
        send_weekly_intelligence_briefs,
        send_weekly_digest,
        send_birthday_greetings,
        send_aftercare_instructions,
        schedule_automation_check,
    )

    tick = 0
    while True:
        tick += 1
        lock_name = "automation_loop_tick"
        if not _try_acquire_automation_lock(lock_name):
            await asyncio.sleep(60)
            continue

        try:
            core_tasks = [
                _safe_run("process_pending_steps", process_pending_steps),
                _safe_run("check_no_response_leads", check_no_response_leads),
                _safe_run("send_appointment_reminders", send_appointment_reminders),
            ]

            if tick % 5 == 0:
                core_tasks.extend(
                    [
                        _safe_run(
                            "send_pending_review_requests", send_pending_review_requests
                        ),
                        _safe_run("send_rebook_suggestions", send_rebook_suggestions),
                        _safe_run("send_onboarding_emails", send_onboarding_emails),
                        _safe_run("send_portal_links", send_portal_links),
                        _safe_run("send_csat_surveys", send_csat_surveys),
                        _safe_run("check_new_reviews", check_new_reviews),
                        _safe_run(
                            "send_invoice_payment_reminders",
                            send_invoice_payment_reminders,
                        ),
                        _safe_run(
                            "send_aftercare_instructions", send_aftercare_instructions
                        ),
                        _safe_run("process_scheduled_posts", _process_scheduled_posts),
                        _safe_run(
                            "process_scheduled_campaigns", _process_scheduled_campaigns
                        ),
                        _safe_run(
                            "recover_stalled_campaigns", _recover_stalled_campaigns
                        ),
                        _safe_run(
                            "run_sequence_processor",
                            email_sequences.run_sequence_processor,
                        ),
                        _safe_run(
                            "schedule_automation_check", schedule_automation_check
                        ),
                        _safe_run("process_noshow_recovery", process_noshow_recovery),
                    ]
                )

            if tick % 30 == 0:
                core_tasks.extend(
                    [
                        _safe_run("send_monthly_reports", send_monthly_reports),
                        _safe_run(
                            "process_recurring_invoices", process_recurring_invoices
                        ),
                        _safe_run(
                            "send_weekly_intelligence_briefs",
                            send_weekly_intelligence_briefs,
                        ),
                        _safe_run("send_weekly_digest", send_weekly_digest),
                        _safe_run("send_birthday_greetings", send_birthday_greetings),
                        _safe_run("send_daily_briefings", send_daily_briefings),
                    ]
                )

            await asyncio.gather(*core_tasks)
        finally:
            _release_automation_lock(lock_name)
        await asyncio.sleep(60)
