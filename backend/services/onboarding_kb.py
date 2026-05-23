"""Knowledge-base generation orchestrators for onboarding endpoints.

Split out of `backend/routers/onboarding.py` to keep the router thin.

Public API:
- `run_generate_kb(db, tenant_id, req) -> GenerateKbResult`
- `run_auto_populate_kb(db, tenant_id, req) -> AutoKbResult`

Both functions raise `fastapi.HTTPException` at the same boundaries the
original endpoints did, so router handlers stay one-liners.
"""

import logging
import re as _re
from dataclasses import dataclass, field
from typing import Any

import httpx
from fastapi import HTTPException

from backend.services.llm_runtime import call_claude_messages
from backend.services.onboarding_ai import AutoKbFaqEntry, parse_auto_kb_response
from backend.services.url_validation import is_safe_url
from backend.services.vertical_presets import (
    get_default_hours_for,
    get_vertical_preset,
)
from backend.services.website_crawler import get_crawled_content, start_crawl

logger = logging.getLogger(__name__)


@dataclass
class GenerateKbResult:
    knowledge_base: str | None
    generated: bool


@dataclass
class AutoKbResult:
    knowledge_base: str
    custom_instructions: str
    faqs: list[AutoKbFaqEntry]
    pages_crawled: int
    chars_extracted: int
    services: list[str] = field(default_factory=list)
    hours: dict[str, str] = field(default_factory=dict)


def _format_hours_for_prompt(hours: dict[str, Any] | None) -> str:
    if not hours:
        return "Not specified"
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    lines: list[str] = []
    tz = hours.get("timezone", "")
    for day in days:
        day_cfg = hours.get(day)
        if not day_cfg:
            continue
        if day_cfg.get("enabled") or (day_cfg.get("open") and day_cfg.get("close")):
            open_t = day_cfg.get("open") or day_cfg.get("start", "09:00")
            close_t = day_cfg.get("close") or day_cfg.get("end", "17:00")
            lines.append(f"  {day.capitalize()}: {open_t} – {close_t}")
        else:
            lines.append(f"  {day.capitalize()}: Closed")
    out = "\n".join(lines)
    if tz:
        out += f"\n  Timezone: {tz}"
    return out


async def run_generate_kb(db, tenant_id: str, req) -> GenerateKbResult:
    """Generate an AI knowledge base from onboarding answers and persist it."""
    hours_text = _format_hours_for_prompt(req.hours)
    services_text = ", ".join(req.services) if req.services else "Not specified"
    faqs_text = (
        "\n".join(f"Q: {faq.question}\nA: {faq.answer}" for faq in req.faqs)
        if req.faqs
        else "None provided"
    )

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
            metadata={
                "tenant_id": tenant_id,
                "business_name": req.business_name,
                "business_type": req.business_type,
            },
        )
        kb_text = message.text.strip()
    except Exception:
        logger.error("KB generation failed for tenant %s", tenant_id, exc_info=True)
        return GenerateKbResult(knowledge_base=None, generated=False)

    try:
        db.table("widget_configs").update({"knowledge_base": kb_text}).eq(
            "tenant_id", tenant_id
        ).execute()
    except Exception:
        logger.error(
            "Failed to persist knowledge_base for tenant %s", tenant_id, exc_info=True
        )

    return GenerateKbResult(knowledge_base=kb_text, generated=True)


async def _fallback_http_fetch(url: str) -> tuple[str, int]:
    """Fallback when the crawler returns nothing — strip tags from a single GET."""
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http:
            resp = await http.get(url, headers={"User-Agent": "AgentNexLiFy-Bot/1.0"})
            if resp.status_code == 200:
                html = resp.text
                text = _re.sub(r"<script[^>]*>.*?</script>", "", html, flags=_re.DOTALL)
                text = _re.sub(r"<style[^>]*>.*?</style>", "", text, flags=_re.DOTALL)
                text = _re.sub(r"<[^>]+>", " ", text)
                text = _re.sub(r"\s+", " ", text).strip()
                truncated = text[:15000]
                return truncated, 1
    except Exception:
        logger.warning("auto_kb: fallback HTTP fetch failed for %s", url, exc_info=True)
    return "", 0


def _seed_preset_for_empty_scrape(
    db, tenant_id: str, business_type: str | None
) -> AutoKbResult | None:
    preset = get_vertical_preset(business_type)
    if not preset:
        return None
    logger.info(
        "auto_kb: empty scrape, seeding from %s preset for tenant=%s",
        business_type,
        tenant_id,
    )
    try:
        db.table("widget_configs").update(
            {
                "knowledge_base": preset["kb"],
                "custom_instructions": preset["ci"],
            }
        ).eq("tenant_id", tenant_id).execute()
        faq_rows = [
            {
                "tenant_id": tenant_id,
                "question": f["question"],
                "answer": f["answer"],
                "category": f["category"],
                "is_active": True,
            }
            for f in preset["faqs"]
        ]
        db.table("faq_entries").insert(faq_rows).execute()
    except Exception:
        logger.warning(
            "auto_kb: failed to persist preset for tenant %s", tenant_id, exc_info=True
        )
    return AutoKbResult(
        knowledge_base=preset["kb"],
        custom_instructions=preset["ci"],
        faqs=[AutoKbFaqEntry(**f) for f in preset["faqs"]],
        pages_crawled=0,
        chars_extracted=0,
        services=list(preset["services"]),
        hours=dict(preset["hours"]),
    )


