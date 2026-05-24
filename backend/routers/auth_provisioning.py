"""Tenant provisioning logic extracted from auth.py.

Two functions:
- `_provision_tenant_account`: creates tenants row, widget_configs row,
  api_key, seeds industry FAQs. Used by signup paths (email + Google).
- `_run_signup_side_effects`: sends welcome email, optionally starts
  website crawl. Best-effort, swallows errors with warning logs.

Uses dynamic lookup `from backend.routers import auth as _auth` for
`_auth.get_service_supabase()` so that the existing test patch surface
`backend.routers.auth.get_service_supabase` continues to intercept.
"""

import logging
import secrets

from fastapi import HTTPException

from backend.services.business_profiles import get_widget_defaults
from backend.services.industry_faqs import _seed_industry_faqs

logger = logging.getLogger(__name__)


def _provision_tenant_account(
    *,
    business_name: str,
    owner_name: str,
    email: str,
    password_hash: str,
    industry: str,
    city: str,
    phone: str | None = None,
    website_url: str | None = None,
) -> tuple[str, str]:
    from backend.routers import auth as _auth

    db = _auth.get_service_supabase()
    normalized_email = email.lower().strip()

    existing = (
        db.table("tenants")
        .select("id")
        .eq("owner_email", normalized_email)
        .limit(1)
        .execute()
    )
    if existing.data:
        raise HTTPException(status_code=409, detail="Email already registered")

    tenant_data = {
        "business_name": business_name,
        "business_type": industry,
        "owner_email": normalized_email,
        "owner_name": owner_name,
        "password_hash": password_hash,
        "city": city,
        "plan": "free",
    }
    result = db.table("tenants").insert(tenant_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create account")

    tenant_id = str(result.data[0]["id"])

    extra_fields = {}
    if website_url:
        extra_fields["website_url"] = website_url
    if phone:
        extra_fields["notification_phone"] = phone
        extra_fields["sms_notifications_enabled"] = True
    if extra_fields:
        try:
            db.table("tenants").update(extra_fields).eq("id", tenant_id).execute()
        except Exception:
            logger.warning(
                "Failed to save signup fields for new tenant %s",
                tenant_id,
                exc_info=True,
            )

    api_key = f"anx_{secrets.token_urlsafe(32)}"
    widget_defaults = get_widget_defaults(industry, business_name)
    try:
        wc_result = (
            db.table("widget_configs")
            .insert(
                {
                    "tenant_id": tenant_id,
                    "api_key": api_key,
                    "bot_name": widget_defaults["bot_name"],
                    "primary_color": widget_defaults["primary_color"],
                    "greeting_message": widget_defaults["greeting_message"],
                    "position": widget_defaults["position"],
                    "show_watermark": True,
                }
            )
            .execute()
        )
        if not wc_result.data:
            raise RuntimeError("widget_configs insert returned no data")
    except Exception:
        logger.error(
            "Failed to create widget_configs for tenant %s — rolling back",
            tenant_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to initialize widget configuration"
        )

    _seed_industry_faqs(tenant_id, industry, business_name, city)
    return tenant_id, api_key


async def _run_signup_side_effects(
    *,
    email: str,
    owner_name: str,
    tenant_id: str,
    business_name: str,
    industry: str,
    city: str,
    website_url: str | None = None,
) -> None:
    from backend.routers import auth as _auth

    try:
        await _auth.send_email(
            to=email,
            subject="Welcome to AgentNexLiFy!",
            body_html=(
                f"<h2>Welcome to AgentNexLiFy, {owner_name or 'there'}!</h2>"
                "<p>Your AI-powered business automation platform is ready to go.</p>"
                "<p><strong>Here's what to do next:</strong></p>"
                "<ol>"
                "<li>Configure your AI assistant with your business info and FAQs</li>"
                "<li>Customize your chat widget's appearance</li>"
                "<li>Embed the widget on your website with one line of code</li>"
                "</ol>"
                "<p>Your AI assistant will start capturing leads and booking appointments automatically.</p>"
                f"<p><a href='{_auth.settings.frontend_url}/dashboard' style='background:#3b82f6;color:#fff;'"
                "padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:600;'>"
                "Go to Dashboard &rarr;</a></p>"
                "<p>&mdash; The AgentNexLiFy Team</p>"
            ),
            tenant_id=tenant_id,
        )
    except Exception:
        logger.warning(
            "Welcome email failed for new tenant %s", tenant_id, exc_info=True
        )

    if website_url:
        try:
            from backend.services.website_crawler import start_crawl

            await start_crawl(tenant_id, website_url)
        except Exception:
            logger.warning(
                "Signup crawl failed for new tenant %s url=%s",
                tenant_id,
                website_url,
                exc_info=True,
            )
