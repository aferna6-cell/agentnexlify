"""Shared helper: generate widget KB + FAQs + custom instructions from text.

Both the website-crawl (auto-kb) endpoint and the no-website description
endpoint (describe-kb) call this. The ONLY difference between them is how
the source text is obtained; everything from Claude invocation onward is
identical.

NOTE: Live GBP / Facebook API enrichment is a future ops step once the
platform obtains the relevant OAuth credentials.  Today the caller may pass
those URLs as plain context text only.
"""

import logging

from backend.services.llm_runtime import call_claude_messages

logger = logging.getLogger(__name__)

# Re-used between both callers — keep in sync with auto-kb prompt.
_KB_PROMPT_TEMPLATE = """You are setting up an AI chat assistant for a business. Based on the provided business information, generate three things:

BUSINESS INFO:
Name: {business_name}
Type: {business_type}
Location: {city}
Phone: {phone}
{extra_context}

BUSINESS DESCRIPTION:
{content_for_prompt}

Generate the following sections separated by exact markers:

===KNOWLEDGE_BASE===
A structured markdown knowledge base (under 3000 chars) with sections:
- About the business (2-3 sentences)
- Products/Services (bullet list)
- Location & Contact
- Key selling points
- How to get started
Do NOT invent facts not supported by the description.

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
Use only services mentioned or strongly implied by the description.

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
If hours are unclear from the description, omit this section entirely.

===FAQ_START===
8-10 FAQ entries in this exact format (one per line):
Q: [question]
A: [answer]
C: [category]
===FAQ_END===

Use only information from the description. Be concise and accurate."""


async def generate_kb_from_text(
    *,
    tenant_id: str,
    business_name: str,
    business_type: str,
    city: str,
    phone: str,
    content_for_prompt: str,
    extra_context: str = "",
    operation: str = "onboarding.generate_kb_from_text",
) -> str:
    """Call Claude and return the raw structured response string.

    Raises HTTPException(502) on Claude failure (callers handle persistence).
    Returns raw text for the caller to parse with _parse_auto_kb_response.
    """
    from fastapi import HTTPException

    prompt = _KB_PROMPT_TEMPLATE.format(
        business_name=business_name,
        business_type=business_type,
        city=city or "Unknown",
        phone=phone or "Not provided",
        extra_context=extra_context,
        content_for_prompt=content_for_prompt,
    )

    try:
        api_response = await call_claude_messages(
            operation=operation,
            model="claude-sonnet-4-6",
            max_tokens=3000,
            temperature=0.3,
            timeout=60.0,
            messages=[{"role": "user", "content": prompt}],
            metadata={"tenant_id": tenant_id},
        )
        return api_response.text
    except Exception:
        logger.error(
            "kb_from_text: Claude API failed for tenant %s", tenant_id, exc_info=True
        )
        raise HTTPException(status_code=502, detail="AI generation failed")
