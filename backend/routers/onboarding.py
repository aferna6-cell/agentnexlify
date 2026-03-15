"""Autopilot Onboarding Wizard — complete setup and status endpoints.

POST /api/v1/onboarding/{tenant_id}/complete
  - Updates tenant with business info
  - Creates business_hours entry
  - Triggers website crawl
  - Auto-creates FAQ entries
  - Generates AI business page content via Claude
  - Sets autopilot_enabled and onboarding_completed_at

GET /api/v1/onboarding/{tenant_id}/status
  - Returns onboarding progress and completion percentage
"""

import logging
from datetime import datetime, timezone
from typing import Any

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_supabase
from backend.routers.auth import require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class OnboardingCompleteRequest(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=200)
    business_type: str = Field(..., min_length=1, max_length=50)
    city: str = Field(..., min_length=1, max_length=100)
    phone: str | None = Field(None, max_length=30)
    website_url: str | None = Field(None, max_length=500)
    hours: dict[str, Any] | None = None
    services: list[str] | None = None


class OnboardingCompleteResponse(BaseModel):
    tenant_id: str
    business_name: str
    configured: dict[str, bool]
    ai_content_generated: bool = False
    crawl_started: bool = False
    faqs_created: int = 0
    message: str


class OnboardingStatusResponse(BaseModel):
    has_business_info: bool = False
    has_hours: bool = False
    has_website: bool = False
    has_faqs: bool = False
    has_widget_customized: bool = False
    onboarding_completed: bool = False
    completion_percentage: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


async def _generate_ai_content(
    business_name: str,
    business_type: str,
    city: str,
    services: list[str] | None,
) -> dict[str, Any] | None:
    """Use Claude to generate business page content.

    Returns a dict with hero_headline, about_section, services_description,
    and a list of 3 FAQ dicts, or None on failure.
    """
    if not settings.anthropic_api_key:
        logger.warning("Anthropic API key not configured -- skipping AI content generation")
        return None

    services_str = ", ".join(services) if services else "general services"
    prompt = (
        f"Generate business page content for a {business_type} business called "
        f'"{business_name}" located in {city}. They offer: {services_str}.\n\n'
        "Return exactly this format (no markdown, no extra text):\n"
        "HERO: <a short, compelling headline for the hero section>\n"
        "ABOUT: <a 2-3 sentence about section>\n"
        "SERVICES: <a brief paragraph describing their services>\n"
        "FAQ1Q: <question 1>\n"
        "FAQ1A: <answer 1>\n"
        "FAQ2Q: <question 2>\n"
        "FAQ2A: <answer 2>\n"
        "FAQ3Q: <question 3>\n"
        "FAQ3A: <answer 3>"
    )

    try:
        client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key,
            timeout=30.0,
        )
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()

        result: dict[str, Any] = {"faqs": []}
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("HERO:"):
                result["hero_headline"] = line[5:].strip()
            elif line.startswith("ABOUT:"):
                result["about_section"] = line[6:].strip()
            elif line.startswith("SERVICES:"):
                result["services_description"] = line[9:].strip()
            elif line.startswith("FAQ1Q:"):
                result.setdefault("faq1", {})["q"] = line[6:].strip()
            elif line.startswith("FAQ1A:"):
                result.setdefault("faq1", {})["a"] = line[6:].strip()
            elif line.startswith("FAQ2Q:"):
                result.setdefault("faq2", {})["q"] = line[6:].strip()
            elif line.startswith("FAQ2A:"):
                result.setdefault("faq2", {})["a"] = line[6:].strip()
            elif line.startswith("FAQ3Q:"):
                result.setdefault("faq3", {})["q"] = line[6:].strip()
            elif line.startswith("FAQ3A:"):
                result.setdefault("faq3", {})["a"] = line[6:].strip()

        for key in ("faq1", "faq2", "faq3"):
            faq = result.pop(key, None)
            if faq and faq.get("q") and faq.get("a"):
                result["faqs"].append({"question": faq["q"], "answer": faq["a"]})

        return result

    except anthropic.APIError as e:
        logger.error("Claude API error during onboarding content generation: %s", e)
        return None
    except Exception:
        logger.exception("Unexpected error during AI content generation")
        return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/{tenant_id}/complete", response_model=OnboardingCompleteResponse)
