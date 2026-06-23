"""Automation scheduled jobs (extended) — weekly/birthday/recurring functions."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.models.database import get_service_supabase
from backend.services.email_sender import mask_email, send_email
from backend.services.webhook_dispatcher import fire_event_background
from backend.services.automation.trigger import BATCH_LIMIT
from backend.services.churn_watch import run_churn_watch

logger = logging.getLogger(__name__)


async def send_weekly_intelligence_briefs() -> int:
    """Send weekly AI-powered business intelligence briefs to paid tenants.

    Runs in the automation loop. Checks day-of-week (Monday only) and whether
    a brief was already sent this week (via activity_log dedup).

    Gathers 7-day metrics (leads, conversations, appointments, invoices, pipeline),
    sends them to Claude for analysis, and emails the AI-generated insights.

    Returns count of briefs sent.
    """
    from backend.services.llm_runtime import call_claude_messages

    db = get_service_supabase()
    now = datetime.now(timezone.utc)

    # Only run on Mondays (weekday() == 0)
    if now.weekday() != 0:
        return 0

    week_start = (now - timedelta(days=7)).isoformat()
    week_tag = f"weekly_brief_{now.date().isoformat()}"
    sent = 0

    # Fetch paid tenants (not free plan)
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

        # Dedup — one brief per tenant per week
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

        # Gather 7-day metrics
        metrics = {}

        # Leads (uses client_id, not tenant_id)
        try:
            leads_result = (
                db.table("leads")
                .select("id, status, lead_temperature, deal_value", count="exact")
                .eq("client_id", tid)
                .gte("created_at", week_start)
                .limit(200)
                .execute()
            )
            leads_data = leads_result.data or []
            metrics["new_leads"] = len(leads_data)
            metrics["hot_leads"] = sum(
                1 for l in leads_data if l.get("lead_temperature") == "hot"
            )
            metrics["total_deal_value"] = sum(
                float(l.get("deal_value") or 0) for l in leads_data
            )
        except Exception:
            metrics["new_leads"] = 0
            logger.warning(
                "weekly brief: failed to count leads for %s", tid, exc_info=True
            )

        # Conversations
        try:
            conv_result = (
                db.table("conversations")
                .select("id, status", count="exact")
                .eq("client_id", tid)
                .gte("created_at", week_start)
                .limit(1)
                .execute()
            )
            metrics["conversations"] = conv_result.count or 0
        except Exception:
            metrics["conversations"] = 0

        # Appointments
        try:
            appt_result = (
                db.table("appointments")
                .select("id, status", count="exact")
                .eq("tenant_id", tid)
                .gte("created_at", week_start)
                .limit(1)
                .execute()
            )
            metrics["appointments"] = appt_result.count or 0
        except Exception:
            metrics["appointments"] = 0

        # Invoices
        try:
            inv_result = (
                db.table("invoices")
                .select("id, status, total", count="exact")
                .eq("tenant_id", tid)
                .gte("created_at", week_start)
                .limit(200)
                .execute()
            )
            inv_data = inv_result.data or []
            metrics["invoices_sent"] = sum(
                1 for i in inv_data if i.get("status") in ("sent", "viewed", "paid")
            )
            metrics["invoices_paid"] = sum(
                1 for i in inv_data if i.get("status") == "paid"
            )
            metrics["revenue_collected"] = sum(
                float(i.get("total") or 0)
                for i in inv_data
                if i.get("status") == "paid"
            )
        except Exception:
            metrics["invoices_sent"] = 0
            metrics["invoices_paid"] = 0
            metrics["revenue_collected"] = 0

        # Reviews
        try:
            rev_result = (
                db.table("reviews")
                .select("id, rating", count="exact")
                .eq("tenant_id", tid)
                .gte("created_at", week_start)
                .limit(50)
                .execute()
            )
            rev_data = rev_result.data or []
            metrics["new_reviews"] = len(rev_data)
            metrics["avg_rating"] = round(
                sum(r.get("rating", 0) for r in rev_data) / max(len(rev_data), 1), 1
            )
        except Exception:
            metrics["new_reviews"] = 0
            metrics["avg_rating"] = 0

        # Action items pending
        try:
            actions_result = (
                db.table("action_items")
                .select("id", count="exact")
                .eq("tenant_id", tid)
                .eq("status", "pending")
                .limit(1)
                .execute()
            )
            metrics["pending_actions"] = actions_result.count or 0
        except Exception:
            metrics["pending_actions"] = 0

        owner_name = tenant.get("owner_name") or "there"
        biz_name = tenant.get("business_name") or "Your Business"
        biz_type = tenant.get("business_type") or "local business"

        # Generate AI insights
        ai_insights = ""
        try:
            prompt = f"""You are a business intelligence analyst for a {biz_type} called "{biz_name}".

