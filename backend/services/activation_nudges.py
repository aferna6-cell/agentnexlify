"""Activation nudge sequence — day-1 / day-3 / day-7 emails to stuck tenants.

A tenant is "stuck" when ALL of these are true:
  - signed up 1, 3, or 7+ days ago (± 3-hour window for loop drift)
  - zero leads captured (leads.client_id = tenant.id)
  - not a demo tenant (tenants.is_demo IS NOT TRUE)
  - plan is 'free' or 'trialing' (not yet a paying activated user)

Dedup: one nudge per tenant per stage, ever. Recorded in activity_log with
activity_type "activation_nudge_d1", "activation_nudge_d3", "activation_nudge_d7".

Mirrors dedup pattern from backend/services/demo_reset_job.py and
backend/services/automation/scheduled_jobs_ext.py.

Security: html.escape on all tenant-supplied values (business_name, owner_name)
interpolated into HTML — per 2026-06-10 approval-notify HTML-injection fix precedent.

No `from __future__ import annotations` — would break FastAPI Pydantic resolution.
"""

import html as _html
import logging
from datetime import datetime, timedelta, timezone

from backend.models.database import get_service_supabase
from backend.services.email_sender import send_email
from backend.services.activity import log_activity
from backend.services.internal_tenants import is_internal_tenant
from backend.config import settings

logger = logging.getLogger(__name__)

# How many hours either side of the target boundary we scan.
# This tolerates the 60-second automation loop + multi-worker drift.
_WINDOW_HOURS = 3

# Plans that indicate "not yet activated" for our purposes.
_STUCK_PLANS = {"free", "trialing"}

# Nudge stage definitions: (activity_type, min_age_days, max_age_days)
_STAGES = [
    ("activation_nudge_d1", 1, 1),
    ("activation_nudge_d3", 3, 3),
    ("activation_nudge_d7", 7, 7),
    # Last-call: OPEN-ENDED window (14+ days, max_age None). Catches tenants
    # who aged out of the exact-day windows before this system shipped —
    # 2026-07-09 audit found 2 abandoned signups (16+ days old) that no stage
    # could ever reach. Dedup via activity_log makes it once-per-tenant, ever.
    ("activation_nudge_d14_lastcall", 14, None),
]

# How many tenants to process per run (prevents unbounded work per tick).
_BATCH_LIMIT = 200


def _day1_html(owner_name: str, business_name: str, settings_url: str) -> str:
    safe_owner = _html.escape(owner_name)
    safe_biz = _html.escape(business_name)
    safe_url = _html.escape(settings_url)
    return (
        f"<div style='font-family:sans-serif;max-width:600px;margin:0 auto;'>"
        f"<h2 style='color:#1e293b;'>Hi {safe_owner},</h2>"
        f"<p style='color:#374151;'>Welcome to AgentNexLiFy! Your account for "
        f"<strong>{safe_biz}</strong> is ready &mdash; it just needs one final step.</p>"
        f"<p style='color:#374151;'>Paste your embed code onto your website and your "
        f"AI staff will start capturing leads immediately. It takes about 2 minutes.</p>"
        f"<p style='margin-top:24px;'>"
        f"<a href='{safe_url}' "
        f"style='background:#6366f1;color:#fff;padding:12px 24px;border-radius:6px;"
        f"text-decoration:none;font-weight:600;display:inline-block;'>"
        f"Get my embed code &rarr;</a></p>"
        f"<p style='color:#6b7280;margin-top:24px;font-size:14px;'>"
        f"Questions? Just reply to this email &mdash; we read every one.</p>"
        f"<p style='color:#6b7280;'>— The AgentNexLiFy Team</p></div>"
    )


def _day3_html(owner_name: str, business_name: str) -> str:
    safe_owner = _html.escape(owner_name)
    safe_biz = _html.escape(business_name)
    return (
        f"<div style='font-family:sans-serif;max-width:600px;margin:0 auto;'>"
        f"<h2 style='color:#1e293b;'>Hi {safe_owner},</h2>"
        f"<p style='color:#374151;'>We noticed <strong>{safe_biz}</strong> hasn't "
        f"captured any leads yet. Getting stuck on the embed is totally normal &mdash; "
        f"sometimes it takes 5 minutes with fresh eyes.</p>"
        f"<p style='color:#374151;'><strong>Reply to this email</strong> and one of us "
        f"will walk through it with you personally. No ticket queue, no bots &mdash; "
        f"a real human who's helped dozens of business owners get live.</p>"
        f"<p style='color:#6b7280;margin-top:24px;font-size:14px;'>"
        f"Already embedded and seeing chats? You might just need your first visitor. "
        f"Share your site link on social and the leads will start flowing.</p>"
        f"<p style='color:#6b7280;'>— The AgentNexLiFy Team</p></div>"
    )