@limiter.limit("10/minute")
async def complete_onboarding(
    request: Request,
    tenant_id: str,
    req: OnboardingCompleteRequest,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Enhanced onboarding endpoint that configures the tenant in one step."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    # 1. Verify tenant exists
    tenant_result = (
        db.table("tenants")
        .select("id, business_name, business_page_enabled")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not tenant_result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    configured = {
        "business_info": False,
        "hours": False,
        "website_crawl": False,
        "faqs": False,
        "ai_content": False,
    }

    # 2. Update tenants table with provided fields
    tenant_update: dict[str, Any] = {
        "business_name": req.business_name,
        "business_type": req.business_type,
        "city": req.city,
        "autopilot_enabled": True,
        "onboarding_completed_at": datetime.now(timezone.utc).isoformat(),
    }
    if req.phone:
        tenant_update["phone"] = req.phone
    if req.website_url:
        tenant_update["website_url"] = req.website_url
    if req.services:
        tenant_update["business_services"] = req.services

    try:
        db.table("tenants").update(tenant_update).eq("id", tenant_id).execute()
        configured["business_info"] = True
    except Exception:
        logger.exception("Failed to update tenant %s during onboarding", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to update business info")

    # 3. Auto-create business_hours entry from the hours JSONB
    if req.hours:
        try:
            # Check if business_hours already exists
            existing_hours = (
                db.table("business_hours")
                .select("id")
                .eq("tenant_id", tenant_id)
                .limit(1)
                .execute()
            )
            hours_data = {
                "tenant_id": tenant_id,
                "hours": req.hours,
                "timezone": req.hours.get("timezone", "America/New_York"),
            }
            # Remove timezone from the hours dict if it was there
            if "timezone" in hours_data["hours"]:
                tz = hours_data["hours"].pop("timezone")
                hours_data["timezone"] = tz

            if existing_hours.data:
                db.table("business_hours").update(hours_data).eq("id", existing_hours.data[0]["id"]).execute()
            else:
                db.table("business_hours").insert(hours_data).execute()
            configured["hours"] = True
        except Exception:
            logger.exception("Failed to create business_hours for tenant %s", tenant_id)

    # 4. If website_url provided, trigger a website crawl
    crawl_started = False
    if req.website_url:
        try:
            from backend.services.website_crawler import start_crawl
            await start_crawl(tenant_id, req.website_url)
            crawl_started = True
            configured["website_crawl"] = True
        except Exception:
            logger.exception("Failed to start website crawl for tenant %s", tenant_id)

    # 5. Auto-create FAQ entries from the services list
    faqs_created = 0
    if req.services and len(req.services) > 0:
        services_str = ", ".join(req.services)
        faq_entries = [
            {
                "tenant_id": tenant_id,
                "question": "What services do you offer?",
                "answer": f"We offer the following services: {services_str}.",
                "category": "services",
                "is_active": True,
            },
            {
                "tenant_id": tenant_id,
                "question": f"Where are you located?",
                "answer": f"We are located in {req.city}. Feel free to contact us for our exact address.",
                "category": "general",
                "is_active": True,
            },
        ]
        if req.phone:
            faq_entries.append({
                "tenant_id": tenant_id,
                "question": "How can I contact you?",
                "answer": f"You can reach us at {req.phone} or through this chat widget.",
                "category": "general",
                "is_active": True,
            })

        for entry in faq_entries:
            try:
                db.table("faq_entries").insert(entry).execute()
                faqs_created += 1
            except Exception:
                logger.exception("Failed to create FAQ entry for tenant %s", tenant_id)

        if faqs_created > 0:
            configured["faqs"] = True

    # 6. Generate AI business page content
    ai_content_generated = False
    try:
        ai_content = await _generate_ai_content(
            business_name=req.business_name,
            business_type=req.business_type,
            city=req.city,
            services=req.services,
        )
        if ai_content:
            # Add AI-generated FAQs
            for faq in ai_content.get("faqs", []):
                try:
                    db.table("faq_entries").insert({
                        "tenant_id": tenant_id,
                        "question": faq["question"],
                        "answer": faq["answer"],
                        "category": "ai_generated",
                        "is_active": True,
                    }).execute()
                    faqs_created += 1
                except Exception:
                    logger.exception("Failed to insert AI-generated FAQ for tenant %s", tenant_id)

            # If business page enabled, update description
            if tenant_result.data[0].get("business_page_enabled"):
                page_update = {}
                if ai_content.get("about_section"):
                    page_update["business_description"] = ai_content["about_section"]
                if page_update:
                    try:
                        db.table("tenants").update(page_update).eq("id", tenant_id).execute()
                    except Exception:
                        logger.exception("Failed to update business page for tenant %s", tenant_id)

            ai_content_generated = True
            configured["ai_content"] = True
    except Exception:
        logger.exception("AI content generation failed for tenant %s", tenant_id)

    return OnboardingCompleteResponse(
        tenant_id=tenant_id,
        business_name=req.business_name,
        configured=configured,
        ai_content_generated=ai_content_generated,
        crawl_started=crawl_started,
        faqs_created=faqs_created,
        message="Onboarding complete! Your business is configured and ready.",
    )


@router.get("/{tenant_id}/status", response_model=OnboardingStatusResponse)
async def onboarding_status(
    tenant_id: str,
    claims: dict = Depends(require_role("owner", "admin", "member")),
):
    """Returns onboarding progress with completion percentage."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()

    # Fetch tenant info
    tenant_result = (
        db.table("tenants")
        .select(
            "id, business_name, business_type, city, phone, website_url, "
            "autopilot_enabled, onboarding_completed_at"
        )
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not tenant_result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant = tenant_result.data[0]

    # Check business info
    has_business_info = bool(
        tenant.get("business_name")
        and tenant.get("business_type")
        and tenant.get("city")
    )

    # Check business hours
    has_hours = False
    try:
        hours_result = (
            db.table("business_hours")
            .select("id")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        has_hours = bool(hours_result.data)
    except Exception:
        logger.warning("Failed to check business_hours for tenant %s", tenant_id)

    # Check website
    has_website = False
    try:
        website_result = (
            db.table("website_content")
            .select("id, crawl_status")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        has_website = bool(
            website_result.data
            and website_result.data[0].get("crawl_status") == "completed"
        )
    except Exception:
        logger.warning("Failed to check website_content for tenant %s", tenant_id)

    # Check FAQs
    has_faqs = False
    try:
        faq_result = (
            db.table("faq_entries")
            .select("id")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        has_faqs = bool(faq_result.data)
    except Exception:
        logger.warning("Failed to check faq_entries for tenant %s", tenant_id)

    # Check widget customization
    has_widget_customized = False
    try:
        widget_result = (
            db.table("widget_configs")
            .select("bot_name, primary_color, greeting_message")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if widget_result.data:
            wc = widget_result.data[0]
            # Considered customized if they changed any default values
            has_widget_customized = bool(
                wc.get("bot_name")
                and wc["bot_name"] != "AI Assistant"
                or wc.get("primary_color")
                and wc["primary_color"] != "#00BFFF"
            )
    except Exception:
        logger.warning("Failed to check widget_configs for tenant %s", tenant_id)

    onboarding_completed = bool(tenant.get("onboarding_completed_at"))

    # Calculate completion percentage
    checks = [
        has_business_info,
        has_hours,
        has_website,
        has_faqs,
        has_widget_customized,
    ]
    completed_count = sum(1 for c in checks if c)
    completion_percentage = int((completed_count / len(checks)) * 100)

    return OnboardingStatusResponse(
        has_business_info=has_business_info,
        has_hours=has_hours,
        has_website=has_website,
        has_faqs=has_faqs,
        has_widget_customized=has_widget_customized,
        onboarding_completed=onboarding_completed,
        completion_percentage=completion_percentage,
    )
