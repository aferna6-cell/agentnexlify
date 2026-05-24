"""Automation scheduled jobs (extended) — weekly/birthday/recurring functions.

Top-level orchestration only. Pure helpers (metrics gathering, AI prompts,
HTML composition, invoice math) live in ``job_helpers/``. ``send_email``,
``get_service_supabase``, ``datetime``, and ``fire_event_background`` stay in
this module so test patches against this namespace continue to work.
"""

import logging
from datetime import date, datetime, timedelta, timezone

from backend.models.database import get_service_supabase
from backend.services.automation.job_helpers.birthday import (
    build_birthday_greeting_email,
    filter_birthday_leads,
)
from backend.services.automation.job_helpers.recurring_invoice import (
    build_new_invoice_payload,
    compute_invoice_totals,
    compute_next_invoice_dates,
    generate_invoice_number,
)
from backend.services.automation.job_helpers.weekly_brief import (
    build_weekly_brief_ai_prompt,
    build_weekly_brief_email,
    format_ai_insights_html,
    gather_weekly_brief_metrics,
)
from backend.services.automation.job_helpers.weekly_digest import (
    build_weekly_digest_email,
    gather_weekly_digest_metrics,
)
from backend.services.automation.trigger import BATCH_LIMIT
from backend.services.email_sender import send_email
from backend.services.webhook_dispatcher import fire_event_background

logger = logging.getLogger(__name__)

__all__ = [
    "send_weekly_intelligence_briefs",
    "send_weekly_digest",
    "send_birthday_greetings",
    "process_recurring_invoices",
    # Re-exported so test patches on scheduled_jobs_ext.<name> keep working
    "send_email",
    "get_service_supabase",
    "fire_event_background",
    "datetime",
    "timedelta",
    "timezone",
    "BATCH_LIMIT",
]


