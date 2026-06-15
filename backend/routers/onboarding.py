"""Autopilot Onboarding Wizard - complete setup and status endpoints.

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
from datetime import datetime, timezone
from typing import Any

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.dependencies import require_role
from backend.services.business_profiles import get_widget_defaults
from backend.services.llm_runtime import call_claude_messages
from backend.services.pay_gate import require_active_plan

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
    # city optional since express setup (2026-06-11) - wizard still collects it
    city: str = Field("", max_length=100)
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
    services: list[str] = []
    hours: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_auto_kb_response(
    raw: str,
) -> tuple[str, str, list[AutoKbFaqEntry], list[str], dict[str, str]]:
    """Parse Claude's auto-KB response into kb, instructions, FAQs, services, hours."""
    import re as _re

    kb_match = _re.search(r"===KNOWLEDGE_BASE===\s*(.+?)(?====CUSTOM_INSTRUCTIONS===)", raw, _re.DOTALL)
    ci_match = _re.search(r"===CUSTOM_INSTRUCTIONS===\s*(.+?)(?====FAQ_START===)", raw, _re.DOTALL)
    faq_match = _re.search(r"===FAQ_START===\s*(.+?)===FAQ_END===", raw, _re.DOTALL)
    services_match = _re.search(r"===SERVICES===\s*(.+?)(?====|$)", raw, _re.DOTALL)
    hours_match = _re.search(r"===HOURS===\s*(.+?)(?====|$)", raw, _re.DOTALL)

    knowledge_base = kb_match.group(1).strip() if kb_match else raw[:2000]
    custom_instructions = ci_match.group(1).strip() if ci_match else ""
    faqs: list[AutoKbFaqEntry] = []

    if faq_match:
        faq_text = faq_match.group(1).strip()
        entries = _re.split(r"\nQ: ", "\nQ: " + faq_text)
        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue
            q_match = _re.match(r"(.+?)(?:\nA: )(.+?)(?:\nC: )(.+)", entry, _re.DOTALL)
            if q_match:
                question = q_match.group(1).strip()
                if question.startswith("Q: "):
                    question = question[3:].strip()
                faqs.append(AutoKbFaqEntry(
                    question=question,
                    answer=q_match.group(2).strip(),
                    category=q_match.group(3).strip(),
                ))

    # services: prefer ===SERVICES=== marker, fall back to "## Services" bullets in KB.
    services: list[str] = []
    if services_match:
        for line in services_match.group(1).strip().splitlines():
            s = line.lstrip("-* ").strip()
            if s:
                services.append(s)
    if not services:
        kb_services = _re.search(r"##\s*Services\s*\n(.+?)(?:\n##|\Z)", knowledge_base, _re.DOTALL | _re.IGNORECASE)
        if kb_services:
            for line in kb_services.group(1).splitlines():
                s = line.lstrip("-* ").strip()
                if s and not s.startswith("#"):
                    services.append(s)

    # hours: prefer ===HOURS=== marker, fall back to "Mon-Fri X-Y, Sat A-B" expansion.
    hours: dict[str, str] = {}
    if hours_match:
        for line in hours_match.group(1).strip().splitlines():
            if ":" in line:
                day, val = line.split(":", 1)
                day = day.strip()[:3].title()
                val = val.strip()
                if day:
                    hours[day] = val
    if not hours:
        hours = _expand_hours_from_text(knowledge_base)

    return knowledge_base, custom_instructions, faqs, services, hours


