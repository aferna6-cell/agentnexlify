"""Public support / contact-us endpoint."""


import html
import logging

from fastapi import APIRouter, BackgroundTasks, Request

from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.models.schemas import ContactRequest, ContactResponse
from backend.services.platform_mailer import send_platform_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/support", tags=["support"])


async def _email_support_message(name: str, email: str, message: str) -> None:
    """Forward a contact-form submission to the platform owner. Never raises."""
    try:
        body = (
            f"<p><strong>From:</strong> {html.escape(name)} "
            f"&lt;{html.escape(email)}&gt;</p>"
            "<p><strong>Message:</strong><br>"
            f"{html.escape(message).replace(chr(10), '<br>')}</p>"
        )
        await send_platform_email(
            subject=f"[Support] {name}"[:120],
            body_html=body,
            reply_to=email,
        )
    except Exception:
        logger.warning("support contact email failed", exc_info=True)


@router.post("/contact", response_model=ContactResponse)
@limiter.limit("5/minute")
async def submit_contact(
    payload: ContactRequest, request: Request, background_tasks: BackgroundTasks
):
    """Accept a public contact-form submission and email the platform owner."""
    db = get_service_supabase()
    db.table("support_messages").insert(
        {"name": payload.name, "email": payload.email, "message": payload.message}
    ).execute()
    logger.info("Contact form submitted by %s", payload.email)
    background_tasks.add_task(
        _email_support_message, payload.name, payload.email, payload.message
    )
    return ContactResponse(
        success=True, message="Thanks for reaching out! We'll get back to you soon."
    )
