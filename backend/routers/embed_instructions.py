"""Email widget embed instructions to whoever manages the tenant's website.

Escape hatch for the onboarding wizard's embed step: most small-business
owners can't edit their own site, so instead of stalling there they email
the snippet + install steps to their "web person" (agency, nephew, Wix
admin). The Agent OS itself needs no embed — this is strictly optional
widget setup.

Critical rules:
  - No from __future__ import annotations (FastAPI router file)
  - html.escape every user-supplied value placed into the email
  - Never log the widget api key
"""

import html
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from backend.dependencies import require_role, verify_tenant
from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.services.email_sender import send_email, mask_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])

WIDGET_CDN_URL = "https://agentnexlify.com/widget/agentnexlify-widget.js"

PLATFORM_GUIDES = [
    (
        "WordPress",
        "Appearance &rarr; Theme File Editor &rarr; footer.php, paste before "
        "&lt;/body&gt;. Or install the &quot;Insert Headers and Footers&quot; "
        "plugin and paste it there.",
    ),
    (
        "Wix",
        "Settings &rarr; Custom Code &rarr; Add Custom Code &rarr; paste the "
        "snippet, set it to load on All Pages in the Body - end.",
    ),
    (
        "Squarespace",
        "Settings &rarr; Advanced &rarr; Code Injection &rarr; paste into the "
        "Footer box.",
    ),
    (
        "GoDaddy Website Builder",
        "Edit Site &rarr; add an HTML section &rarr; paste the snippet.",
    ),
]


class EmailEmbedRequest(BaseModel):
    recipient_email: str = Field(..., max_length=320)
    note: str | None = Field(None, max_length=500)

    @field_validator("recipient_email")
    @classmethod
    def validate_recipient(cls, v: str) -> str:
        import re

        v = v.strip().lower()
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", v):
            raise ValueError("Invalid email address")
        return v


@router.post("/{tenant_id}/email-embed")
@limiter.limit("5/hour")
async def email_embed_instructions(
    request: Request,
    tenant_id: str,
    req: EmailEmbedRequest,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Send the widget embed snippet + platform install steps to a recipient."""
    verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    try:
        result = (
            db.table("widget_configs")
            .select("api_key, bot_name")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("email-embed: widget config lookup failed for %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load widget config")

    if not result.data or not result.data[0].get("api_key"):
        raise HTTPException(
            status_code=404,
            detail="Widget isn't set up yet — finish onboarding first.",
        )

    api_key = result.data[0]["api_key"]
    business_name = html.escape(claims.get("business_name") or "this business")
    sender_email = html.escape(claims.get("email") or "")
    note_html = (
        f"<p><em>Note from {sender_email}:</em> {html.escape(req.note)}</p>"
        if req.note
        else ""
    )

    snippet = html.escape(
        f'<script src="{WIDGET_CDN_URL}"\n'
        f'        data-api-key="{api_key}"\n'
        f"        async>\n"
        f"</script>"
    )
    guides = "".join(
        f"<li><strong>{name}:</strong> {steps}</li>" for name, steps in PLATFORM_GUIDES
    )

    body_html = (
        f"<h2>Add the {business_name} chat widget to the website</h2>"
        f"<p>{sender_email} uses AgentNexLiFy to run {business_name} with AI staff. "
        "They asked us to send you the one-line snippet that adds their AI front "
        "desk (chat widget) to the website.</p>"
        f"{note_html}"
        "<p><strong>Paste this just before the closing &lt;/body&gt; tag:</strong></p>"
        f"<pre style='background:#f4f4f5;padding:14px;border-radius:8px;"
        f"overflow-x:auto'><code>{snippet}</code></pre>"
        "<p><strong>Platform shortcuts:</strong></p>"
        f"<ul>{guides}</ul>"
        "<p>Save, refresh the page, and the chat bubble appears. "
        "No other changes needed.</p>"
        "<p>&mdash; The AgentNexLiFy Team</p>"
    )

    try:
        await send_email(
            to=req.recipient_email,
            subject=f"Chat widget install for {claims.get('business_name') or 'your client'}",
            body_html=body_html,
            tenant_id=tenant_id,
        )
    except Exception:
        logger.exception(
            "email-embed: send failed for tenant %s to %s",
            tenant_id,
            mask_email(req.recipient_email),
        )
        raise HTTPException(status_code=502, detail="Failed to send the email")

    logger.info(
        "email-embed: sent for tenant %s to %s",
        tenant_id,
        mask_email(req.recipient_email),
    )
    return {"success": True, "message": "Instructions sent"}