async def send_weekly_intelligence_briefs() -> int:
    """Send weekly AI-powered business intelligence briefs to paid tenants.

    Runs in the automation loop. Checks day-of-week (Monday only) and whether
    a brief was already sent this week (via activity_log dedup).

    Returns count of briefs sent.
    """
    from backend.services.activity import log_activity
    from backend.services.llm_runtime import call_claude_messages_sync

    db = get_service_supabase()
    now = datetime.now(timezone.utc)

    if now.weekday() != 0:
        return 0

    week_start = (now - timedelta(days=7)).isoformat()
    week_tag = f"weekly_brief_{now.date().isoformat()}"
    sent = 0

    try:
        tenants = (
            db.table("tenants")
            .select("id, business_name, owner_email, owner_name, plan, business_type")
            .neq("plan", "free")
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("send_weekly_intelligence_briefs: failed to query tenants")
        return 0

    for tenant in tenants.data or []:
        tid = tenant["id"]
        email = tenant.get("owner_email")
        if not email:
            continue

        try:
            existing = (
                db.table("activity_log")
                .select("id", count="exact")
                .eq("tenant_id", tid)
                .eq("activity_type", week_tag)
                .limit(1)
                .execute()
            )
            if existing.count and existing.count > 0:
                continue
        except Exception:
            logger.warning(
                "send_weekly_intelligence_briefs: dedup check failed for tenant %s", tid
            )
            continue

        metrics = gather_weekly_brief_metrics(db, tid, week_start)

        owner_name = tenant.get("owner_name") or "there"
        biz_name = tenant.get("business_name") or "Your Business"
        biz_type = tenant.get("business_type") or "local business"

        ai_insights = ""
        try:
            prompt = build_weekly_brief_ai_prompt(metrics, biz_name, biz_type)
            response = call_claude_messages_sync(
                operation="automation.weekly_intelligence_brief",
                model="claude-sonnet-4-6",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
                timeout=30.0,
                max_retries=1,
                retry_delay_seconds=0.75,
                metadata={
                    "tenant_id": tid,
                    "business_type": biz_type,
                    "new_leads": metrics.get("new_leads", 0),
                    "conversations": metrics.get("conversations", 0),
                    "appointments": metrics.get("appointments", 0),
                    "revenue_collected": metrics.get("revenue_collected", 0),
                    "pending_actions": metrics.get("pending_actions", 0),
                },
            )
            ai_insights = response.text
        except Exception:
            logger.warning(
                "weekly brief: AI analysis failed for tenant %s", tid, exc_info=True
            )

        insights_html = format_ai_insights_html(ai_insights)
        subject, body_html = build_weekly_brief_email(
            owner_name, biz_name, metrics, insights_html
        )

        try:
            result = await send_email(
                to=email, subject=subject, body_html=body_html, tenant_id=tid
            )
            if result.get("success"):
                sent += 1
                logger.info(
                    "Sent weekly intelligence brief to %s (tenant %s)", email, tid
                )
                log_activity(
                    tenant_id=tid,
                    activity_type=week_tag,
                    description=f"Weekly intelligence brief sent: {metrics.get('new_leads', 0)} leads, ${metrics.get('revenue_collected', 0):.2f} revenue",
                )
        except Exception:
            logger.exception(
                "Failed to send weekly brief to %s (tenant %s)", email, tid
            )

    return sent


async def send_weekly_digest() -> int:
    """Send a weekly chatbot performance digest email to paid tenants.

    Runs in the automation loop (30-min tier). Only executes on Fridays
    (weekday == 4). Gathers 7-day chat metrics and emails a branded
    summary to each tenant. Deduped via activity_log.

    Returns count of emails sent.
    """
    from backend.services.activity import log_activity

    db = get_service_supabase()
    now = datetime.now(timezone.utc)

    if now.weekday() != 4:
        return 0

    week_start = (now - timedelta(days=7)).isoformat()
    week_tag = f"weekly_digest_{now.date().isoformat()}"
    sent = 0

    try:
        tenants = (
            db.table("tenants")
            .select("id, business_name, owner_email, owner_name")
            .neq("plan", "free")
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("send_weekly_digest: failed to query tenants")
        return 0

    for tenant in tenants.data or []:
        tid = tenant["id"]
        email = tenant.get("owner_email")
        if not email:
            continue

        try:
            existing = (
                db.table("activity_log")
                .select("id", count="exact")
                .eq("tenant_id", tid)
                .eq("activity_type", week_tag)
                .limit(1)
                .execute()
            )
            if existing.count and existing.count > 0:
                continue
        except Exception:
            logger.warning("send_weekly_digest: dedup check failed for tenant %s", tid)
            continue

        metrics = gather_weekly_digest_metrics(db, tid, week_start)
        owner_name = tenant.get("owner_name") or "there"
        biz_name = tenant.get("business_name") or "Your Business"
        subject, body_html = build_weekly_digest_email(owner_name, biz_name, metrics)

        try:
            result = await send_email(
                to=email, subject=subject, body_html=body_html, tenant_id=tid
            )
            if result.get("success"):
                sent += 1
                logger.info("Sent weekly digest to %s (tenant %s)", email, tid)
                log_activity(
                    tenant_id=tid,
                    activity_type=week_tag,
                    description=(
                        f"Weekly digest sent: {metrics['conversations']} conversations, "
                        f"{metrics['messages']} messages, {metrics['leads_count']} leads"
                    ),
                )
        except Exception:
            logger.exception(
                "Failed to send weekly digest to %s (tenant %s)", email, tid
            )

    return sent


async def send_birthday_greetings() -> int:
    """Check for leads with birthdays today and send greeting emails.

    Deduped via activity_log (birthday_greeting_{year} per lead).
    Runs daily, checks all tenants with paid plans.
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    today_mmdd = now.strftime("%m-%d")
    current_year = now.year
    sent = 0

    try:
        leads = (
            db.table("leads")
            .select("id, client_id, name, email, date_of_birth")
            .not_.is_("date_of_birth", "null")
            .not_.is_("email", "null")
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("send_birthday_greetings: failed to query leads")
        return 0

    birthday_leads = filter_birthday_leads(leads.data or [], today_mmdd)
    if not birthday_leads:
        return 0

    tenant_cache: dict[str, dict | None] = {}

    for lead in birthday_leads:
        tenant_id = lead["client_id"]
        lead_id = lead["id"]

        try:
            tag = f"birthday_greeting_{current_year}"
            existing = (
                db.table("activity_log")
                .select("id")
                .eq("tenant_id", tenant_id)
                .eq("lead_id", lead_id)
                .eq("activity_type", tag)
                .limit(1)
                .execute()
            )
            if existing.data:
                continue
        except Exception:
            logger.warning("Dedup check failed in sequence enrollment", exc_info=True)

        if tenant_id not in tenant_cache:
            try:
                t = (
                    db.table("tenants")
                    .select("business_name, plan")
                    .eq("id", tenant_id)
                    .limit(1)
                    .execute()
                )
                tenant_cache[tenant_id] = t.data[0] if t.data else None
            except Exception:
                tenant_cache[tenant_id] = None

        tenant = tenant_cache.get(tenant_id)
        if not tenant or (tenant.get("plan") or "free") == "free":
            continue

        business_name = tenant.get("business_name") or "Us"
        customer_name = lead.get("name") or "there"
        subject, body = build_birthday_greeting_email(customer_name, business_name)

        try:
            result = await send_email(
                to=lead["email"], subject=subject, body_html=body, tenant_id=tenant_id
            )
            if result.get("success"):
                sent += 1
        except Exception:
            logger.exception("Failed to send birthday greeting to lead %s", lead_id)

        try:
            db.table("activity_log").insert(
                {
                    "tenant_id": tenant_id,
                    "lead_id": lead_id,
                    "activity_type": f"birthday_greeting_{current_year}",
                    "description": f"Birthday greeting sent to {customer_name}",
                }
            ).execute()
        except Exception:
            logger.warning(
                "Failed to log birthday greeting for lead %s", lead_id, exc_info=True
            )

    return sent


async def process_recurring_invoices() -> int:
    """Create new invoices from recurring invoices whose next_invoice_date has arrived.

    Runs every 30 min in the automation loop. For each recurring invoice with
    next_invoice_date <= today:
    1. Create a new draft invoice with the same line items
    2. Advance the parent's next_invoice_date by the recurrence_interval
    3. Log the activity
    """
    db = get_service_supabase()
    today_str = date.today().isoformat()

    try:
        due = (
            db.table("invoices")
            .select(
                "id, tenant_id, lead_id, items_json, tax_rate, notes, recurrence_interval, next_invoice_date, invoice_number"
            )
            .eq("is_recurring", True)
            .lte("next_invoice_date", today_str)
            .not_.is_("next_invoice_date", "null")
            .neq("status", "cancelled")
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("process_recurring_invoices: query failed")
        return 0

    if not due.data:
        return 0

    created = 0
    for parent in due.data:
        parent_id = parent["id"]
        tenant_id = parent["tenant_id"]
        try:
            items = parent.get("items_json") or []
            tax_rate = float(parent.get("tax_rate") or 0)
            subtotal, tax_amount, total = compute_invoice_totals(items, tax_rate)

            invoice_number = generate_invoice_number(
                db, tenant_id, datetime.now(timezone.utc)
            )
            interval = parent.get("recurrence_interval", "monthly")
            original_next_date = parent["next_invoice_date"]
            _, due_date, next_date = compute_next_invoice_dates(
                interval, date.today(), original_next_date
            )

            # Claim the recurring parent row before inserting the child invoice
            # so multiple workers cannot generate the same child invoice twice.
            claim_result = (
                db.table("invoices")
                .update({"next_invoice_date": next_date.isoformat()})
                .eq("id", parent_id)
                .eq("next_invoice_date", original_next_date)
                .select("id")
                .execute()
            )
            if not claim_result.data:
                logger.info(
                    "Skipping recurring invoice %s because another worker already claimed it",
                    parent_id,
                )
                continue

            new_invoice = build_new_invoice_payload(
                tenant_id=tenant_id,
                parent=parent,
                invoice_number=invoice_number,
                items=items,
                subtotal=subtotal,
                tax_rate=tax_rate,
                tax_amount=tax_amount,
                total=total,
                due_date=due_date,
            )
            try:
                insert_result = db.table("invoices").insert(new_invoice).execute()
            except Exception:
                try:
                    db.table("invoices").update(
                        {"next_invoice_date": original_next_date}
                    ).eq("id", parent_id).eq(
                        "next_invoice_date", next_date.isoformat()
                    ).execute()
                except Exception:
                    logger.warning(
                        "Failed to roll back recurring invoice claim for %s",
                        parent_id,
                        exc_info=True,
                    )
                raise

            created_invoice = insert_result.data[0] if insert_result.data else {}
            created += 1
            logger.info(
                "Created recurring invoice %s from parent %s for tenant %s (next: %s)",
                invoice_number,
                parent_id,
                tenant_id,
                next_date.isoformat(),
            )

            try:
                fire_event_background(
                    tenant_id,
                    "invoice.created",
                    {
                        "invoice_id": created_invoice.get("id"),
                        "invoice_number": invoice_number,
                        "total": total,
                        "status": "draft",
                        "recurring_from": parent_id,
                    },
                )
            except Exception:
                logger.exception(
                    "Failed to enqueue invoice.created webhook for recurring invoice %s",
                    parent_id,
                )

        except Exception:
            logger.exception("Failed to process recurring invoice %s", parent_id)

    return created