def _day7_html(owner_name: str, business_name: str, settings_url: str) -> str:
    safe_owner = _html.escape(owner_name)
    safe_biz = _html.escape(business_name)
    safe_url = _html.escape(settings_url)
    return (
        f"<div style='font-family:sans-serif;max-width:600px;margin:0 auto;'>"
        f"<h2 style='color:#1e293b;'>Hi {safe_owner},</h2>"
        f"<p style='color:#374151;'>One last nudge for <strong>{safe_biz}</strong>.</p>"
        f"<p style='color:#374151;'>Here's what business owners in your first week usually catch:</p>"
        f"<ul style='color:#374151;padding-left:20px;'>"
        f"<li style='margin-bottom:8px;'>Missed calls that would have gone to voicemail "
        f"&mdash; now becoming booked jobs.</li>"
        f"<li style='margin-bottom:8px;'>Visitors browsing at midnight who ask questions "
        f"and leave their number.</li>"
        f"<li style='margin-bottom:8px;'>Appointment requests while you're out on a job, "
        f"answered automatically.</li>"
        f"</ul>"
        f"<p style='color:#374151;'>You're one embed code away from all of that.</p>"
        f"<p style='margin-top:24px;'>"
        f"<a href='{safe_url}' "
        f"style='background:#6366f1;color:#fff;padding:12px 24px;border-radius:6px;"
        f"text-decoration:none;font-weight:600;display:inline-block;'>"
        f"Activate my widget now &rarr;</a></p>"
        f"<p style='color:#6b7280;margin-top:24px;font-size:14px;'>"
        f"Reply to this email anytime &mdash; we're here to help.</p>"
        f"<p style='color:#6b7280;'>— The AgentNexLiFy Team</p></div>"
    )


def _day14_lastcall_html(owner_name: str, business_name: str, settings_url: str) -> str:
    safe_owner = _html.escape(owner_name)
    safe_biz = _html.escape(business_name)
    safe_url = _html.escape(settings_url)
    return (
        f"<div style='font-family:sans-serif;max-width:600px;margin:0 auto;'>"
        f"<h2 style='color:#1e293b;'>Hi {safe_owner},</h2>"
        f"<p style='color:#374151;'>A while back you created an AgentNexLiFy account for "
        f"<strong>{safe_biz}</strong> and never got it live. Your account is still here, "
        f"and finishing takes about 5 minutes.</p>"
        f"<p style='color:#374151;'>Pick your plan, paste one embed code on your site, and "
        f"your AI receptionist starts answering visitors, capturing leads, and booking "
        f"appointments &mdash; nights and weekends included.</p>"
        f"<p style='margin-top:24px;'>"
        f"<a href='{safe_url}' "
        f"style='background:#6366f1;color:#fff;padding:12px 24px;border-radius:6px;"
        f"text-decoration:none;font-weight:600;display:inline-block;'>"
        f"Finish setting up {safe_biz} &rarr;</a></p>"
        f"<p style='color:#6b7280;margin-top:24px;font-size:14px;'>"
        f"Stuck on anything? Reply to this email and a real person will walk you through it. "
        f"This is the last automated email we'll send you about setup.</p>"
        f"<p style='color:#6b7280;'>— The AgentNexLiFy Team</p></div>"
    )


def _build_email(
    stage: str,
    owner_name: str,
    business_name: str,
    settings_url: str,
) -> tuple[str, str]:
    """Return (subject, body_html) for the given stage.

    Tenant-supplied strings are html.escaped inside each helper.
    """
    safe_biz_subject = _html.escape(business_name)
    if stage == "activation_nudge_d1":
        subject = f"Your embed code is ready — {safe_biz_subject}"
        body = _day1_html(owner_name, business_name, settings_url)
    elif stage == "activation_nudge_d3":
        subject = f"Stuck on setup? We'll do it with you — {safe_biz_subject}"
        body = _day3_html(owner_name, business_name)
    elif stage == "activation_nudge_d7":
        subject = f"What owners catch in week one — {safe_biz_subject}"
        body = _day7_html(owner_name, business_name, settings_url)
    else:  # d14 last call
        subject = f"Your AI receptionist is still waiting — {safe_biz_subject}"
        body = _day14_lastcall_html(owner_name, business_name, settings_url)
    return subject, body


