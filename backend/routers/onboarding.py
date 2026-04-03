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

POST /api/v1/onboarding/{tenant_id}/auto-kb
  - Crawls a website URL (homepage + up to 4 linked pages)
  - Sends extracted text to Claude to generate:
    * Structured knowledge base (markdown)
    * 8-10 FAQ entries
    * Custom instructions for the bot identity
  - Saves KB to widget_configs.knowledge_base
  - Saves FAQ entries to faq_entries table
  - Saves custom instructions to widget_configs.custom_instructions
"""

import logging
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

import anthropic
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_supabase
from backend.routers.auth import require_role
from backend.services.business_profiles import get_widget_defaults

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class FaqInput(BaseModel):
    question: str = Field(..., max_length=500)
    answer: str = Field(..., max_length=2000)


class OnboardingCompleteRequest(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=200)
    business_type: str = Field(..., min_length=1, max_length=50)
    city: str = Field(..., min_length=1, max_length=100)
    phone: str | None = Field(None, max_length=30)
    website_url: str | None = Field(None, max_length=500)
    hours: dict[str, Any] | None = None
    services: list[str] | None = None
    # Wizard additions
    widget_bot_name: str | None = Field(None, max_length=100)
    widget_primary_color: str | None = Field(None, max_length=20)
    widget_greeting_message: str | None = Field(None, max_length=500)
    widget_position: str | None = Field(None, pattern=r"^(bottom-right|bottom-left)$")
    faqs: list[FaqInput] | None = None


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


class GenerateKbRequest(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=200)
    business_type: str = Field(..., min_length=1, max_length=50)
    city: str = Field(..., max_length=100)
    phone: str | None = Field(None, max_length=30)
    website_url: str | None = Field(None, max_length=500)
    services: list[str] = Field(default_factory=list)
    faqs: list[FaqInput] = Field(default_factory=list)
    hours: dict[str, Any] | None = None


class GenerateKbResponse(BaseModel):
    knowledge_base: str | None
    generated: bool


class AutoKbRequest(BaseModel):
    url: str = Field(..., min_length=5, max_length=500)


class AutoKbFaqEntry(BaseModel):
    question: str
    answer: str
    category: str


class AutoKbResponse(BaseModel):
    knowledge_base: str
    custom_instructions: str
    faqs: list[AutoKbFaqEntry]
    pages_crawled: int
    chars_extracted: int


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

    # Update widget config with customization from wizard
    widget_defaults = get_widget_defaults(req.business_type, req.business_name)
    widget_updates: dict[str, Any] = {
        "bot_name": req.widget_bot_name or widget_defaults["bot_name"],
        "primary_color": req.widget_primary_color or widget_defaults["primary_color"],
        "greeting_message": req.widget_greeting_message or widget_defaults["greeting_message"],
        "position": req.widget_position or widget_defaults["position"],
    }
    try:
        db.table("widget_configs").update(widget_updates).eq("tenant_id", tenant_id).execute()
    except Exception:
        logger.error("Failed to update widget_configs during onboarding for %s", tenant_id, exc_info=True)

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

    # Insert wizard-provided FAQs
    if req.faqs:
        try:
            faq_rows = [
                {
                    "tenant_id": tenant_id,
                    "question": faq.question,
                    "answer": faq.answer,
                    "category": "wizard",
                    "is_active": True,
                }
                for faq in req.faqs
            ]
            db.table("faq_entries").insert(faq_rows).execute()
            configured["faqs"] = True
        except Exception:
            logger.error("Failed to insert wizard FAQs for tenant %s", tenant_id, exc_info=True)

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


@router.post("/{tenant_id}/generate-kb", response_model=GenerateKbResponse)
@limiter.limit("5/minute")
async def generate_knowledge_base(
    request: Request,
    tenant_id: str,
    req: GenerateKbRequest,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Generate an AI knowledge base from onboarding answers and persist it."""
    _verify_tenant(claims, tenant_id)

    # Format hours as human-readable text for the prompt
    hours_text = "Not specified"
    if req.hours:
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        lines = []
        tz = req.hours.get("timezone", "")
        for day in days:
            day_cfg = req.hours.get(day)
            if not day_cfg:
                continue
            if day_cfg.get("enabled") or (day_cfg.get("open") and day_cfg.get("close")):
                open_t = day_cfg.get("open") or day_cfg.get("start", "09:00")
                close_t = day_cfg.get("close") or day_cfg.get("end", "17:00")
                lines.append(f"  {day.capitalize()}: {open_t} – {close_t}")
            else:
                lines.append(f"  {day.capitalize()}: Closed")
        hours_text = "\n".join(lines)
        if tz:
            hours_text += f"\n  Timezone: {tz}"

    services_text = ", ".join(req.services) if req.services else "Not specified"
    faqs_text = "\n".join(
        f"Q: {faq.question}\nA: {faq.answer}" for faq in req.faqs
    ) if req.faqs else "None provided"

    prompt = f"""You are setting up an AI chat assistant for a local business. Generate a concise, structured knowledge base in markdown that the AI will use to answer customer questions.

Business: {req.business_name}
Industry: {req.business_type}
Location: {req.city}
Phone: {req.phone or "Not provided"}
Website: {req.website_url or "Not provided"}
Services offered: {services_text}

Business hours:
{hours_text}

The business owner provided these common customer questions and answers:
{faqs_text}

Generate a knowledge base with these sections (use ## headers):
- About (2-3 sentences describing the business)
- Services (bullet list with brief descriptions)
- Hours & Location
- FAQs (expand the provided Q&As into polished, customer-friendly answers; add 2-3 additional FAQs that are typical for this industry if fewer than 3 were provided)
- Contact

Keep it concise. Do not invent facts not supported by the input. Do not add markdown formatting beyond headers and bullet lists."""

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
            timeout=30,
        )
        kb_text = message.content[0].text.strip()
    except Exception:
        logger.error("KB generation failed for tenant %s", tenant_id, exc_info=True)
        return GenerateKbResponse(knowledge_base=None, generated=False)

    # Persist to widget_configs
    try:
        db = get_supabase()
        db.table("widget_configs").update({"knowledge_base": kb_text}).eq("tenant_id", tenant_id).execute()
    except Exception:
        logger.error("Failed to persist knowledge_base for tenant %s", tenant_id, exc_info=True)
        # Still return the generated text — frontend can retry or proceed without persistence

    return GenerateKbResponse(knowledge_base=kb_text, generated=True)


