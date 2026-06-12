"""Auto-create a personalized Agent OS welcome thread on first tenant signup.

Deterministic-first — no LLM call. Message is composed from templates and
the per-vertical guidance pack from os_kb_feed.vertical_guidance().

Schema note: os_threads and os_messages use client_id (NOT tenant_id) per
backend.services.tenant_scope._TENANT_COLUMN_OVERRIDES.  tenant_table()
injects the correct column automatically.

Every step is fault-tolerant with logging. A failure here MUST NOT break
signup.
"""

import logging
from typing import Any

from backend.services.os_kb_feed import vertical_guidance
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

_WELCOME_THREAD_TITLE = "Welcome to your Agent OS"

# Vertical-specific prompt triples.  Each entry maps an os_kb_feed alias key
# to three short prompts the owner can literally type in the composer.
# Keys match the resolved VERTICAL_GUIDANCE keys in os_kb_feed.py.
_VERTICAL_PROMPTS: dict[str, list[str]] = {
    "home_services": [
        "Did we miss any calls today? Draft the callback texts.",
        "Follow up on any open estimates older than 3 days.",
        "What emergency calls came in from the widget this week?",
    ],
    "auto_repair": [
        "Follow up on open repair quotes from this week.",
        "What vehicles are waiting on parts approval?",
        "Draft a reminder for tomorrow's scheduled appointments.",
    ],
    "salon": [
        "Who hasn't rebooked in the last 6 weeks?",
        "Follow up on open booking requests from the widget.",
        "Draft a day-before reminder for tomorrow's appointments.",
    ],
    "dental": [
        "Who's overdue for a 6-month check-up?",
        "Follow up on any open treatment plan conversations.",
        "What came in from the widget today?",
    ],
    "realestate": [
        "What new leads came in from the widget this week?",
        "Follow up with buyers who requested a showing.",
        "Draft a monthly market-update email for my list.",
    ],
    "financial_services": [
        "Who started a trial this week and hasn't engaged yet?",
        "Draft a day-3 check-in for new trial members.",
        "Follow up with subscribers who cancelled last month.",
    ],
    "_default": [
        "What came in from the widget today?",
        "Follow up with leads who haven't heard from us.",
        "Draft a reminder for tomorrow's appointments.",
    ],
}

# Maps os_kb_feed _TYPE_ALIASES resolved keys to _VERTICAL_PROMPTS keys.
# os_kb_feed already resolves aliases to canonical keys; we mirror that here
# for the prompt selection so both files stay in sync.
_GUIDANCE_KEY_TO_PROMPT_KEY: dict[str, str] = {
    "home_services": "home_services",
    "auto_repair": "auto_repair",
    "salon": "salon",
    "dental": "dental",
    "realestate": "realestate",
    "financial_services": "financial_services",
    "_default": "_default",
}


def _resolve_prompt_key(business_type: str | None) -> str:
    """Return the _VERTICAL_PROMPTS key for a business_type string."""
    from backend.services.os_kb_feed import _TYPE_ALIASES  # local import to stay import-cheap

    raw = (business_type or "").strip().lower()
    guidance_key = _TYPE_ALIASES.get(raw, "_default")
    return _GUIDANCE_KEY_TO_PROMPT_KEY.get(guidance_key, "_default")


