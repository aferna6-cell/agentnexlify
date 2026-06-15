"""Public support / contact-us endpoint.

Persists the submission to ``support_messages`` (migration 003) AND emails the
platform admin (``settings.support_form_email``) so it lands in the inbox, not
only the database. Both the DB write and the email are best-effort: a failure
in either is logged and never blocks the form — a contact form should not 500
on the visitor. Ops can recover any lost email from the persisted row.
"""

import logging

from fastapi import APIRouter, Request

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.models.schemas import ContactRequest, ContactResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/support", tags=["support"])


def _html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _notify_admin(payload: ContactRequest) -> None:
    """Email the platform admin the contact submission. Best-effort."""
    if not settings.support_form_email:
        logger.warning("support contact: SUPPORT_FORM_EMAIL unset — not emailing")
        return
    if not settings.resend_api_key:
        logger.warning("support contact: RESEND_API_KEY unset — not emailing")
        return
    try:
        import resend

        resend.api_key = settings.resend_api_key
        subject = payload.subject or "(no subject)"
        body_html = (
            "<h2>New support form submission</h2>"
            f"<p><strong>From:</strong> {_html_escape(payload.name)} "
            f"&lt;{_html_escape(payload.email)}&gt;</p>"
            f"<p><strong>Subject:</strong> {_html_escape(subject)}</p>"
            "<p><strong>Message:</strong></p>"
            f"<p>{_html_escape(payload.message)}</p>"
        )
        resend.Emails.send(
            {
                "from": "AgentNexLiFy Support <noreply@agentnexlify.com>",
                "to": [settings.support_form_email],
                "reply_to": payload.email,
                "subject": f"[Support] {subject}",
                "html": body_html,
            }
        )
        logger.info("support contact: admin emailed for %s", payload.email)
    except Exception:
        logger.exception("support contact: admin email failed for %s", payload.email)


@router.post("/contact", response_model=ContactResponse)
@limiter.limit("5/minute")
async def submit_contact(payload: ContactRequest, request: Request):
    """Accept a public contact-form submission: persist + email the admin."""
    try:
        db = get_service_supabase()
        db.table("support_messages").insert(
            {"name": payload.name, "email": payload.email, "message": payload.message}
        ).execute()
    except Exception:
        logger.exception("support contact: DB insert failed for %s", payload.email)

    _notify_admin(payload)
    logger.info("Contact form submitted by %s", payload.email)
    return ContactResponse(
        success=True, message="Thanks for reaching out! We'll get back to you soon."
    )
