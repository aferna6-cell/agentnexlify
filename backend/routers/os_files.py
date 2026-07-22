"""Agent OS file upload + image generation endpoints.

POST /api/v1/os/uploads        — authenticated tenant file upload
POST /api/v1/os/images/generate — authenticated image generation

Rate limits:
  Uploads:    20/hour (slowapi) + 50/day per-tenant DB cap
  Generation: 10/hour (slowapi) + 20/day per-tenant DB cap (kind='generated')

client_id is always taken from JWT — never from path or body.
"""

import base64
import logging
from datetime import date, datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant
from backend.services.agent_os_gate import require_agent_os_access
from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.services.image_gen import (
    ImageGenError,
    ImageGenNotConfigured,
    generate_image_png,
    is_configured,
)
from backend.services.llm_runtime import call_claude_messages
from backend.services.tenant_scope import tenant_table
from backend.config import settings

logger = logging.getLogger(__name__)

# Stage-3 plan gate (2026-07-22, audit H1): suite surface - agent_os
# plan (+ legacy) only; 402 upsell otherwise.
router = APIRouter(
    prefix="/api/v1/os",
    tags=["agent-os-files"],
    dependencies=[Depends(require_agent_os_access)],
)

# ── constants ─────────────────────────────────────────────────────────────────

_ALLOWED_CONTENT_TYPES = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/webp",
        "image/gif",
        "application/pdf",
    }
)
_IMAGE_CONTENT_TYPES = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/webp",
        "image/gif",
    }
)
_CONTENT_TYPE_EXTENSIONS = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
    "application/pdf": "pdf",
}

_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
_UPLOAD_BUCKET = "os-uploads"
_DAILY_UPLOAD_CAP = 50
_DAILY_GEN_CAP = 20

_VISION_MODEL = "claude-haiku-4-5-20251001"
_VISION_PROMPT = (
    "Describe this image for a business assistant: "
    "key text, objects, amounts, names. ≤120 words."
)
_VISION_MAX_TOKENS = 300


# ── helpers ───────────────────────────────────────────────────────────────────


def _today_utc() -> str:
    return date.today().isoformat()


def _count_today_uploads(db, client_id: str) -> int:
    """Count all os_uploads rows created today (UTC) for the tenant."""
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).isoformat()
    result = (
        tenant_table(db, "os_uploads", client_id)
        .select("id")
        .gte("created_at", today_start)
        .execute()
    )
    return len(result.data or [])


def _count_today_generated(db, client_id: str) -> int:
    """Count os_uploads rows with kind='generated' created today (UTC)."""
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).isoformat()
    result = (
        tenant_table(db, "os_uploads", client_id)
        .select("id")
        .eq("kind", "generated")
        .gte("created_at", today_start)
        .execute()
    )
    return len(result.data or [])


def _build_public_url(path: str) -> str:
    return f"{settings.supabase_url}/storage/v1/object/public/{_UPLOAD_BUCKET}/{path}"


async def _vision_describe(image_data: bytes, content_type: str) -> str | None:
    """Run vision description on an image. Returns None on any failure."""
    try:
        b64 = base64.standard_b64encode(image_data).decode("ascii")
        result = await call_claude_messages(
            operation="os_file_vision",
            model=_VISION_MODEL,
            max_tokens=_VISION_MAX_TOKENS,
            messages=[
                {
                    "role": "user",
                    "content": [  # type: ignore[list-item]
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": content_type,
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": _VISION_PROMPT},
                    ],
                }
            ],
        )
        return result.text or None
    except Exception:
        logger.warning("os_files.vision_describe.failed", exc_info=True)
        return None


# ── Pydantic models ───────────────────────────────────────────────────────────


class UploadResponse(BaseModel):
    id: str
    public_url: str
    filename: str
    content_type: str
    vision_summary: str | None = None


class ImageGenRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=1000)


class ImageGenResponse(BaseModel):
    id: str
    public_url: str


# ── upload endpoint ───────────────────────────────────────────────────────────


