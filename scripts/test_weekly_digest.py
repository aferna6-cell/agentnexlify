"""One-off test: simulate and send the weekly digest email for MTOptions tenant.

Usage:
    cd /home/aidan/agentnexlify
    python -m scripts.test_weekly_digest

Sends the same branded HTML that send_weekly_digest() would produce,
but targets a specific email address and skips the day-of-week / dedup checks.
"""

import logging
import sys
from datetime import datetime, timedelta, timezone

import resend

# -- bootstrap imports (project root must be on sys.path) --------------------
sys.path.insert(0, "/home/aidan/agentnexlify")

from backend.config import settings
from backend.models.database import get_supabase

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

# -- constants ---------------------------------------------------------------
TENANT_ID = "6d76f24b-dd71-470c-9b86-03ee35b7e887"
RECIPIENT = "aidanfernandes31@gmail.com"
FROM_ADDRESS = "AgentNexLiFy <noreply@agentnexlify.com>"


def main() -> None:
    # Verify Resend key is available
    if not settings.resend_api_key:
        logger.error("settings.resend_api_key is empty -- cannot send email")
        sys.exit(1)

    db = get_supabase()
    now = datetime.now(timezone.utc)
    week_start = (now - timedelta(days=7)).isoformat()

    # ---- 1. Conversations & messages (from chat_messages, last 7 days) -----
    conversations = 0
    messages = 0
    try:
        msgs_result = (
            db.table("chat_messages")
            .select("session_id")
            .eq("tenant_id", TENANT_ID)
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
        logger.exception("Failed to count messages")

    logger.info("Conversations: %d | Messages: %d", conversations, messages)

    # ---- 2. Leads captured (uses client_id, NOT tenant_id!) ----------------
    leads_count = 0
    try:
        leads_result = (
            db.table("leads")
            .select("id", count="exact")
            .eq("client_id", TENANT_ID)
            .gte("created_at", week_start)
            .limit(1)
            .execute()
        )
        leads_count = leads_result.count or 0
    except Exception:
        logger.exception("Failed to count leads")

    logger.info("Leads captured: %d", leads_count)

    # ---- 3. Top question (exclude greetings / single chars) ----------------
    top_question = "N/A"
    try:
        user_msgs = (
            db.table("chat_messages")
            .select("content")
            .eq("tenant_id", TENANT_ID)
            .eq("role", "user")
            .gte("created_at", week_start)
            .limit(500)
            .execute()
        )
        skip_words = {
            "hi", "hello", "hey", "e", "ok", "yes", "no", "thanks", "thank you",
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
        logger.exception("Failed to find top question")

    logger.info("Top question: %s", top_question)

    # ---- 4. Build branded HTML (same template as send_weekly_digest) -------
    biz_name = "MTOptions"
    owner_name = "there"

    # Fetch real owner_name if available
    try:
        tenant_row = (
            db.table("tenants")
            .select("owner_name")
            .eq("id", TENANT_ID)
            .limit(1)
            .execute()
        )
        if tenant_row.data:
            owner_name = tenant_row.data[0].get("owner_name") or "there"
    except Exception:
        logger.exception("Failed to fetch tenant owner_name")

    subject = f"Your weekly chat report \u2014 {biz_name}"

    display_question = (
        top_question if len(top_question) <= 80 else top_question[:77] + "..."
    )

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
        f"<p style='color:#6b7280;margin-top:16px;'>\u2014 The AgentNexLiFy Team</p>"
        f"</div>"
    )

    # ---- 5. Send via Resend API directly -----------------------------------
    resend.api_key = settings.resend_api_key

    send_params = {
        "from": FROM_ADDRESS,
        "to": [RECIPIENT],
        "subject": subject,
        "html": body_html,
    }

    logger.info("Sending digest email to %s ...", RECIPIENT)
    try:
        result = resend.Emails.send(send_params)
        logger.info("Email sent successfully!")
        _print_summary(result, subject, RECIPIENT, conversations, messages, leads_count, display_question)
    except Exception as primary_err:
        logger.warning(
            "Primary send failed (%s). Falling back to sandbox domain + account owner email.",
            primary_err,
        )
        # Resend sandbox: can only send from onboarding@resend.dev to the
        # account owner email when the custom domain is not verified.
        FALLBACK_FROM = "AgentNexLiFy <onboarding@resend.dev>"
        FALLBACK_TO = "aferna6@g.clemson.edu"
        send_params["from"] = FALLBACK_FROM
        send_params["to"] = [FALLBACK_TO]
        try:
            result = resend.Emails.send(send_params)
            logger.info("Email sent via sandbox fallback!")
            _print_summary(result, subject, FALLBACK_TO, conversations, messages, leads_count, display_question)
            print(f"\nNOTE: agentnexlify.com domain is NOT verified on Resend.")
            print(f"      Email was sent to {FALLBACK_TO} instead of {RECIPIENT}.")
            print(f"      Verify the domain at https://resend.com/domains to unlock full sending.")
        except Exception:
            logger.exception("Fallback send also failed")
            sys.exit(1)


def _print_summary(
    result: dict,
    subject: str,
    to: str,
    conversations: int,
    messages: int,
    leads_count: int,
    display_question: str,
) -> None:
    print(f"\nResult: {result}")
    print(f"\nSubject: {subject}")
    print(f"To: {to}")
    print(f"Conversations: {conversations}")
    print(f"Messages: {messages}")
    print(f"Leads: {leads_count}")
    print(f"Top question: {display_question}")


if __name__ == "__main__":
    main()
