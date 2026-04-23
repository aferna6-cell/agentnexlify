"""Photo quote widget endpoint — POST /api/widget/photo-quote and GET /api/quotes.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI.
Do NOT add 'from __future__ import annotations' to this file.
"""

import io
import json
import logging
import os
import uuid
from collections import deque
from datetime import date, datetime, timezone
from typing import Any

import anthropic
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from backend.models.database import get_service_supabase
from backend.services.llm_runtime import call_claude_messages

logger = logging.getLogger(__name__)

router = APIRouter(tags=["widget"])
dashboard_router = APIRouter(tags=["quotes"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB
PHOTO_QUOTES_BUCKET = os.getenv("PHOTO_QUOTES_BUCKET", "photo-quotes")
DAILY_QUOTA = 50  # hard daily quota per tenant
OVERAGE_THRESHOLD = 500  # start billing overage after this

DEFAULT_DISCLAIMER = "Estimate only — final quote subject to inspection."

CONFIDENCE_DEFAULTS: dict[str, float] = {
    "plumbing": 0.7,
    "roofing": 0.8,
    "hvac": 0.75,
    "auto_body": 0.75,
    "landscaping": 0.7,
    "pest": 0.7,
}

# ---------------------------------------------------------------------------
# In-memory rate limit (5 uploads/min per conversation_id)
# NOTE: per-worker only — for production use Redis or DB-backed rate limiting
# ---------------------------------------------------------------------------
_rate_buckets: dict[str, deque] = {}


def _check_rate_limit(conversation_id: str | None) -> bool:
    """Return True if allowed, False if rate-limited."""
    if not conversation_id:
        return True
    now_ts = datetime.now(timezone.utc).timestamp()
    bucket = _rate_buckets.setdefault(conversation_id, deque())
    # drop entries older than 60 seconds
    while bucket and bucket[0] < now_ts - 60:
        bucket.popleft()
    if len(bucket) >= 5:
        return False
    bucket.append(now_ts)
    return True


# ---------------------------------------------------------------------------
# Helper: resolve tenant from api_key
# ---------------------------------------------------------------------------


def _get_tenant_by_api_key(api_key: str) -> dict[str, Any]:
    db = get_service_supabase()
    result = (
        db.table("widget_configs")
        .select("tenant_id, photo_quote_enabled")
        .eq("api_key", api_key)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=403, detail="Invalid API key")
    row = result.data[0]
    if not row.get("photo_quote_enabled"):
        raise HTTPException(
            status_code=403,
            detail="Photo quotes not enabled for this tenant",
        )
    return row


def _get_pricing_rules(client_id: str) -> dict[str, Any]:
    db = get_service_supabase()
    try:
        result = (
            db.table("tenant_pricing_rules")
            .select("industry, rules_jsonb, disclaimer_text, min_confidence_threshold")
            .eq("client_id", client_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else {}
    except Exception as exc:
        logger.warning(
            "photo_quote: pricing rules fetch failed client_id=%s",
            client_id,
            exc_info=exc,
        )
        return {}


# ---------------------------------------------------------------------------
# Helper: daily quota check + usage upsert
# ---------------------------------------------------------------------------


def _check_and_increment_quota(client_id: str) -> tuple[int, bool]:
    """Return (current_count, overage_triggered). Increments atomically via upsert."""
    db = get_service_supabase()
    today = date.today().isoformat()
    try:
        # fetch current
        result = (
            db.table("tenant_quote_usage")
            .select("quote_count, overage_count")
            .eq("client_id", client_id)
            .eq("period_start", today)
            .limit(1)
            .execute()
        )
        current_count = result.data[0]["quote_count"] if result.data else 0
        if current_count >= DAILY_QUOTA:
            return current_count, False

        # upsert increment
        db.table("tenant_quote_usage").upsert(
            {
                "client_id": client_id,
                "period_start": today,
                "quote_count": current_count + 1,
                "overage_count": (
                    result.data[0].get("overage_count", 0) if result.data else 0
                ),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="client_id,period_start",
        ).execute()

        overage = (current_count + 1) > OVERAGE_THRESHOLD
        if overage:
            _fire_stripe_overage(client_id)

        return current_count + 1, overage
    except Exception as exc:
        logger.warning(
            "photo_quote: quota check failed client_id=%s", client_id, exc_info=exc
        )
        return 0, False


def _fire_stripe_overage(client_id: str) -> None:
    price_id = os.getenv("STRIPE_PHOTO_QUOTE_PRICE_ID", "")
    if not price_id:
        return
    try:
        import stripe

        stripe.billing_util.report_usage_record(
            subscription_item=price_id,
            quantity=1,
            action="increment",
        )
        logger.info("photo_quote: stripe overage reported client_id=%s", client_id)
    except Exception as exc:
        logger.warning(
            "photo_quote: stripe overage report failed client_id=%s",
            client_id,
            exc_info=exc,
        )


# ---------------------------------------------------------------------------
# Helper: upload image to Supabase Storage
# ---------------------------------------------------------------------------


def _upload_to_storage(client_id: str, image_bytes: bytes, content_type: str) -> str:
    ext = "jpg" if content_type == "image/jpeg" else "png"
    path = f"{client_id}/{uuid.uuid4().hex}.{ext}"
    db = get_service_supabase()
    db.storage.from_(PHOTO_QUOTES_BUCKET).upload(
        path,
        image_bytes,
        {"content-type": content_type},
    )
    # build public URL
    public_url_response = db.storage.from_(PHOTO_QUOTES_BUCKET).get_public_url(path)
    if isinstance(public_url_response, str):
        return public_url_response
    return (
        public_url_response.get("publicURL")
        or public_url_response.get("publicUrl")
        or path
    )


def _make_thumbnail(
    image_bytes: bytes, content_type: str, client_id: str
) -> str | None:
    """Create 256px thumbnail; return storage URL or None on failure."""
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        long_edge = max(img.width, img.height)
        if long_edge > 256:
            scale = 256 / long_edge
            new_w = max(1, int(img.width * scale))
            new_h = max(1, int(img.height * scale))
            img = img.resize((new_w, new_h), Image.LANCZOS)
        buf = io.BytesIO()
        fmt = "JPEG" if content_type == "image/jpeg" else "PNG"
        img.save(buf, format=fmt)
        thumb_bytes = buf.getvalue()
        ext = "jpg" if content_type == "image/jpeg" else "png"
        path = f"{client_id}/thumb_{uuid.uuid4().hex}.{ext}"
        db = get_service_supabase()
        db.storage.from_(PHOTO_QUOTES_BUCKET).upload(
            path,
            thumb_bytes,
            {"content-type": content_type},
        )
        public_url_response = db.storage.from_(PHOTO_QUOTES_BUCKET).get_public_url(path)
        if isinstance(public_url_response, str):
            return public_url_response
        return public_url_response.get("publicURL") or public_url_response.get(
            "publicUrl"
        )
    except ImportError:
        # TODO: install Pillow via pip install --break-system-packages pillow
        logger.warning("photo_quote: Pillow not available, skipping thumbnail")
        return None
    except Exception as exc:
        logger.warning("photo_quote: thumbnail generation failed", exc_info=exc)
        return None


# ---------------------------------------------------------------------------
# Helper: call Claude Opus 4.7 vision
# ---------------------------------------------------------------------------


def _build_quote_prompt(pricing_rules: dict[str, Any]) -> str:
    rules_text = ""
    if pricing_rules.get("rules_jsonb"):
        try:
            rules = pricing_rules["rules_jsonb"]
            if isinstance(rules, str):
                rules = json.loads(rules)
            rules_text = (
                f"\n\nPricing rules for this business:\n{json.dumps(rules, indent=2)}"
            )
        except Exception:
            pass

    industry = pricing_rules.get("industry", "general")
    disclaimer = pricing_rules.get("disclaimer_text") or DEFAULT_DISCLAIMER

    return f"""You are a damage assessment AI for a {industry} business. Analyze the photo and provide a quote estimate.

{rules_text}

Respond ONLY with valid JSON matching this exact schema:
{{
  "quote_low": <integer dollars, e.g. 150>,
  "quote_high": <integer dollars, e.g. 400>,
  "severity": "<minor|major|needs_human>",
  "confidence": <float 0.0-1.0>,
  "summary": "<1-2 sentence description of damage and reasoning>",
  "needs_human": <true|false>
}}

Rules:
- quote_low and quote_high are dollar amounts (NOT cents)
- severity "minor" = routine fix under $500, "major" = significant work over $500, "needs_human" = cannot assess from photo
- confidence reflects how clearly you can assess from this photo
- needs_human = true when photo is unclear, damage is ambiguous, or confidence < 0.6
- If you cannot assess, set needs_human=true and severity="needs_human"

Disclaimer to include in your reasoning (NOT in the JSON): {disclaimer}"""


async def _call_claude_vision(
    image_bytes: bytes,
    content_type: str,
    pricing_rules: dict[str, Any],
    client_id: str,
) -> dict[str, Any]:
    import base64

    image_b64 = base64.b64encode(image_bytes).decode()
    media_type = content_type  # "image/jpeg" or "image/png"

    system_prompt = _build_quote_prompt(pricing_rules)

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_b64,
                    },
                },
                {
                    "type": "text",
                    "text": "Please analyze this photo and provide a quote estimate in the JSON format specified.",
                },
            ],
        }
    ]

    result = await call_claude_messages(
        operation="photo_quote.vision",
        model="claude-opus-4-7",
        max_tokens=512,
        messages=messages,
        temperature=None,  # omit for Opus 4.7
        system=system_prompt,
        timeout=45.0,
        metadata={"client_id": client_id},
    )

    raw = result.text.strip()
    # strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    parsed = json.loads(raw)
    return parsed


