"""Pure helpers for send_weekly_intelligence_briefs.

DB reads (metrics gathering), AI prompt construction, and HTML email
composition. No external I/O beyond passed-in db client.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "gather_weekly_brief_metrics",
    "build_weekly_brief_ai_prompt",
    "format_ai_insights_html",
    "build_weekly_brief_email",
]


def gather_weekly_brief_metrics(db: Any, tenant_id: str, week_start: str) -> dict:
    """Aggregate 7-day metrics for the weekly intelligence brief.

    Reads leads, conversations, appointments, invoices, reviews, action_items
    from Supabase. Each block failure is non-fatal — fills 0 and warns.
    """
    metrics: dict[str, Any] = {}

    # Leads (uses client_id, not tenant_id)
    try:
        leads_result = (
            db.table("leads")
            .select("id, status, lead_temperature, deal_value", count="exact")
            .eq("client_id", tenant_id)
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
            "weekly brief: failed to count leads for %s", tenant_id, exc_info=True
        )

    # Conversations
    try:
        conv_result = (
            db.table("conversations")
            .select("id, status", count="exact")
            .eq("client_id", tenant_id)
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
            .eq("tenant_id", tenant_id)
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
            .eq("tenant_id", tenant_id)
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
            .eq("tenant_id", tenant_id)
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
            .eq("tenant_id", tenant_id)
            .eq("status", "pending")
            .limit(1)
            .execute()
        )
        metrics["pending_actions"] = actions_result.count or 0
    except Exception:
        metrics["pending_actions"] = 0

    return metrics


def build_weekly_brief_ai_prompt(metrics: dict, biz_name: str, biz_type: str) -> str:
    """Build the prompt sent to Claude to generate the weekly insights bullets."""
    return f"""You are a business intelligence analyst for a {biz_type} called "{biz_name}".

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


def format_ai_insights_html(ai_insights: str) -> str:
    """Convert markdown-ish bullets/paragraphs into HTML for the brief email."""
    if not ai_insights:
        return ""
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
    return (
        "<ul style='padding-left:20px;'>" + "".join(formatted_lines) + "</ul>"
    )


def build_weekly_brief_email(
    owner_name: str, biz_name: str, metrics: dict, insights_html: str
) -> tuple[str, str]:
    """Return (subject, body_html) for the weekly intelligence brief email."""
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
    return subject, body_html
