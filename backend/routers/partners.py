"""Agency / reseller partner inquiries — public capture endpoint.

The agency channel is the fastest tenant multiplier (one agency = 10-20
seats; GoHighLevel's growth engine is exactly this buyer). This router takes
the inquiry from the marketing site's /partners page and emails the owner —
no new table, no auth surface, rate-limited + honeypotted against spam.

Program terms live in docs/partners/agency-program.md.

Critical rules: no `from __future__ import annotations`; never log secrets.
"""

import html
import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel, EmailStr, Field

from backend.limiter import limiter
from backend.services.platform_mailer import send_platform_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/partners", tags=["partners"])


class PartnerInquiryRequest(BaseModel):
    agency_name: str = Field(..., min_length=2, max_length=200)
    contact_name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    client_count: str = Field(default="", max_length=50)
    message: str = Field(default="", max_length=2000)
    # Honeypot — real users never fill this hidden field; bots do.
    website: str = Field(default="", max_length=200)


@router.post("/inquiry")
@limiter.limit("5/hour")
async def partner_inquiry(request: Request, body: PartnerInquiryRequest):
    """Capture an agency/reseller inquiry and email the owner. Always 200."""
    if body.website.strip():
        # Honeypot tripped — accept silently so the bot learns nothing.
        logger.info("partners: honeypot tripped, dropping inquiry")
        return {"status": "received"}

    subject = f"Partner inquiry: {body.agency_name}"
    body_html = (
        "<div style='font-family:sans-serif;max-width:600px;margin:0 auto;'>"
        "<h2 style='color:#1e293b;'>Agency / reseller inquiry</h2>"
        "<table style='border-collapse:collapse;'>"
        f"<tr><td style='padding:6px 16px 6px 0;color:#374151;'>Agency</td>"
        f"<td style='padding:6px 0;font-weight:600;'>{html.escape(body.agency_name)}</td></tr>"
        f"<tr><td style='padding:6px 16px 6px 0;color:#374151;'>Contact</td>"
        f"<td style='padding:6px 0;font-weight:600;'>{html.escape(body.contact_name)}</td></tr>"
        f"<tr><td style='padding:6px 16px 6px 0;color:#374151;'>Email</td>"
        f"<td style='padding:6px 0;font-weight:600;'>{html.escape(body.email)}</td></tr>"
        f"<tr><td style='padding:6px 16px 6px 0;color:#374151;'>Clients managed</td>"
        f"<td style='padding:6px 0;font-weight:600;'>{html.escape(body.client_count or '-')}</td></tr>"
        "</table>"
        f"<p style='color:#374151;white-space:pre-wrap;'>{html.escape(body.message or '')}</p>"
        "<p style='color:#6b7280;font-size:13px;'>Program terms: docs/partners/agency-program.md. "
        "Reply directly to the contact email above.</p>"
        "</div>"
    )
    try:
        await send_platform_email(subject=subject, body_html=body_html)
    except Exception:
        # The prospect should never see a failure; the log line is the alert.
        logger.exception("partners: failed to email owner for inquiry")
    return {"status": "received"}