def _expand_hours_from_text(text: str) -> dict[str, str]:
    """Best-effort: parse 'Mon-Fri 8am-6pm, Sat 9am-2pm' style strings into 7-day dict."""
    import re as _re

    days_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    out: dict[str, str] = {}
    for m in _re.finditer(
        r"\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)(?:-(Mon|Tue|Wed|Thu|Fri|Sat|Sun))?\s*([0-9]{1,2}(?::[0-9]{2})?\s*(?:am|pm)?\s*[-–]\s*[0-9]{1,2}(?::[0-9]{2})?\s*(?:am|pm)?|closed)",
        text,
        _re.IGNORECASE,
    ):
        start, end, val = m.group(1).title(), (m.group(2) or m.group(1)).title(), m.group(3).strip()
        try:
            i, j = days_order.index(start), days_order.index(end)
        except ValueError:
            continue
        for d in days_order[i : j + 1]:
            out.setdefault(d, val)
    return out


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
    _gate: dict = Depends(require_active_plan),
):
    """Enhanced onboarding endpoint that configures the tenant in one step."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()

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
        "industry_pack": False,
    }

    # 2. Update tenants table with provided fields
    tenant_update: dict[str, Any] = {
        "business_name": req.business_name,
        "business_type": req.business_type,
        "autopilot_enabled": True,
        "onboarding_completed_at": datetime.now(timezone.utc).isoformat(),
    }
    if req.city:
        tenant_update["city"] = req.city
    if req.phone:
        tenant_update["notification_phone"] = req.phone
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
    existing_widget = {}
    try:
        existing_widget_result = (
            db.table("widget_configs")
            .select("bot_name, primary_color, greeting_message, position")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if existing_widget_result.data:
            existing_widget = existing_widget_result.data[0] or {}
    except Exception:
        logger.warning("Failed to read existing widget config during onboarding for %s", tenant_id, exc_info=True)
    widget_updates: dict[str, Any] = {
        "bot_name": req.widget_bot_name or existing_widget.get("bot_name") or widget_defaults["bot_name"],
        "primary_color": req.widget_primary_color or existing_widget.get("primary_color") or widget_defaults["primary_color"],
        "greeting_message": req.widget_greeting_message or existing_widget.get("greeting_message") or widget_defaults["greeting_message"],
        "position": req.widget_position or existing_widget.get("position") or widget_defaults["position"],
    }
    try:
        db.table("widget_configs").update(widget_updates).eq("tenant_id", tenant_id).execute()
    except Exception:
        logger.error("Failed to update widget_configs during onboarding for %s", tenant_id, exc_info=True)

    industry_pack_applied = False
    industry_pack_key = None
    try:
        from backend.services.industry_packs import load_pack
        from backend.services.industry_packs.seed import apply_pack_to_tenant

        pack = load_pack(req.business_type)
        industry_pack_key = pack.key
        result = apply_pack_to_tenant(db, tenant_id, pack, dry_run=False)
        industry_pack_applied = True
        configured["industry_pack"] = True
        if result.errors:
            logger.warning(
                "Industry pack seeded with warnings for tenant=%s pack=%s errors=%s",
                tenant_id,
                pack.key,
                result.errors,
            )
    except Exception:
        logger.warning(
            "Failed to apply industry pack during onboarding for tenant %s",
            tenant_id,
            exc_info=True,
        )

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
        ]
        if req.city:
            faq_entries.append({
                "tenant_id": tenant_id,
                "question": "Where are you located?",
                "answer": f"We are located in {req.city}. Feel free to contact us for our exact address.",
                "category": "general",
                "is_active": True,
            })
        if req.phone:
            faq_entries.append({
                "tenant_id": tenant_id,
                "question": "How can I contact you?",
                "answer": f"You can reach us at {req.phone} or through this chat widget.",
                "category": "general",
                "is_active": True,
            })

        # Batched (audit 2026-06-10): per-row inserts were N+1 - the batched
        # pattern already used at the wizard-FAQ insert below.
        if faq_entries:
            try:
                db.table("faq_entries").insert(faq_entries).execute()
                faqs_created += len(faq_entries)
            except Exception:
                logger.exception("Failed to create FAQ entries for tenant %s", tenant_id)

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

    # 7. Auto-create a default "Welcome" email sequence so drip campaigns work out of the box
    try:
        existing_seqs = (
            db.table("email_sequences")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not existing_seqs.data:
            biz = req.business_name or "our team"
            seq_result = db.table("email_sequences").insert({
                "tenant_id": tenant_id,
                "name": "Welcome Series",
                "trigger_type": "lead_captured",
                "is_active": True,
            }).execute()
            if seq_result.data:
                seq_id = seq_result.data[0]["id"]
                welcome_steps = [
                    {
                        "sequence_id": seq_id,
                        "step_order": 1,
                        "delay_days": 0,
                        "delay_hours": 0,
                        "subject": f"Thanks for reaching out to {biz}!",
                        "body": (
                            f"<p>Hi {{{{name}}}},</p>"
                            f"<p>Thanks for getting in touch with {biz}! We received your message and "
                            f"wanted to make sure you know we're here to help.</p>"
                            f"<p>If you have any questions, just reply to this email or chat with us on our website.</p>"
                            f"<p>Best,<br/>{biz}</p>"
                        ),
                        "email_type": "html",
                        "is_active": True,
                    },
                    {
                        "sequence_id": seq_id,
                        "step_order": 2,
                        "delay_days": 2,
                        "delay_hours": 0,
                        "subject": f"Here's what {biz} can do for you",
                        "body": (
                            f"<p>Hi {{{{name}}}},</p>"
                            f"<p>We wanted to share a bit more about what we offer and how we can help.</p>"
                            f"<p>Whether you're looking for a quick question answered or ready to get started, "
                            f"we're just a message away.</p>"
                            f"<p>Visit our website to learn more or book a time that works for you.</p>"
                            f"<p>Best,<br/>{biz}</p>"
                        ),
                        "email_type": "html",
                        "is_active": True,
                    },
                    {
                        "sequence_id": seq_id,
                        "step_order": 3,
                        "delay_days": 5,
                        "delay_hours": 0,
                        "subject": f"Ready to get started with {biz}?",
                        "body": (
                            f"<p>Hi {{{{name}}}},</p>"
                            f"<p>Just checking in! If you're ready to move forward or have any questions, "
                            f"we'd love to hear from you.</p>"
                            f"<p>You can reply to this email, give us a call, or book an appointment "
                            f"directly through our website.</p>"
                            f"<p>Looking forward to working with you!</p>"
                            f"<p>Best,<br/>{biz}</p>"
                        ),
                        "email_type": "html",
                        "is_active": True,
                    },
                ]
                db.table("email_sequence_steps").insert(welcome_steps).execute()
                logger.info("Auto-created Welcome Series with 3 steps for tenant %s", tenant_id)
    except Exception:
        logger.warning("Failed to auto-create welcome email sequence for tenant %s", tenant_id, exc_info=True)

    return OnboardingCompleteResponse(
        tenant_id=tenant_id,
        business_name=req.business_name,
        configured=configured,
        ai_content_generated=ai_content_generated,
        crawl_started=crawl_started,
        faqs_created=faqs_created,
        industry_pack_applied=industry_pack_applied,
        industry_pack_key=industry_pack_key,
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

    try:
        message = await call_claude_messages(
            operation="onboarding.generate_kb",
            model="claude-sonnet-4-6",
            max_tokens=1200,
            timeout=30.0,
            messages=[{"role": "user", "content": prompt}],
            metadata={"tenant_id": tenant_id, "business_name": req.business_name, "business_type": req.business_type},
        )
        kb_text = message.text.strip()
    except Exception:
        logger.error("KB generation failed for tenant %s", tenant_id, exc_info=True)
        return GenerateKbResponse(knowledge_base=None, generated=False)

    # Persist to widget_configs
    try:
        db = get_service_supabase()
        db.table("widget_configs").update({"knowledge_base": kb_text}).eq("tenant_id", tenant_id).execute()
    except Exception:
        logger.error("Failed to persist knowledge_base for tenant %s", tenant_id, exc_info=True)
        # Still return the generated text - frontend can retry or proceed without persistence

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

    # SSRF prevention: validate URL before making any outbound requests
    from backend.services.url_validation import is_safe_url
    if not is_safe_url(req.url):
        raise HTTPException(
            status_code=400,
            detail="URL must be http/https and resolve to a public address",
        )

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
        # Onboarding v2: fall back to vertical preset before giving up.
        from backend.services.vertical_presets import get_vertical_preset
        db = get_service_supabase()
        tenant_for_preset = db.table("tenants").select("business_type").eq("id", tenant_id).single().execute()
        bt = (tenant_for_preset.data or {}).get("business_type") if tenant_for_preset else None
        preset = get_vertical_preset(bt)
        if preset:
            logger.info("auto_kb: empty scrape, seeding from %s preset for tenant=%s", bt, tenant_id)
            try:
                db.table("widget_configs").update({
                    "knowledge_base": preset["kb"],
                    "custom_instructions": preset["ci"],
                }).eq("tenant_id", tenant_id).execute()
                faq_rows = [
                    {"tenant_id": tenant_id, "question": f["question"], "answer": f["answer"], "category": f["category"], "is_active": True}
                    for f in preset["faqs"]
                ]
                db.table("faq_entries").insert(faq_rows).execute()
            except Exception:
                logger.warning("auto_kb: failed to persist preset for tenant %s", tenant_id, exc_info=True)
            return AutoKbResponse(
                knowledge_base=preset["kb"],
                custom_instructions=preset["ci"],
                faqs=[AutoKbFaqEntry(**f) for f in preset["faqs"]],
                pages_crawled=0,
                chars_extracted=0,
                services=list(preset["services"]),
                hours=dict(preset["hours"]),
            )
        raise HTTPException(status_code=422, detail="Could not extract content from the provided URL")

    # Truncate for Claude prompt
    content_for_prompt = extracted_text[:15000]

    # 3. Get tenant info for context
    db = get_service_supabase()
    tenant = db.table("tenants").select("business_name, business_type, city, phone").eq("id", tenant_id).single().execute()
    t = tenant.data or {}

    # 4. Call Claude to generate KB + FAQs + custom instructions

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

===SERVICES===
3-8 distinct services offered, one per line, no leading dash. Example:
Drain cleaning
Water heater repair
Sewer line service
Use only services mentioned or strongly implied by the website content.

===HOURS===
7 lines of business hours, one per day, format "Day: hours" or "Day: closed".
Use 3-letter day prefixes (Mon, Tue, Wed, Thu, Fri, Sat, Sun). Example:
Mon: 8am-6pm
Tue: 8am-6pm
Wed: 8am-6pm
Thu: 8am-6pm
Fri: 8am-6pm
Sat: 9am-2pm
Sun: closed
If hours are unclear from the content, omit this section entirely.

===FAQ_START===
8-10 FAQ entries in this exact format (one per line):
Q: [question]
A: [answer]
C: [category]
===FAQ_END===

Use only information from the website content. Be concise and accurate."""

    try:
        api_response = await call_claude_messages(
            operation="onboarding.auto_populate_kb",
            model="claude-sonnet-4-6",
            max_tokens=3000,
            temperature=0.3,
            timeout=60.0,
            messages=[{"role": "user", "content": prompt}],
            metadata={"tenant_id": tenant_id, "url": req.url, "pages_crawled": pages_crawled, "chars_extracted": chars_extracted},
        )
        raw = api_response.text
    except Exception:
        logger.error("auto_kb: Claude API failed for tenant %s", tenant_id, exc_info=True)
        raise HTTPException(status_code=502, detail="AI generation failed")

    # 5. Parse the response
    knowledge_base, custom_instructions, faqs, services, hours = _parse_auto_kb_response(raw)

    # v2: ensure structured fields populated even if Claude omitted markers
    # or KB only listed weekdays. Always return 7-key hours dict.
    from backend.services.vertical_presets import get_vertical_preset, get_default_hours_for
    preset = get_vertical_preset(t.get("business_type"))
    if not services and preset:
        services = list(preset["services"])
    default_hours = get_default_hours_for(t.get("business_type"))
    for day, val in default_hours.items():
        hours.setdefault(day, val)

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
        services=services,
        hours=hours,
    )


@router.get("/{tenant_id}/status", response_model=OnboardingStatusResponse)
async def onboarding_status(
    tenant_id: str,
    claims: dict = Depends(require_role("owner", "admin", "member")),
):
    """Returns onboarding progress with completion percentage."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()

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


# ---------------------------------------------------------------------------
# Industry Pack endpoints - seed turnkey workflow bundles by business_type
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

    Not tenant-scoped - packs are global read-only content. Used by the
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
    KB seed articles) into the tenant. Idempotent - re-running skips any
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
