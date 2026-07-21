"""Widget photo-quote endpoint (#37).

``POST /api/widget/photo-quote`` — a widget visitor uploads a photo of a job;
Claude vision assesses it against the tenant's pricing rules and returns a price
range (or a ``needs_human`` handoff). The row is persisted to ``quote_requests``
and both the full image + a 256px thumbnail are stored in the ``photo-quotes``
bucket.

The assessment logic (validation, prompt build, response parse, quota) lives in
``backend/services/photo_quote_service.py`` (unit-tested). This router is the I/O
shell: multipart parse, per-conversation rate limit, Pillow thumbnail, Storage
upload, and the DB insert. Persistence + storage are best-effort — the visitor
always gets their quote even if a write hiccups.

No ``from __future__ import annotations`` (CLAUDE.md Rule 5 — it breaks Pydantic
body resolution). ``quote_requests`` is ``client_id``-scoped (migration 108).
"""

import base64
import io
import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.models.database import get_service_supabase
from backend.services import api_key_limiter, photo_quote_service
from backend.services.llm_runtime import call_claude_messages

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/widget", tags=["widget-photo-quote"])

_BUCKET = "photo-quotes"
_UPLOADS_PER_MINUTE = 5
_THUMBNAIL_PX = 256


class PhotoQuoteResponse(BaseModel):
    quote_low: int
    quote_high: int
    severity: str
    confidence: float
    summary: str
    needs_human: bool
    quote_request_id: str | None = None
    thumbnail_url: str | None = None


def _load_pricing(db, client_id: str):
    """Return (rules_row, industry) for the tenant, or (None, 'service').

    Uses the tenant's first configured ``tenant_pricing_rules`` row. A tenant
    with no pricing rule still gets an assessment — it just resolves to the safe
    default confidence floor and typically routes to ``needs_human``.
    """
    try:
        res = (
            db.table("tenant_pricing_rules")
            .select("industry, rules_jsonb, disclaimer_text, min_confidence_threshold")
            .eq("client_id", client_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
    except Exception:
        logger.warning("widget_photo_quote: pricing lookup failed for %s", client_id)
        rows = []
    if rows:
        return rows[0], rows[0].get("industry") or "service"
    return None, "service"


def _make_thumbnail(image_bytes: bytes) -> bytes | None:
    """Downscale to a <=256px JPEG thumbnail. Returns None on any failure."""
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGB")
        img.thumbnail((_THUMBNAIL_PX, _THUMBNAIL_PX))
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=80)
        return out.getvalue()
    except Exception:
        logger.warning("widget_photo_quote: thumbnail generation failed")
        return None


def _upload(db, path: str, data: bytes, content_type: str) -> str | None:
    """Best-effort Storage upload; returns the storage path on success."""
    try:
        db.storage.from_(_BUCKET).upload(
            path, data, file_options={"content-type": content_type}
        )
        return path
    except Exception:
        logger.warning("widget_photo_quote: storage upload failed for %s", path)
        return None


@router.post("/photo-quote", response_model=PhotoQuoteResponse)
async def create_photo_quote(
    image: UploadFile = File(...),
    client_id: str = Form(...),
    conversation_id: str = Form(None),
):
    # Per-conversation rate limit: 5 uploads/min (falls back to client_id key).
    rl_key = f"photoquote:{conversation_id or client_id}"
    allowed, _count = api_key_limiter.check_and_increment(rl_key, _UPLOADS_PER_MINUTE)
    if not allowed:
        raise HTTPException(status_code=429, detail="Too many photo uploads — slow down.")

    image_bytes = await image.read()
    err = photo_quote_service.validate_image(image.content_type, len(image_bytes))
    if err == "unsupported_media_type":
        raise HTTPException(status_code=415, detail="Only JPEG and PNG images are accepted.")
    if err in ("empty_image", "image_too_large"):
        raise HTTPException(status_code=413, detail="Image is empty or larger than 10 MB.")

    db = get_service_supabase()

    # Hard daily per-tenant quota (cost guard).
    if photo_quote_service.is_over_daily_quota(db, client_id):
        raise HTTPException(status_code=429, detail="Daily photo-quote limit reached.")

    rules_row, industry = _load_pricing(db, client_id)

    image_b64 = base64.b64encode(image_bytes).decode()
    try:
        quote = await photo_quote_service.assess_photo(
            image_b64,
            image.content_type,
            rules_row,
            industry,
            llm_call=call_claude_messages,
        )
    except Exception:
        logger.exception("widget_photo_quote: assessment failed for %s", client_id)
        raise HTTPException(status_code=502, detail="Could not assess the photo right now.")

    # Best-effort persistence: store images + row. A failure here never blocks
    # the visitor's quote.
    from uuid import uuid4

    base_name = uuid4().hex
    full_path = _upload(db, f"{client_id}/{base_name}.bin", image_bytes, image.content_type or "image/jpeg")
    thumb_bytes = _make_thumbnail(image_bytes)
    thumb_path = (
        _upload(db, f"{client_id}/{base_name}_thumb.jpg", thumb_bytes, "image/jpeg")
        if thumb_bytes
        else None
    )

    quote_request_id = None
    if thumb_path:  # thumbnail_url is NOT NULL — only persist when we have one
        row = {
            "client_id": client_id,
            "conversation_id": conversation_id,
            "image_url": full_path,
            "thumbnail_url": thumb_path,
            "quote_low": quote["quote_low"],
            "quote_high": quote["quote_high"],
            "severity": quote["severity"],
            "confidence": quote["confidence"],
            "claude_summary": quote["summary"],
            "needs_human": quote["needs_human"],
        }
        try:
            created = db.table("quote_requests").insert(row).execute()
            if created.data:
                quote_request_id = created.data[0].get("id")
        except Exception:
            logger.warning("widget_photo_quote: quote_requests insert failed for %s", client_id)

    return PhotoQuoteResponse(
        quote_low=quote["quote_low"],
        quote_high=quote["quote_high"],
        severity=quote["severity"],
        confidence=quote["confidence"],
        summary=quote["summary"],
        needs_human=quote["needs_human"],
        quote_request_id=quote_request_id,
        thumbnail_url=thumb_path,
    )