def _compose_welcome_message(
    business_name: str,
    business_type: str | None,
    website_url: str | None,
) -> str:
    """Compose the deterministic welcome message for the first assistant turn.

    Structure:
      1. Greeting with business name.
      2. One sentence showing vertical awareness (from the guidance pack).
      3. Optional website line (only when website_url is provided).
      4. "Three things you can try right now:" + 3 vertical-appropriate prompts.
    """
    # 1. Greeting
    safe_name = (business_name or "your business").strip()
    lines: list[str] = [
        f"Hi, and welcome to your Agent OS for {safe_name}!",
        "",
        "I'm your AI staff — I can send follow-ups, draft messages, book "
        "appointments, and surface anything that needs your attention, all from "
        "this inbox.",
    ]

    # 2. Vertical-flavored sentence pulled from the guidance pack
    guidance = vertical_guidance(business_type)
    if guidance:
        first_entry = guidance[0]
        answer_text = first_entry.get("answer", "")
        # Pull the first sentence of the answer for a concise flavour hint.
        # Sentences end with ". " or end-of-string.
        first_sentence = answer_text.split(".")[0].strip()
        if first_sentence:
            lines.append("")
            lines.append(
                f"I already know a bit about how {safe_name} works: {first_sentence}."
            )

    # 3. Website line
    if website_url:
        safe_url = str(website_url).strip().rstrip("/")
        lines.append("")
        lines.append(
            f"I'm reading {safe_url} to learn your services — ask me what I "
            "found in a few minutes."
        )

    # 4. Three starter prompts
    prompt_key = _resolve_prompt_key(business_type)
    prompts = _VERTICAL_PROMPTS.get(prompt_key, _VERTICAL_PROMPTS["_default"])
    lines.append("")
    lines.append("Three things you can try right now:")
    for i, prompt in enumerate(prompts[:3], start=1):
        lines.append(f'{i}. "{prompt}"')

    return "\n".join(lines)


async def create_welcome_thread(
    db: Any,
    *,
    tenant_id: str,
    business_name: str,
    business_type: str | None,
    website_url: str | None = None,
) -> str | None:
    """Insert a welcome os_thread + one assistant message for a new tenant.

    Returns the thread id on success, or None on any failure (fault-tolerant
    — a failure must never break signup).

    Idempotent: if a thread titled _WELCOME_THREAD_TITLE already exists for
    the tenant, returns its id without inserting new rows.
    """
    # 1. Idempotency check
    try:
        existing = (
            tenant_table(db, "os_threads", tenant_id)
            .select("id")
            .eq("title", _WELCOME_THREAD_TITLE)
            .limit(1)
            .execute()
        )
        if existing.data:
            thread_id = existing.data[0]["id"]
            logger.info(
                "welcome_thread: already exists tenant=%s thread_id=%s",
                tenant_id,
                thread_id,
            )
            return thread_id
    except Exception:
        logger.warning(
            "welcome_thread: idempotency check failed tenant=%s — continuing with insert",
            tenant_id,
            exc_info=True,
        )

    # 2. Insert os_threads row
    thread_id: str | None = None
    try:
        result = (
            tenant_table(db, "os_threads", tenant_id)
            .insert(
                {
                    "title": _WELCOME_THREAD_TITLE,
                    "source": "system",
                    "status": "open",
                    "created_by": "system",
                }
            )
            .execute()
        )
        thread_id = result.data[0]["id"] if result.data else None
    except Exception:
        logger.warning(
            "welcome_thread: os_threads insert failed tenant=%s",
            tenant_id,
            exc_info=True,
        )
        return None

    if not thread_id:
        logger.warning(
            "welcome_thread: os_threads insert returned no data tenant=%s", tenant_id
        )
        return None

    # 3. Insert os_messages row (assistant-role welcome message)
    try:
        message_content = _compose_welcome_message(
            business_name=business_name,
            business_type=business_type,
            website_url=website_url,
        )
        tenant_table(db, "os_messages", tenant_id).insert(
            {
                "thread_id": thread_id,
                "role": "assistant",
                "content": message_content,
            }
        ).execute()
    except Exception:
        logger.warning(
            "welcome_thread: os_messages insert failed tenant=%s thread_id=%s",
            tenant_id,
            thread_id,
            exc_info=True,
        )
        # Thread was created successfully; return its id even if message insert failed.
        # The owner still sees the thread — the missing message is recoverable.

    logger.info(
        "welcome_thread: created tenant=%s thread_id=%s business_type=%s",
        tenant_id,
        thread_id,
        business_type,
    )
    return thread_id
