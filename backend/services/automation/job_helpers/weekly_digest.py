"""Pure helpers for send_weekly_digest.

DB reads (chat_messages, leads) and HTML email composition.
No external I/O beyond passed-in db client.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "gather_weekly_digest_metrics",
    "build_weekly_digest_email",
]

_TOP_QUESTION_SKIP_WORDS = {
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


def gather_weekly_digest_metrics(db: Any, tenant_id: str, week_start: str) -> dict:
    """Aggregate 7-day chatbot metrics: conversations, messages, leads, top question."""
    conversations = 0
    messages = 0
    try:
        msgs_result = (
            db.table("chat_messages")
            .select("session_id")
            .eq("tenant_id", tenant_id)
            .gte("created_at", week_start)
            .limit(5000)
            .execute()
        )
        msgs_data = msgs_result.data or []
        messages = len(msgs_data)
        conversations = len(
            {m["session_id"] for m in msgs_data if m.get("session_id")}
        )
    except Exception:
        logger.warning(
            "weekly digest: failed to count messages for tenant %s",
            tenant_id,
            exc_info=True,
        )

    leads_count = 0
    try:
        leads_result = (
            db.table("leads")
            .select("id", count="exact")
            .eq("client_id", tenant_id)
            .gte("created_at", week_start)
            .limit(1)
            .execute()
        )
        leads_count = leads_result.count or 0
    except Exception:
        logger.warning(
            "weekly digest: failed to count leads for tenant %s",
            tenant_id,
            exc_info=True,
        )

    top_question = "N/A"
    try:
        user_msgs = (
            db.table("chat_messages")
            .select("content")
            .eq("tenant_id", tenant_id)
            .eq("role", "user")
            .gte("created_at", week_start)
            .limit(500)
            .execute()
        )
        freq: dict[str, int] = {}
        for m in user_msgs.data or []:
            content = (m.get("content") or "").strip()
            if not content or len(content) <= 2:
                continue
            if content.lower() in _TOP_QUESTION_SKIP_WORDS:
                continue
            key = content[:120]
            freq[key] = freq.get(key, 0) + 1
        if freq:
            top_question = max(freq, key=freq.get)  # type: ignore[arg-type]
    except Exception:
        logger.warning(
            "weekly digest: failed to find top question for tenant %s",
            tenant_id,
            exc_info=True,
        )

    return {
        "conversations": conversations,
        "messages": messages,
        "leads_count": leads_count,
        "top_question": top_question,
    }


def build_weekly_digest_email(
    owner_name: str, biz_name: str, metrics: dict
) -> tuple[str, str]:
    """Return (subject, body_html) for the weekly digest email."""
    conversations = metrics["conversations"]
    messages = metrics["messages"]
    leads_count = metrics["leads_count"]
    top_question = metrics["top_question"]

    display_question = (
        top_question if len(top_question) <= 80 else top_question[:77] + "..."
    )

    subject = f"Your weekly chat report — {biz_name}"
    body_html = (
        f"<div style='font-family:sans-serif;max-width:600px;margin:0 auto;'>"
        f"<h2 style='color:#1e293b;'>Hi {owner_name},</h2>"
        f"<p style='color:#374151;'>Here's how your AI assistant performed this week:</p>"
        f"<table style='border-collapse:collapse;width:100%;max-width:500px;margin:16px 0;"
        f"background:#1e293b;border-radius:8px;overflow:hidden;'>"
        f"<tr style='border-bottom:1px solid #334155;'>"
        f"<td style='padding:12px 16px;color:#94a3b8;font-weight:600;'>Conversations</td>"
        f"<td style='padding:12px 16px;color:#f1f5f9;text-align:right;font-size:18px;font-weight:bold;'>{conversations}</td></tr>"
        f"<tr style='border-bottom:1px solid #334155;'>"
        f"<td style='padding:12px 16px;color:#94a3b8;font-weight:600;'>Messages</td>"
        f"<td style='padding:12px 16px;color:#f1f5f9;text-align:right;font-size:18px;font-weight:bold;'>{messages}</td></tr>"
        f"<tr style='border-bottom:1px solid #334155;'>"
        f"<td style='padding:12px 16px;color:#94a3b8;font-weight:600;'>Leads Captured</td>"
        f"<td style='padding:12px 16px;color:#f1f5f9;text-align:right;font-size:18px;font-weight:bold;'>{leads_count}</td></tr>"
        f"<tr>"
        f"<td style='padding:12px 16px;color:#94a3b8;font-weight:600;'>Top Question</td>"
        f"<td style='padding:12px 16px;color:#f1f5f9;text-align:right;font-style:italic;'>"
        f"&ldquo;{display_question}&rdquo;</td></tr>"
        f"</table>"
        f"<p style='margin-top:24px;'>"
        f"<a href='https://app.agentnexlify.com/analytics' "
        f"style='color:#3b82f6;font-weight:600;text-decoration:none;'>View full analytics &rarr;</a></p>"
        f"<p style='color:#6b7280;margin-top:16px;'>— The AgentNexLiFy Team</p>"
        f"</div>"
    )
    return subject, body_html