# ---------------------------------------------------------------------------
# POST /api/widget/photo-quote
# ---------------------------------------------------------------------------


@router.post("/photo-quote")
async def photo_quote(
    image: UploadFile = File(...),
    api_key: str = Form(...),
    conversation_id: str = Form(None),
):
    """Accept an uploaded damage photo and return an AI-generated quote range."""
    try:
        # 1. Auth: resolve tenant from api_key
        widget_row = _get_tenant_by_api_key(api_key)
        client_id = widget_row["tenant_id"]

        # 2. Rate limit: 5 uploads/min per conversation
        if not _check_rate_limit(conversation_id):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too many photo uploads. Please wait a moment.",
                    "needs_human": True,
                },
            )

        # 3. Validate image
        content_type = image.content_type or ""
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=400, detail="Only JPEG and PNG images are accepted."
            )

        image_bytes = await image.read()
        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=400, detail="Image exceeds 10 MB limit.")

        # 4. Daily quota check
        db = get_service_supabase()
        today = date.today().isoformat()
        quota_result = (
            db.table("tenant_quote_usage")
            .select("quote_count")
            .eq("client_id", client_id)
            .eq("period_start", today)
            .limit(1)
            .execute()
        )
        current_count = quota_result.data[0]["quote_count"] if quota_result.data else 0
        if current_count >= DAILY_QUOTA:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Daily photo quote limit reached.",
                    "needs_human": True,
                },
            )

        # 5. Upload full image to storage
        try:
            image_url = _upload_to_storage(client_id, image_bytes, content_type)
        except Exception as exc:
            logger.warning(
                "photo_quote: storage upload failed client_id=%s",
                client_id,
                exc_info=exc,
            )
            image_url = None

        # 6. Generate thumbnail
        thumbnail_url = _make_thumbnail(image_bytes, content_type, client_id)
        if thumbnail_url is None:
            thumbnail_url = image_url or ""

        # 7. Fetch pricing rules
        pricing_rules = _get_pricing_rules(client_id)
        industry = pricing_rules.get("industry", "general")
        disclaimer = pricing_rules.get("disclaimer_text") or DEFAULT_DISCLAIMER
        min_threshold = pricing_rules.get("min_confidence_threshold")
        if min_threshold is None:
            min_threshold = CONFIDENCE_DEFAULTS.get(industry, 0.7)

        # 8. Call Claude vision
        try:
            claude_result = await _call_claude_vision(
                image_bytes, content_type, pricing_rules, client_id
            )
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning(
                "photo_quote: Claude JSON parse failed client_id=%s",
                client_id,
                exc_info=exc,
            )
            claude_result = {
                "quote_low": 0,
                "quote_high": 0,
                "severity": "needs_human",
                "confidence": 0.0,
                "summary": "Unable to parse estimate. A team member will follow up.",
                "needs_human": True,
            }
        except anthropic.APIError as exc:
            logger.warning(
                "photo_quote: Claude API error client_id=%s", client_id, exc_info=exc
            )
            claude_result = {
                "quote_low": 0,
                "quote_high": 0,
                "severity": "needs_human",
                "confidence": 0.0,
                "summary": "Unable to analyze photo at this time.",
                "needs_human": True,
            }

        # 9. Apply confidence threshold
        confidence = float(claude_result.get("confidence", 0.0))
        needs_human = bool(claude_result.get("needs_human", False))
        if confidence < float(min_threshold):
            needs_human = True

        # dollars → cents for storage
        quote_low_cents = int((claude_result.get("quote_low") or 0) * 100)
        quote_high_cents = int((claude_result.get("quote_high") or 0) * 100)
        severity = claude_result.get("severity") or "needs_human"
        claude_summary = claude_result.get("summary") or ""

        # 10. Persist quote_request
        quote_request_id: str | None = None
        try:
            conv_id = conversation_id if conversation_id else None
            insert_result = (
                db.table("quote_requests")
                .insert(
                    {
                        "client_id": client_id,
                        "conversation_id": conv_id,
                        "image_url": image_url,
                        "thumbnail_url": thumbnail_url,
                        "quote_low": quote_low_cents,
                        "quote_high": quote_high_cents,
                        "severity": severity,
                        "confidence": confidence,
                        "claude_summary": claude_summary,
                        "needs_human": needs_human,
                    }
                )
                .execute()
            )
            if insert_result.data:
                quote_request_id = insert_result.data[0].get("id")
        except Exception as exc:
            logger.warning(
                "photo_quote: DB insert failed client_id=%s", client_id, exc_info=exc
            )

        # 11. Increment usage
        _check_and_increment_quota(client_id)

        # 12. Build response (dollars for display)
        return {
            "quote_low": claude_result.get("quote_low") or 0,
            "quote_high": claude_result.get("quote_high") or 0,
            "severity": severity,
            "confidence": confidence,
            "summary": claude_summary,
            "needs_human": needs_human,
            "disclaimer": disclaimer,
            "quote_request_id": quote_request_id,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("photo_quote: unhandled error", exc_info=exc)
        # Never 5xx to widget — always 200 with needs_human
        return {"error": "Unable to process image", "needs_human": True}


# ---------------------------------------------------------------------------
# GET /api/quotes — dashboard view of quote requests
# ---------------------------------------------------------------------------


@router.get("/quotes")
async def list_quote_requests(
    page: int = 1,
    limit: int = 20,
    tenant_id: str = None,
    token: str = None,
):
    """Return quote_requests for the tenant (newest first) + current month usage.

    Auth: called with Bearer JWT — tenant_id and token extracted by dependency injection
    in production. For now we accept them as query params for simplicity.
    This endpoint is dashboard-facing, not widget-facing.
    """
    # Import auth dependency inline to avoid circular import

    db = get_service_supabase()

    if not tenant_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    offset = (page - 1) * limit

    try:
        rows = (
            db.table("quote_requests")
            .select("*")
            .eq("client_id", tenant_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
    except Exception as exc:
        logger.warning(
            "list_quote_requests: DB error tenant_id=%s", tenant_id, exc_info=exc
        )
        raise HTTPException(status_code=500, detail="Failed to fetch quotes")

    # Current month usage
    today = date.today()
    period_start = today.replace(day=1).isoformat()
    try:
        usage_result = (
            db.table("tenant_quote_usage")
            .select("quote_count, overage_count")
            .eq("client_id", tenant_id)
            .eq("period_start", period_start)
            .limit(1)
            .execute()
        )
        month_count = usage_result.data[0]["quote_count"] if usage_result.data else 0
    except Exception:
        month_count = 0

    return {
        "quotes": rows.data or [],
        "page": page,
        "limit": limit,
        "month_count": month_count,
        "month_limit": OVERAGE_THRESHOLD,
    }