async def send_activation_nudges() -> int:
    """Send day-1 / day-3 / day-7 activation nudge emails to stuck tenants.

    Called from the automation loop every 30 minutes. Returns the total
    number of emails sent across all stages.

    Fault-tolerance: one failing tenant never aborts the batch.
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    settings_url = (settings.frontend_url or "https://app.agentnexlify.com").rstrip("/") + "/dashboard/settings"
    total_sent = 0

    for activity_type, target_day, max_age_day in _STAGES:
        # Exact-day stages: [target*24h - window, target*24h + window).
        # Last-call stage (max_age_day None): everything older than target_day —
        # open-ended so pre-existing drop-offs are caught; dedup keeps it one-shot.
        upper_bound = (now - timedelta(days=target_day) + timedelta(hours=_WINDOW_HOURS)).isoformat()

        # Query tenants in this window, not demo, on a stuck plan.
        try:
            query = (
                db.table("tenants")
                .select("id, business_name, owner_email, owner_name, plan, is_demo")
                .lte("created_at", upper_bound)
                .neq("is_demo", True)
                .limit(_BATCH_LIMIT)
            )
            if max_age_day is not None:
                lower_bound = (now - timedelta(days=max_age_day, hours=_WINDOW_HOURS)).isoformat()
                query = query.gte("created_at", lower_bound)
            result = query.execute()
        except Exception:
            logger.exception(
                "send_activation_nudges: failed to query tenants for stage=%s", activity_type
            )
            continue

        for tenant in result.data or []:
            tid = tenant["id"]
            email = tenant.get("owner_email")
            plan = (tenant.get("plan") or "free").lower()

            if not email:
                continue

            # Only nudge free / trialing tenants.
            if plan not in _STUCK_PLANS:
                continue

            # Internal/test/demo-named accounts never get nudges (matters most
            # for the open-ended last-call stage, which sees ALL old tenants).
            if is_internal_tenant(tenant):
                continue

            # Per-tenant fault isolation — a crash here must not stop the rest.
            try:
                _sent = await _process_one_tenant(
                    db=db,
                    tenant_id=tid,
                    email=email,
                    owner_name=tenant.get("owner_name") or "there",
                    business_name=tenant.get("business_name") or "your business",
                    activity_type=activity_type,
                    settings_url=settings_url,
                )
                total_sent += _sent
            except Exception:
                logger.exception(
                    "send_activation_nudges: unhandled error for tenant=%s stage=%s",
                    tid,
                    activity_type,
                )

    return total_sent


async def _process_one_tenant(
    *,
    db,
    tenant_id: str,
    email: str,
    owner_name: str,
    business_name: str,
    activity_type: str,
    settings_url: str,
) -> int:
    """Check dedup + lead count, then send nudge if appropriate.

    Returns 1 if email was sent, 0 otherwise.
    """
    # Dedup: skip if this stage was already sent to this tenant.
    try:
        existing = (
            db.table("activity_log")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .eq("activity_type", activity_type)
            .limit(1)
            .execute()
        )
        if existing.count and existing.count > 0:
            return 0
    except Exception:
        logger.warning(
            "send_activation_nudges: dedup check failed for tenant=%s stage=%s",
            tenant_id,
            activity_type,
            exc_info=True,
        )
        # Conservative: skip rather than double-send on dedup failure.
        return 0

    # Activation signal: check whether any leads exist (leads uses client_id).
    try:
        leads_result = (
            db.table("leads")
            .select("id", count="exact")
            .eq("client_id", tenant_id)
            .limit(1)
            .execute()
        )
        if leads_result.count and leads_result.count > 0:
            # Tenant has at least one lead — they're activated; skip all nudges.
            return 0
    except Exception:
        logger.warning(
            "send_activation_nudges: lead check failed for tenant=%s stage=%s",
            tenant_id,
            activity_type,
            exc_info=True,
        )
        # Conservative: skip rather than nudge someone who may already be active.
        return 0

    # Build and send the nudge email.
    subject, body_html = _build_email(activity_type, owner_name, business_name, settings_url)

    try:
        result = await send_email(
            to=email,
            subject=subject,
            body_html=body_html,
            tenant_id=tenant_id,
        )
    except Exception:
        logger.exception(
            "send_activation_nudges: send_email raised for tenant=%s stage=%s",
            tenant_id,
            activity_type,
        )
        return 0

    if not result.get("success"):
        logger.warning(
            "send_activation_nudges: send_email returned failure for tenant=%s stage=%s detail=%s",
            tenant_id,
            activity_type,
            result.get("detail"),
        )
        return 0

    logger.info(
        "send_activation_nudges: sent stage=%s to tenant=%s",
        activity_type,
        tenant_id,
    )

    # Record the send for dedup. Fire-and-forget via log_activity.
    log_activity(
        tenant_id=tenant_id,
        activity_type=activity_type,
        description=f"Activation nudge sent ({activity_type})",
    )

    return 1
