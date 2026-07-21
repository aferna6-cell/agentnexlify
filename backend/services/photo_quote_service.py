"""Photo-quote assessment service — vision → pricing → quote shape (#37 core).

The testable brain of the ``POST /api/widget/photo-quote`` endpoint: validate the
upload, build the vision prompt from the tenant's pricing rules (#38), call the
model through ``llm_runtime`` (injected), parse the response into the
``quote_requests`` row shape, and gate ``needs_human`` on the per-vertical
confidence floor. Storage upload, thumbnailing, and multipart parsing live in the
router (they are I/O); this module holds the logic so it is unit-testable.

Dependencies (the model call, the #38 prompt builder + threshold resolver, the
db) are injected. The #38 helpers are lazy-imported inside the function bodies so
this module imports cleanly even before ``photo_quote_prompts`` merges, and so
tests can pass fakes without touching it.

``quote_requests`` is ``client_id``-scoped (migration 108).
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)

# 3x-vision assessment runs on the current top Opus (rules/model-routing.md,
# rules/vision-3x.md). Kept as a module constant so the router does not hardcode it.
MODEL = "claude-opus-4-8"
MAX_TOKENS = 800

ALLOWED_MEDIA_TYPES = frozenset({"image/jpeg", "image/png"})
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB
DEFAULT_DAILY_QUOTA = 50
VALID_SEVERITY = frozenset({"minor", "major", "needs_human"})


def validate_image(media_type: str | None, size_bytes: int) -> str | None:
    """Return an error code for a bad upload, or None when the image is fine."""
    if media_type not in ALLOWED_MEDIA_TYPES:
        return "unsupported_media_type"
    if size_bytes <= 0:
        return "empty_image"
    if size_bytes > MAX_IMAGE_BYTES:
        return "image_too_large"
    return None


def _strip_json_fence(text: str) -> str:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _clamp_confidence(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _non_negative_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _needs_human_result(summary: str) -> dict:
    return {
        "quote_low": 0,
        "quote_high": 0,
        "severity": "needs_human",
        "confidence": 0.0,
        "summary": summary,
        "needs_human": True,
    }


def parse_quote_response(
    raw_text: str,
    rules_row: Any,
    industry: str,
    *,
    resolve_threshold: Callable[[Any], float] | None = None,
) -> dict:
    """Parse the model's JSON into the quote shape and gate ``needs_human``.

    ``needs_human`` is true when the model says so OR when confidence is below
    the tenant's per-vertical floor (#38 ``resolve_confidence_threshold``). On
    that gate, or on an unparseable response, the price range is zeroed — a
    human quotes it rather than the widget showing a guessed number.
    """
    if resolve_threshold is None:
        from backend.services.photo_quote_prompts import (
            resolve_confidence_threshold as resolve_threshold,
        )

    try:
        parsed = json.loads(_strip_json_fence(raw_text))
    except (json.JSONDecodeError, TypeError):
        logger.warning("photo_quote_service: unparseable model response")
        return _needs_human_result("Could not read the photo — a team member will follow up.")

    if not isinstance(parsed, dict):
        return _needs_human_result("Could not read the photo — a team member will follow up.")

    severity = parsed.get("severity")
    if severity not in VALID_SEVERITY:
        severity = "needs_human"
    confidence = _clamp_confidence(parsed.get("confidence"))
    summary = str(parsed.get("summary") or "").strip()[:1000]

    threshold = resolve_threshold(rules_row)
    needs_human = severity == "needs_human" or confidence < threshold

    if needs_human:
        return {
            "quote_low": 0,
            "quote_high": 0,
            "severity": "needs_human",
            "confidence": confidence,
            "summary": summary or "This needs a person to price — a team member will follow up.",
            "needs_human": True,
        }

    quote_low = _non_negative_int(parsed.get("quote_low"))
    quote_high = _non_negative_int(parsed.get("quote_high"))
    if quote_high < quote_low:
        quote_low, quote_high = quote_high, quote_low
    return {
        "quote_low": quote_low,
        "quote_high": quote_high,
        "severity": severity,
        "confidence": confidence,
        "summary": summary,
        "needs_human": False,
    }


def is_over_daily_quota(
    db,
    client_id: str,
    *,
    limit: int = DEFAULT_DAILY_QUOTA,
    now: datetime | None = None,
) -> bool:
    """True when the tenant already hit today's photo-quote quota.

    Fail-open: a count error returns False (do not block a paying customer's
    upload on a transient DB hiccup) — the quota is a cost guard, not security.
    """
    now = now or datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    try:
        res = (
            db.table("quote_requests")
            .select("id", count="exact")
            .eq("client_id", client_id)
            .gte("created_at", day_start)
            .limit(1)
            .execute()
        )
        return bool(res.count is not None and res.count >= limit)
    except Exception:
        logger.warning("photo_quote_service: quota check failed — allowing the request")
        return False


async def assess_photo(
    image_b64: str,
    media_type: str,
    rules_row: Any,
    industry: str,
    *,
    llm_call: Callable[..., Any],
    build_prompt: Callable[[Any, str], str] | None = None,
    resolve_threshold: Callable[[Any], float] | None = None,
) -> dict:
    """Run the vision assessment and return the parsed quote shape.

    ``llm_call`` is ``llm_runtime.call_claude_messages`` (injected). The #38
    prompt builder + threshold resolver are lazy-imported defaults so this module
    loads without them and tests can inject fakes.
    """
    if build_prompt is None:
        from backend.services.photo_quote_prompts import build_vision_prompt as build_prompt

    system_prompt = build_prompt(rules_row, industry)
    content = [
        {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": image_b64},
        },
        {"type": "text", "text": "Assess this photo and quote it per the pricing rules."},
    ]

    result = await llm_call(
        operation="photo_quote.assess",
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": content}],
        metadata={"industry": industry},
    )
    return parse_quote_response(
        result.text, rules_row, industry, resolve_threshold=resolve_threshold
    )