Here are this week's metrics:
- New leads: {metrics.get("new_leads", 0)} (hot: {metrics.get("hot_leads", 0)})
- Conversations: {metrics.get("conversations", 0)}
- Appointments booked: {metrics.get("appointments", 0)}
- Invoices sent: {metrics.get("invoices_sent", 0)}, paid: {metrics.get("invoices_paid", 0)}
- Revenue collected: ${metrics.get("revenue_collected", 0):.2f}
- Pipeline value (new leads): ${metrics.get("total_deal_value", 0):.2f}
- New reviews: {metrics.get("new_reviews", 0)} (avg rating: {metrics.get("avg_rating", 0)})
- Pending action items: {metrics.get("pending_actions", 0)}

Write a brief, actionable weekly intelligence summary (3-5 bullet points). Focus on:
1. What went well this week
2. What needs attention (missed opportunities, overdue items)
3. One specific recommendation to improve next week

Keep it concise, professional, and encouraging. Use actual numbers. No fluff."""

            response = await call_claude_messages(
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

        # Build email
        insights_html = ""
        if ai_insights:
            # Convert markdown-ish bullet points to HTML
            lines = ai_insights.strip().split("\n")
            formatted_lines = []
            for line in lines:
                line = line.strip()
                if line.startswith("- ") or line.startswith("* "):
                    formatted_lines.append(
                        f"<li style='margin-bottom:8px;color:#374151;'>{line[2:]}</li>"
                    )
                elif line:
                    formatted_lines.append(f"<p style='color:#374151;'>{line}</p>")
            insights_html = (
                "<ul style='padding-left:20px;'>" + "".join(formatted_lines) + "</ul>"
            )

        subject = f"Weekly Intelligence Brief — {biz_name}"
        body_html = (
            f"<div style='font-family:sans-serif;max-width:600px;margin:0 auto;'>"
            f"<h2 style='color:#1e293b;'>Hi {owner_name},</h2>"
            f"<p style='color:#374151;'>Here's your weekly business intelligence brief for <strong>{biz_name}</strong>.</p>"
            f"<h3 style='color:#1e293b;margin-top:24px;'>This Week's Numbers</h3>"
            f"<table style='border-collapse:collapse;width:100%;max-width:500px;margin:16px 0;'>"
            f"<tr style='background:#f3f4f6;'>"
            f"<td style='padding:10px 14px;border:1px solid #e5e7eb;font-weight:600;'>New Leads</td>"
            f"<td style='padding:10px 14px;border:1px solid #e5e7eb;text-align:right;'>{metrics.get('new_leads', 0)} ({metrics.get('hot_leads', 0)} hot)</td></tr>"
            f"<tr><td style='padding:10px 14px;border:1px solid #e5e7eb;font-weight:600;'>Conversations</td>"
            f"<td style='padding:10px 14px;border:1px solid #e5e7eb;text-align:right;'>{metrics.get('conversations', 0)}</td></tr>"
            f"<tr style='background:#f3f4f6;'><td style='padding:10px 14px;border:1px solid #e5e7eb;font-weight:600;'>Appointments</td>"
            f"<td style='padding:10px 14px;border:1px solid #e5e7eb;text-align:right;'>{metrics.get('appointments', 0)}</td></tr>"
            f"<tr><td style='padding:10px 14px;border:1px solid #e5e7eb;font-weight:600;'>Revenue Collected</td>"
            f"<td style='padding:10px 14px;border:1px solid #e5e7eb;text-align:right;font-weight:bold;color:#059669;'>${metrics.get('revenue_collected', 0):,.2f}</td></tr>"
            f"<tr style='background:#f3f4f6;'><td style='padding:10px 14px;border:1px solid #e5e7eb;font-weight:600;'>Reviews</td>"
            f"<td style='padding:10px 14px;border:1px solid #e5e7eb;text-align:right;'>{metrics.get('new_reviews', 0)} (avg {metrics.get('avg_rating', 0)})</td></tr>"
            f"<tr><td style='padding:10px 14px;border:1px solid #e5e7eb;font-weight:600;'>Pending Actions</td>"
            f"<td style='padding:10px 14px;border:1px solid #e5e7eb;text-align:right;'>{metrics.get('pending_actions', 0)}</td></tr>"
            f"</table>"
        )
        if insights_html:
            body_html += (
                f"<h3 style='color:#1e293b;margin-top:24px;'>AI Insights</h3>"
                f"{insights_html}"
            )
        body_html += (
            "<p style='margin-top:24px;color:#374151;'>View your full dashboard at "
            "<a href='https://app.agentnexlify.com' style='color:#3b82f6;'>app.agentnexlify.com</a></p>"
            "<p style='color:#6b7280;margin-top:16px;'>— The AgentNexLiFy Team</p></div>"
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
                # Track in activity_log for dedup
                from backend.services.activity import log_activity

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
    db = get_service_supabase()
    now = datetime.now(timezone.utc)

    # Only run on Fridays (weekday() == 4)
    if now.weekday() != 4:
        return 0

    week_start = (now - timedelta(days=7)).isoformat()
    week_tag = f"weekly_digest_{now.date().isoformat()}"
    sent = 0

    # Fetch active paid tenants.
    # Filters: plan != 'free' AND plan_status IN ('active','trialing').
    # This excludes cancelled/paused subscriptions — same guard as pay_gate.py.
    # avg_lead_value is optional — column may not exist on all deployments;
    # the query falls back to 0 gracefully if the column is absent.
    try:
        tenants = (
            db.table("tenants")
            .select("id, business_name, owner_email, owner_name, avg_lead_value, plan_status")
            .neq("plan", "free")
            .in_("plan_status", ["active", "trialing"])
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        # avg_lead_value column may not exist yet — retry without it
        try:
            tenants = (
                db.table("tenants")
                .select("id, business_name, owner_email, owner_name, plan_status")
                .neq("plan", "free")
                .in_("plan_status", ["active", "trialing"])
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

        # Dedup — one digest per tenant per week
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

        # ---- Per-tenant work wrapped for best-effort isolation ----
        # A crash for one tenant must not abort the batch for others.
        try:
            ok = await _build_and_send_digest(
                db=db,
                tenant=tenant,
                tid=tid,
                email=email,
                week_start=week_start,
                week_tag=week_tag,
                # opportunity_html: leave None here.
                # When the os_opportunities lane is ready, the orchestrator
                # can pre-fetch highlights and pass them in.
                # DO NOT import os_opportunities in this module.
                opportunity_html=None,
            )
            if ok:
                sent += 1
        except Exception:
            logger.exception(
                "send_weekly_digest: unhandled error for tenant %s — skipping", tid
            )

    return sent


async def _build_and_send_digest(
    db: Any,
    tenant: dict,
    tid: str,
    email: str,
    week_start: str,
    week_tag: str,
    # --- OPPORTUNITY HIGHLIGHTS SEAM ---
    # Pass pre-formatted HTML from the opportunity scanner here when that lane
    # is ready.  Do NOT import os_opportunities in this module — keep lanes
    # separate.  The outer scheduler can call os_opportunities.get_highlights(tid)
    # and pass the result in.  When None, no opportunity section is rendered.
    opportunity_html: "str | None" = None,
) -> bool:
    """Build + send one tenant's weekly value digest email.

    Returns True if the email was sent successfully, False otherwise.
    Raises only on programming errors (not send/db failures).
    """
    import html as _html
    from backend.services.weekly_value import compute_weekly_value, empty_state_message

    # ---- Gather 7-day value metrics ----
    # compute_weekly_value handles leads (client_id), appointments,
    # conversations, invoices, and agent runs in one fault-tolerant call.
    # avg_lead_value is read from the tenant row (0.0 if absent/unset).
    avg_lead_value = float(tenant.get("avg_lead_value") or 0)
    value = compute_weekly_value(db, tid, avg_lead_value=avg_lead_value)
    leads_count = value["leads_captured"]
    conversations = value["conversations_handled"]

    # Detect zero-activity week before building email body
    total_activity = (
        leads_count
        + value["appointments_booked"]
        + conversations
        + value["invoices_sent"]
        + value["agent_runs_completed"]
    )
    is_empty_week = total_activity == 0

    # Top question — most common user message (exclude greetings / single chars)
    top_question = "N/A"
    try:
        user_msgs = (
            db.table("chat_messages")
            .select("content")
            .eq("tenant_id", tid)
            .eq("role", "user")
            .gte("created_at", week_start)
            .limit(500)
            .execute()
        )
        skip_words = {
            "hi",
            "hello",
            "hey",
            "e",
            "ok",
            "yes",
            "no",
            "thanks",
            "thank you",
        }
        freq: dict[str, int] = {}
        for m in user_msgs.data or []:
            content = (m.get("content") or "").strip()
            if not content or len(content) <= 2:
                continue
            if content.lower() in skip_words:
                continue
            key = content[:120]  # Normalize long messages
            freq[key] = freq.get(key, 0) + 1
        if freq:
            top_question = max(freq, key=freq.get)  # type: ignore[arg-type]
    except Exception:
        logger.warning(
            "send_weekly_digest: failed to find top question for tenant %s",
            tid,
            exc_info=True,
        )

    # ---- Build branded HTML email ----
    # html.escape everything user/customer-controlled: top_question is
    # customer-typed chat content (same injection class as the 2026-06-10
    # approval-notify fix); business/owner names are tenant input.
    owner_name = _html.escape(tenant.get("owner_name") or "there")
    biz_name = _html.escape(tenant.get("business_name") or "Your Business")

    pipeline_val = value["estimated_pipeline_value"]

    if is_empty_week:
        # Empty-state email: helpful "here's what your AI is ready to do" message.
        # No zeros table — that would look like a bug report, not a value digest.
        subject = f"Your AI staff is ready — {tenant.get('business_name') or 'your business'}"
        empty_lines = empty_state_message().split("\n")
        empty_body_parts = []
        for line in empty_lines:
            if line.startswith("•"):
                empty_body_parts.append(
                    f"<li style='margin-bottom:8px;color:#374151;'>{_html.escape(line[1:].strip())}</li>"
                )
            else:
                empty_body_parts.append(
                    f"<p style='color:#374151;'>{_html.escape(line)}</p>"
                )
        # Wrap bullet items in a <ul>
        formatted_empty = ""
        in_list = False
        for part in empty_body_parts:
            if part.startswith("<li"):
                if not in_list:
                    formatted_empty += "<ul style='padding-left:20px;'>"
                    in_list = True
                formatted_empty += part
            else:
                if in_list:
                    formatted_empty += "</ul>"
                    in_list = False
                formatted_empty += part
        if in_list:
            formatted_empty += "</ul>"

        body_html = (
            f"<div style='font-family:sans-serif;max-width:600px;margin:0 auto;'>"
            f"<h2 style='color:#1e293b;'>Hi {owner_name},</h2>"
            f"{formatted_empty}"
            f"<p style='margin-top:24px;'>"
            f"<a href='https://app.agentnexlify.com/dashboard' "
            f"style='color:#6366f1;font-weight:600;text-decoration:none;'>View your dashboard &rarr;</a></p>"
            f"<p style='color:#6b7280;margin-top:16px;'>— The AgentNexLiFy Team</p>"
            f"</div>"
        )
    else:
        subject = f"What your AI staff got done — {tenant.get('business_name') or 'your business'}"

        display_question = _html.escape(
            top_question if len(top_question) <= 80 else top_question[:77] + "..."
        )

        def _row(label: str, val: str, last: bool = False) -> str:
            border = "" if last else "border-bottom:1px solid #334155;"
            return (
                f"<tr style='{border}'>"
                f"<td style='padding:12px 16px;color:#94a3b8;font-weight:600;'>{label}</td>"
                f"<td style='padding:12px 16px;color:#f1f5f9;text-align:right;font-size:18px;font-weight:bold;'>{val}</td></tr>"
            )

        pipeline_str = f"${pipeline_val:,.0f}" if pipeline_val > 0 else "—"

        rows = [
            _row("Leads captured", str(leads_count)),
            _row(
                "Estimated pipeline value",
                f"<span style='color:#10b981;'>{pipeline_str}</span>",
            ),
            _row("Appointments booked", str(value["appointments_booked"])),
            _row(
                "Invoices sent",
                f"{value['invoices_sent']} (${value['invoices_sent_total']:,.0f})",
            ),
            _row(
                "Invoices paid",
                f"{value['invoices_paid']} (${value['invoices_paid_total']:,.0f})",
            ),
            _row("Tasks your AI staff completed", str(value["agent_runs_completed"])),
            _row("Conversations handled", str(conversations)),
            _row(
                "Top customer question",
                f"<span style='font-style:italic;font-size:14px;font-weight:normal;'>&ldquo;{display_question}&rdquo;</span>",
                last=True,
            ),
        ]

        body_html = (
            f"<div style='font-family:sans-serif;max-width:600px;margin:0 auto;'>"
            f"<h2 style='color:#1e293b;'>Hi {owner_name},</h2>"
            f"<p style='color:#374151;'>Here's what your AI staff at {biz_name} got done this week:</p>"
            f"<table style='border-collapse:collapse;width:100%;max-width:500px;margin:16px 0;"
            f"background:#1e293b;border-radius:8px;overflow:hidden;'>"
            + "".join(rows)
            + f"</table>"
        )

        # --- OPPORTUNITY HIGHLIGHTS SEAM ---
        # When the opportunity scanner lane is wired in, the outer scheduler
        # passes opportunity_html here. This module never imports os_opportunities.
        if opportunity_html:
            body_html += (
                f"<h3 style='color:#1e293b;margin-top:24px;'>Opportunities this week</h3>"
                f"<div style='color:#374151;'>{opportunity_html}</div>"
            )

        body_html += (
            f"<p style='margin-top:24px;'>"
            f"<a href='https://app.agentnexlify.com/dashboard/agent-os' "
            f"style='color:#6366f1;font-weight:600;text-decoration:none;'>Ask your AI staff for more &rarr;</a></p>"
            f"<p style='color:#6b7280;margin-top:16px;'>— The AgentNexLiFy Team</p>"
            f"</div>"
        )

    result = await send_email(
        to=email, subject=subject, body_html=body_html, tenant_id=tid
    )
    if result.get("success"):
        logger.info("Sent weekly digest to %s (tenant %s)", mask_email(email), tid)
        from backend.services.activity import log_activity

        log_activity(
            tenant_id=tid,
            activity_type=week_tag,
            description=f"Weekly digest sent: {conversations} conversations, {leads_count} leads, ${pipeline_val:,.0f} pipeline",
        )
        return True
    return False


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
            .filter("date_of_birth", "not.is", "null")
            .filter("email", "not.is", "null")
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("send_birthday_greetings: failed to query leads")
        return 0

    birthday_leads = [
        lead
        for lead in (leads.data or [])
        if lead.get("date_of_birth", "")[5:10] == today_mmdd
    ]

    if not birthday_leads:
        return 0

    tenant_cache: dict[str, dict | None] = {}

    for lead in birthday_leads:
        tenant_id = lead["client_id"]
        lead_id = lead["id"]

        # Dedup: check if already sent this year
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

        subject = f"Happy Birthday from {business_name}!"
        body = (
            f"<h2>Happy Birthday, {customer_name}!</h2>"
            f"<p>Everyone at <strong>{business_name}</strong> wishes you a wonderful birthday!</p>"
            f"<p>As a special thank you for being a valued client, we'd love to see you soon. "
            f"Reply to this email or contact us to schedule your next visit.</p>"
            f"<p>Best wishes,<br>The {business_name} Team</p>"
        )

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
    from datetime import date

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
            .filter("next_invoice_date", "not.is", "null")
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
            subtotal = sum(
                float(i.get("quantity", 1)) * float(i.get("unit_price", 0))
                for i in items
            )
            tax_amount = round(subtotal * tax_rate / 100, 2)
            total = round(subtotal + tax_amount, 2)

            # Generate invoice number
            prefix = f"INV-{datetime.now(timezone.utc).strftime('%Y%m%d')}"
            count_result = (
                db.table("invoices")
                .select("id", count="exact")
                .eq("tenant_id", tenant_id)
                .execute()
            )
            seq = (count_result.count or 0) + 1
            invoice_number = f"{prefix}-{seq:04d}"

            # Calculate due date (same offset as recurrence interval)
            from dateutil.relativedelta import relativedelta

            interval = parent.get("recurrence_interval", "monthly")
            intervals_map = {
                "weekly": relativedelta(weeks=1),
                "biweekly": relativedelta(weeks=2),
                "monthly": relativedelta(months=1),
                "quarterly": relativedelta(months=3),
            }
            delta = intervals_map.get(interval, relativedelta(months=1))
            due_date = (date.today() + delta).isoformat()
            original_next_date = parent["next_invoice_date"]
            next_date = date.fromisoformat(original_next_date) + delta

            # Claim the recurring parent row before inserting the child invoice.
            # This keeps multiple workers from generating the same invoice twice.
            claim_result = (
                db.table("invoices")
                .update(
                    {
                        "next_invoice_date": next_date.isoformat(),
                    }
                )
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

            new_invoice = {
                "tenant_id": tenant_id,
                "lead_id": parent.get("lead_id"),
                "parent_invoice_id": parent_id,
                "invoice_number": invoice_number,
                "items_json": items,
                "subtotal": subtotal,
                "tax_rate": tax_rate,
                "tax_amount": tax_amount,
                "total": total,
                "notes": parent.get("notes"),
                "status": "draft",
                "due_date": due_date,
                "is_recurring": False,  # child is not itself recurring
            }
            try:
                insert_result = db.table("invoices").insert(new_invoice).execute()
            except Exception:
                # Best-effort rollback so the parent can be retried on the next tick.
                try:
                    db.table("invoices").update(
                        {
                            "next_invoice_date": original_next_date,
                        }
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