def _build_auto_kb_prompt(tenant_info: dict, url: str, content: str) -> str:
    return f"""You are setting up an AI chat assistant for a business. Based on their website content, generate three things:

BUSINESS INFO:
Name: {tenant_info.get("business_name", "Unknown")}
Type: {tenant_info.get("business_type", "business")}
Location: {tenant_info.get("city", "Unknown")}
Phone: {tenant_info.get("phone", "Not provided")}
Website: {url}

WEBSITE CONTENT:
{content}

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


async def run_auto_populate_kb(db, tenant_id: str, req) -> AutoKbResult:
    """Crawl a website URL and auto-generate KB + FAQs + custom instructions."""
    if not is_safe_url(req.url):
        raise HTTPException(
            status_code=400,
            detail="URL must be http/https and resolve to a public address",
        )

    logger.info("auto_kb: starting for tenant=%s url=%s", tenant_id, req.url)

    try:
        crawl_result = await start_crawl(tenant_id, req.url)
        pages_crawled = crawl_result.get("pages_found", 0)
    except Exception:
        logger.error("auto_kb: crawl failed for %s", req.url, exc_info=True)
        pages_crawled = 0

    extracted_text = get_crawled_content(tenant_id) or ""
    chars_extracted = len(extracted_text)

    if not extracted_text:
        extracted_text, fb_pages = await _fallback_http_fetch(req.url)
        chars_extracted = len(extracted_text)
        if fb_pages:
            pages_crawled = fb_pages

    if not extracted_text:
        tenant_for_preset = (
            db.table("tenants")
            .select("business_type")
            .eq("id", tenant_id)
            .single()
            .execute()
        )
        tenant_row = (
            tenant_for_preset.data
            if (tenant_for_preset and tenant_for_preset.data)
            else {}
        )
        business_type = tenant_row.get("business_type") if isinstance(tenant_row, dict) else None
        seeded = _seed_preset_for_empty_scrape(db, tenant_id, business_type)
        if seeded:
            return seeded
        raise HTTPException(
            status_code=422,
            detail="Could not extract content from the provided URL",
        )

    content_for_prompt = extracted_text[:15000]
    tenant = (
        db.table("tenants")
        .select("business_name, business_type, city, phone")
        .eq("id", tenant_id)
        .single()
        .execute()
    )
    t = tenant.data or {}
    if not isinstance(t, dict):
        t = {}

    prompt = _build_auto_kb_prompt(t, req.url, content_for_prompt)

    try:
        api_response = await call_claude_messages(
            operation="onboarding.auto_populate_kb",
            model="claude-sonnet-4-6",
            max_tokens=3000,
            temperature=0.3,
            timeout=60.0,
            messages=[{"role": "user", "content": prompt}],
            metadata={
                "tenant_id": tenant_id,
                "url": req.url,
                "pages_crawled": pages_crawled,
                "chars_extracted": chars_extracted,
            },
        )
        raw = api_response.text
    except Exception:
        logger.error("auto_kb: Claude API failed for tenant %s", tenant_id, exc_info=True)
        raise HTTPException(status_code=502, detail="AI generation failed")

    knowledge_base, custom_instructions, faqs, services, hours = parse_auto_kb_response(raw)

    bt = t.get("business_type") if isinstance(t, dict) else None
    preset = get_vertical_preset(bt)
    if not services and preset:
        services = list(preset["services"])
    default_hours = get_default_hours_for(bt)
    for day, val in default_hours.items():
        hours.setdefault(day, val)

    try:
        db.table("widget_configs").update(
            {
                "knowledge_base": knowledge_base,
                "custom_instructions": custom_instructions,
            }
        ).eq("tenant_id", tenant_id).execute()
    except Exception:
        logger.error(
            "auto_kb: failed to persist KB for tenant %s", tenant_id, exc_info=True
        )

    if faqs:
        try:
            faq_rows = [
                {
                    "tenant_id": tenant_id,
                    "question": f.question,
                    "answer": f.answer,
                    "category": f.category,
                    "is_active": True,
                }
                for f in faqs
            ]
            db.table("faq_entries").insert(faq_rows).execute()
        except Exception:
            logger.error(
                "auto_kb: failed to persist FAQs for tenant %s",
                tenant_id,
                exc_info=True,
            )

    logger.info(
        "auto_kb: completed for tenant=%s kb=%d chars, ci=%d chars, faqs=%d, pages=%d",
        tenant_id,
        len(knowledge_base),
        len(custom_instructions),
        len(faqs),
        pages_crawled,
    )

    return AutoKbResult(
        knowledge_base=knowledge_base,
        custom_instructions=custom_instructions,
        faqs=faqs,
        pages_crawled=pages_crawled,
        chars_extracted=chars_extracted,
        services=services,
        hours=hours,
    )
