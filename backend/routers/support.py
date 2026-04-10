"""Public support / contact-us endpoint."""


import logging

from fastapi import APIRouter, Request

from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.models.schemas import ContactRequest, ContactResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/support", tags=["support"])


@router.post("/contact", response_model=ContactResponse)
@limiter.limit("5/minute")
async def submit_contact(payload: ContactRequest, request: Request):
    """Accept a public contact-form submission."""
    db = get_service_supabase()
    db.table("support_messages").insert(
        {"name": payload.name, "email": payload.email, "message": payload.message}
    ).execute()
    logger.info("Contact form submitted by %s", payload.email)
    return ContactResponse(
        success=True, message="Thanks for reaching out! We'll get back to you soon."
    )