@router.post("/uploads", response_model=UploadResponse, status_code=201)
@limiter.limit("20/hour")
async def upload_file(
    request: Request,
    file: UploadFile,
    claims: dict = Depends(_get_current_tenant),
):
    """Upload a file to Agent OS storage.

    - Max 10 MB
    - Allowed types: image/png, image/jpeg, image/webp, image/gif, application/pdf
    - Images get a vision summary via Haiku (failure does not fail the upload)
    - Rate limited: 20/hour (slowapi IP) + 50/day per tenant
    """
    client_id = claims["tenant_id"]
    db = get_service_supabase()

    # ── per-tenant daily cap ──────────────────────────────────────────────────
    daily_count = _count_today_uploads(db, client_id)
    if daily_count >= _DAILY_UPLOAD_CAP:
        raise HTTPException(
            status_code=429,
            detail=f"Daily upload limit of {_DAILY_UPLOAD_CAP} files reached. Try again tomorrow.",
        )

    # ── content type ──────────────────────────────────────────────────────────
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {content_type!r}. "
            f"Allowed: {sorted(_ALLOWED_CONTENT_TYPES)}",
        )

    # ── read + size check ─────────────────────────────────────────────────────
    data = await file.read()
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # ── storage path ──────────────────────────────────────────────────────────
    ext = _CONTENT_TYPE_EXTENSIONS[content_type]
    unique_name = f"{uuid4().hex}.{ext}"
    storage_path = f"{client_id}/{unique_name}"

    # ── Supabase Storage upload ───────────────────────────────────────────────
    try:
        get_service_supabase().storage.from_(_UPLOAD_BUCKET).upload(
            storage_path,
            data,
            file_options={"content-type": content_type},
        )
    except Exception:
        logger.exception(
            "os_files.upload.storage_error tenant=%s path=%s", client_id, storage_path
        )
        raise HTTPException(
            status_code=502,
            detail="Storage upload failed. Please retry. If the problem persists, contact support.",
        )

    public_url = _build_public_url(storage_path)

    # ── vision summary for images ─────────────────────────────────────────────
    vision_summary: str | None = None
    if content_type in _IMAGE_CONTENT_TYPES:
        vision_summary = await _vision_describe(data, content_type)

    # ── persist metadata ──────────────────────────────────────────────────────
    try:
        row = tenant_table(db, "os_uploads", client_id).insert(
            {
                "filename": file.filename or unique_name,
                "content_type": content_type,
                "size_bytes": len(data),
                "storage_path": storage_path,
                "public_url": public_url,
                "vision_summary": vision_summary,
                "kind": "upload",
            }
        ).execute()
        record_id = row.data[0]["id"]
    except Exception:
        logger.exception("os_files.upload.db_insert_error tenant=%s", client_id)
        # Storage succeeded; return 502 so caller knows something went wrong
        raise HTTPException(
            status_code=502,
            detail="File stored but metadata save failed. Contact support.",
        )

    logger.info(
        "os_files.upload.success tenant=%s id=%s bytes=%d content_type=%s",
        client_id,
        record_id,
        len(data),
        content_type,
    )
    return UploadResponse(
        id=record_id,
        public_url=public_url,
        filename=file.filename or unique_name,
        content_type=content_type,
        vision_summary=vision_summary,
    )


# ── image generation endpoint ─────────────────────────────────────────────────


@router.post("/images/generate", response_model=ImageGenResponse, status_code=201)
@limiter.limit("10/hour")
async def generate_image(
    request: Request,
    req: ImageGenRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Generate an image via the configured AI provider and store in Agent OS.

    - Returns 503 when IMAGE_GEN_PROVIDER / IMAGE_GEN_API_KEY not set
    - Rate limited: 10/hour (slowapi IP) + 20/day per tenant
    - Prompt is never logged; only prompt length is logged
    """
    client_id = claims["tenant_id"]

    # ── provider gate ─────────────────────────────────────────────────────────
    if not is_configured():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "image_generation_not_configured",
                "message": (
                    "Image generation is not enabled for this deployment. "
                    "Contact your administrator to configure IMAGE_GEN_PROVIDER and IMAGE_GEN_API_KEY."
                ),
            },
        )

    db = get_service_supabase()

    # ── per-tenant daily generation cap ───────────────────────────────────────
    daily_gen = _count_today_generated(db, client_id)
    if daily_gen >= _DAILY_GEN_CAP:
        raise HTTPException(
            status_code=429,
            detail=f"Daily image generation limit of {_DAILY_GEN_CAP} reached. Try again tomorrow.",
        )

    # ── generate ──────────────────────────────────────────────────────────────
    logger.info(
        "os_files.image_gen.start tenant=%s prompt_len=%d", client_id, len(req.prompt)
    )
    try:
        png_bytes = generate_image_png(req.prompt)
    except ImageGenNotConfigured:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "image_generation_not_configured",
                "message": "Image generation provider is not configured.",
            },
        )
    except ImageGenError as exc:
        logger.warning("os_files.image_gen.provider_error tenant=%s error=%s", client_id, exc)
        raise HTTPException(status_code=502, detail="Image generation failed. Please retry.")

    # ── store in bucket ───────────────────────────────────────────────────────
    unique_name = f"gen_{uuid4().hex}.png"
    storage_path = f"{client_id}/{unique_name}"

    try:
        get_service_supabase().storage.from_(_UPLOAD_BUCKET).upload(
            storage_path,
            png_bytes,
            file_options={"content-type": "image/png"},
        )
    except Exception:
        logger.exception(
            "os_files.image_gen.storage_error tenant=%s path=%s", client_id, storage_path
        )
        raise HTTPException(status_code=502, detail="Storage upload failed after generation.")

    public_url = _build_public_url(storage_path)

    # ── persist metadata ──────────────────────────────────────────────────────
    try:
        row = tenant_table(db, "os_uploads", client_id).insert(
            {
                "filename": unique_name,
                "content_type": "image/png",
                "size_bytes": len(png_bytes),
                "storage_path": storage_path,
                "public_url": public_url,
                "vision_summary": req.prompt,
                "kind": "generated",
            }
        ).execute()
        record_id = row.data[0]["id"]
    except Exception:
        logger.exception("os_files.image_gen.db_insert_error tenant=%s", client_id)
        raise HTTPException(
            status_code=502,
            detail="Image stored but metadata save failed. Contact support.",
        )

    logger.info(
        "os_files.image_gen.success tenant=%s id=%s bytes=%d",
        client_id,
        record_id,
        len(png_bytes),
    )
    return ImageGenResponse(id=record_id, public_url=public_url)
