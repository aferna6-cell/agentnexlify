"""Agent notification service — email and SMS alerts."""

from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from backend.config import settings
from backend.models.schemas import ClientRow

logger = logging.getLogger(__name__)

URGENCY_SUBJECTS = {
    "hot_lead": "AgentNexLiFy: Hot Lead Alert",
    "escalation": "AgentNexLiFy: Lead Escalation — Needs Human",
    "callback_requested": "AgentNexLiFy: Callback Requested",
}


async def send_agent_notification(client: ClientRow, urgency: str, message: str) -> None:
    """Send notification to the real estate agent via email (and SMS if configured)."""
    if client.notification_email:
        await _send_email(client.notification_email, urgency, message, client.agent_name)
    if client.notification_phone:
        await _send_sms(client.notification_phone, urgency, message)


async def _send_email(to_email: str, urgency: str, body: str, agent_name: str) -> None:
    if not settings.smtp_user or not settings.smtp_pass:
        logger.info("SMTP not configured — skipping email to %s", to_email)
        logger.info("Would have sent [%s]: %s", urgency, body)
        return

    subject = URGENCY_SUBJECTS.get(urgency, f"AgentNexLiFy: Notification ({urgency})")
    msg = MIMEMultipart()
    msg["From"] = settings.smtp_user
    msg["To"] = to_email
    msg["Subject"] = subject

    html = f"""\
<html><body>
<h2 style="color:#6cff5c">{subject}</h2>
<pre style="font-family:sans-serif;font-size:14px;line-height:1.6">{body}</pre>
<hr>
<p style="color:#888;font-size:12px">Sent by AgentNexLiFy for {agent_name}</p>
</body></html>"""
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_pass)
            server.send_message(msg)
        logger.info("Email sent to %s", to_email)
    except Exception:
        logger.exception("Failed to send email to %s", to_email)


async def _send_sms(to_phone: str, urgency: str, message: str) -> None:
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        logger.info("Twilio not configured — skipping SMS to %s", to_phone)
        return

    try:
        import httpx

        url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
        prefix = URGENCY_SUBJECTS.get(urgency, "AgentNexLiFy Alert")
        sms_body = f"{prefix}\n\n{message}"
        if len(sms_body) > 1600:
            sms_body = sms_body[:1597] + "..."

        async with httpx.AsyncClient() as http:
            resp = await http.post(
                url,
                data={
                    "From": settings.twilio_phone_number,
                    "To": to_phone,
                    "Body": sms_body,
                },
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            )
            resp.raise_for_status()
        logger.info("SMS sent to %s", to_phone)
    except Exception:
        logger.exception("Failed to send SMS to %s", to_phone)
