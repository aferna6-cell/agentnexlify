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
import os
from typing import Any

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.dependencies import require_role
from backend.services.llm_runtime import call_claude_messages
from backend.services.onboarding_ai import (
    AutoKbFaqEntry,
)
from backend.services.onboarding_kb import (
    run_auto_populate_kb,
    run_generate_kb,
)
from backend.services.onboarding_workflow import (
    compute_onboarding_status,
    run_onboarding_complete,
)

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
    industry_pack_applied: bool = False
    industry_pack_key: str | None = None
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


class AutoKbResponse(BaseModel):
    knowledge_base: str
    custom_instructions: str
    faqs: list[AutoKbFaqEntry]
    pages_crawled: int
    chars_extracted: int
    services: list[str] = []
    hours: dict[str, str] = {}


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
    if not settings.anthropic_api_key and os.environ.get("TESTING") != "1":
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
        response = await call_claude_messages(
            operation="onboarding.generate_ai_content",
            model="claude-sonnet-4-6",
            max_tokens=800,
            timeout=30.0,
            messages=[{"role": "user", "content": prompt}],
            metadata={"business_name": business_name, "business_type": business_type, "city": city},
        )
        text = response.text.strip()

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
    db = get_service_supabase()
    result = await run_onboarding_complete(
        db, tenant_id, req, ai_content_fn=_generate_ai_content
    )
    return OnboardingCompleteResponse(
        tenant_id=tenant_id,
        business_name=req.business_name,
        configured=result.configured,
        ai_content_generated=result.ai_content_generated,
        crawl_started=result.crawl_started,
        faqs_created=result.faqs_created,
        industry_pack_applied=result.industry_pack_applied,
        industry_pack_key=result.industry_pack_key,
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
    db = get_service_supabase()
    result = await run_generate_kb(db, tenant_id, req)
    return GenerateKbResponse(
        knowledge_base=result.knowledge_base,
        generated=result.generated,
    )


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
    db = get_service_supabase()
    result = await run_auto_populate_kb(db, tenant_id, req)
    return AutoKbResponse(
        knowledge_base=result.knowledge_base,
        custom_instructions=result.custom_instructions,
        faqs=result.faqs,
        pages_crawled=result.pages_crawled,
        chars_extracted=result.chars_extracted,
        services=result.services,
        hours=result.hours,
    )


@router.get("/{tenant_id}/status", response_model=OnboardingStatusResponse)
async def onboarding_status(
    tenant_id: str,
    claims: dict = Depends(require_role("owner", "admin", "member")),
):
    """Returns onboarding progress with completion percentage."""
    _verify_tenant(claims, tenant_id)
    db = get_service_supabase()
    result = compute_onboarding_status(db, tenant_id)
    return OnboardingStatusResponse(
        has_business_info=result.has_business_info,
        has_hours=result.has_hours,
        has_website=result.has_website,
        has_faqs=result.has_faqs,
        has_widget_customized=result.has_widget_customized,
        onboarding_completed=result.onboarding_completed,
        completion_percentage=result.completion_percentage,
    )


# ---------------------------------------------------------------------------
# Industry Pack endpoints — seed turnkey workflow bundles by business_type
# ---------------------------------------------------------------------------


class ApplyIndustryPackRequest(BaseModel):
    """Payload for applying an industry pack.

    If `business_type` is omitted, the tenant's stored business_type is used.
    `dry_run=True` returns the expected seed counts without writing anything.
    """

    business_type: str | None = Field(default=None, max_length=50)
    dry_run: bool = False


class IndustryPackSummary(BaseModel):
    key: str
    label: str
    version: int
    counts: dict[str, int]


class ApplyIndustryPackResponse(BaseModel):
    pack: IndustryPackSummary
    dry_run: bool
    forms_inserted: int
    forms_skipped: int
    sequences_inserted: int
    sequences_skipped: int
    smart_lists_inserted: int
    smart_lists_skipped: int
    automation_rules_inserted: int
    automation_rules_skipped: int
    kb_articles_inserted: int
    kb_articles_skipped: int
    total_inserted: int
    errors: list[str]


class ListIndustryPacksResponse(BaseModel):
    packs: list[IndustryPackSummary]


@router.get("/industry-packs", response_model=ListIndustryPacksResponse)
async def list_industry_packs(
    claims: dict = Depends(require_role("owner", "admin", "member")),
):
    """List all available industry packs with their component counts.

    Not tenant-scoped — packs are global read-only content. Used by the
    onboarding wizard to show the user which pack will be applied.
    """
    from backend.services.industry_packs import list_available_packs

    raw = list_available_packs()
    return ListIndustryPacksResponse(
        packs=[IndustryPackSummary(**p) for p in raw],
    )


@router.post(
    "/{tenant_id}/apply-industry-pack",
    response_model=ApplyIndustryPackResponse,
)
async def apply_industry_pack(
    tenant_id: str,
    req: ApplyIndustryPackRequest,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Seed a turnkey industry pack (forms, sequences, smart lists, rules,
    KB seed articles) into the tenant. Idempotent — re-running skips any
    rows already seeded with the same source tag.

    If `business_type` is omitted, uses the tenant's stored business_type.
    Falls back to `default` pack if the business_type isn't recognized.
    """
    _verify_tenant(claims, tenant_id)
    from backend.services.industry_packs import load_pack
    from backend.services.industry_packs.seed import apply_pack_to_tenant

    db = get_service_supabase()

    # Resolve business_type (from body or tenant record)
    business_type = (req.business_type or "").strip() or None
    if business_type is None:
        tenant_row = (
            db.table("tenants")
            .select("business_type")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        if not tenant_row.data:
            raise HTTPException(status_code=404, detail="Tenant not found")
        business_type = tenant_row.data[0].get("business_type") or "default"

    pack = load_pack(business_type)
    logger.info(
        "apply_industry_pack: tenant=%s business_type=%s → pack=%s dry_run=%s",
        tenant_id, business_type, pack.key, req.dry_run,
    )

    try:
        result = apply_pack_to_tenant(db, tenant_id, pack, dry_run=req.dry_run)
    except Exception as exc:
        logger.exception("apply_industry_pack failed for tenant=%s pack=%s", tenant_id, pack.key)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to apply industry pack: {type(exc).__name__}: {exc}",
        )

    return ApplyIndustryPackResponse(
        pack=IndustryPackSummary(
            key=pack.key,
            label=pack.label,
            version=pack.version,
            counts=pack.summary(),
        ),
        dry_run=req.dry_run,
        forms_inserted=result.forms_inserted,
        forms_skipped=result.forms_skipped,
        sequences_inserted=result.sequences_inserted,
        sequences_skipped=result.sequences_skipped,
        smart_lists_inserted=result.smart_lists_inserted,
        smart_lists_skipped=result.smart_lists_skipped,
        automation_rules_inserted=result.automation_rules_inserted,
        automation_rules_skipped=result.automation_rules_skipped,
        kb_articles_inserted=result.kb_articles_inserted,
        kb_articles_skipped=result.kb_articles_skipped,
        total_inserted=result.total_inserted(),
        errors=result.errors,
    )