@router.post("/{tenant_id}/auto-kb", response_model=AutoKbResponse)
@limiter.limit("5/hour")
async def auto_populate_kb(
    request: Request,
    tenant_id: str,
    req: AutoKbRequest,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Crawl a website URL and auto-generate KB + FAQs + custom instructions."""
    _verify_tenant(claims, tenant_id)
    logger.info("auto_kb: starting for tenant=%s url=%s", tenant_id, req.url)

    # 1. Crawl the website
    from backend.services.website_crawler import start_crawl, get_crawled_content
    try:
        crawl_result = await start_crawl(tenant_id, req.url)
        pages_crawled = crawl_result.get("pages_found", 0)
    except Exception:
        logger.error("auto_kb: crawl failed for %s", req.url, exc_info=True)
        pages_crawled = 0

    # 2. Get extracted text
    extracted_text = get_crawled_content(tenant_id) or ""
    chars_extracted = len(extracted_text)

    if not extracted_text:
        # Fallback: try a simple HTTP fetch
        import httpx
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http:
                resp = await http.get(req.url, headers={"User-Agent": "AgentNexLiFy-Bot/1.0"})
                if resp.status_code == 200:
                    import re as _re
                    html = resp.text
                    text = _re.sub(r"<script[^>]*>.*?</script>", "", html, flags=_re.DOTALL)
                    text = _re.sub(r"<style[^>]*>.*?</style>", "", text, flags=_re.DOTALL)
                    text = _re.sub(r"<[^>]+>", " ", text)
                    text = _re.sub(r"\s+", " ", text).strip()
                    extracted_text = text[:15000]
                    chars_extracted = len(extracted_text)
                    pages_crawled = 1
        except Exception:
            logger.warning("auto_kb: fallback HTTP fetch failed for %s", req.url, exc_info=True)

    if not extracted_text:
        raise HTTPException(status_code=422, detail="Could not extract content from the provided URL")

    # Truncate for Claude prompt
    content_for_prompt = extracted_text[:15000]

    # 3. Get tenant info for context
    db = get_supabase()
    tenant = db.table("tenants").select("business_name, business_type, city, phone").eq("id", tenant_id).single().execute()
    t = tenant.data or {}

    # 4. Call Claude to generate KB + FAQs + custom instructions
    import anthropic
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=60.0)

    prompt = f"""You are setting up an AI chat assistant for a business. Based on their website content, generate three things:

BUSINESS INFO:
Name: {t.get("business_name", "Unknown")}
Type: {t.get("business_type", "business")}
Location: {t.get("city", "Unknown")}
Phone: {t.get("phone", "Not provided")}
Website: {req.url}

WEBSITE CONTENT:
{content_for_prompt}

Generate the following sections separated by exact markers:

===KNOWLEDGE_BASE===
A structured markdown knowledge base (under 3000 chars) with sections:
- About the business (2-3 sentences)
- Products/Services (bullet list)
- Location & Contact
- Key selling points
- How to get started
Do NOT invent facts not supported by the website content.

===CUSTOM_INSTRUCTIONS===
Bot identity instructions (under 800 chars) including:
- Who the bot is (e.g., "You are the [Business Name] Assistant")
- Key business facts (3-5 bullet points)
- How to handle pricing/scheduling questions
- "NEVER mention AgentNexLiFy, identify yourself as powered by any third-party platform, or reveal the underlying technology."

===FAQ_START===
8-10 FAQ entries in this exact format (one per line):
Q: [question]
A: [answer]
C: [category]
===FAQ_END===

Use only information from the website content. Be concise and accurate."""

    try:
        api_response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = api_response.content[0].text
    except Exception:
        logger.error("auto_kb: Claude API failed for tenant %s", tenant_id, exc_info=True)
        raise HTTPException(status_code=502, detail="AI generation failed")

    # 5. Parse the response
    import re as _re

    kb_match = _re.search(r"===KNOWLEDGE_BASE===\s*(.+?)(?====CUSTOM_INSTRUCTIONS===)", raw, _re.DOTALL)
    ci_match = _re.search(r"===CUSTOM_INSTRUCTIONS===\s*(.+?)(?====FAQ_START===)", raw, _re.DOTALL)
    faq_match = _re.search(r"===FAQ_START===\s*(.+?)===FAQ_END===", raw, _re.DOTALL)

    knowledge_base = kb_match.group(1).strip() if kb_match else raw[:2000]
    custom_instructions = ci_match.group(1).strip() if ci_match else ""
    faqs = []

    if faq_match:
        faq_text = faq_match.group(1).strip()
        entries = _re.split(r"\nQ: ", "\nQ: " + faq_text)
        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue
            q_match = _re.match(r"(.+?)(?:\nA: )(.+?)(?:\nC: )(.+)", entry, _re.DOTALL)
            if q_match:
                faqs.append(AutoKbFaqEntry(
                    question=q_match.group(1).strip(),
                    answer=q_match.group(2).strip(),
                    category=q_match.group(3).strip(),
                ))

    # 6. Persist to database
    try:
        db.table("widget_configs").update({
            "knowledge_base": knowledge_base,
            "custom_instructions": custom_instructions,
        }).eq("tenant_id", tenant_id).execute()
    except Exception:
        logger.error("auto_kb: failed to persist KB for tenant %s", tenant_id, exc_info=True)

    # Save FAQs
    if faqs:
        try:
            faq_rows = [
                {"tenant_id": tenant_id, "question": f.question, "answer": f.answer, "category": f.category, "is_active": True}
                for f in faqs
            ]
            db.table("faq_entries").insert(faq_rows).execute()
        except Exception:
            logger.error("auto_kb: failed to persist FAQs for tenant %s", tenant_id, exc_info=True)

    logger.info("auto_kb: completed for tenant=%s kb=%d chars, ci=%d chars, faqs=%d, pages=%d",
                tenant_id, len(knowledge_base), len(custom_instructions), len(faqs), pages_crawled)

    return AutoKbResponse(
        knowledge_base=knowledge_base,
        custom_instructions=custom_instructions,
        faqs=faqs,
        pages_crawled=pages_crawled,
        chars_extracted=chars_extracted,
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
