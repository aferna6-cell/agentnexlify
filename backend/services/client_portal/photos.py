"""Photo upload helpers for service records.

Validation, Supabase Storage upload, and photos_json append. Keeps the router
thin and lets the upload route handle only HTTP concerns.
"""

import logging
import uuid
from typing import Any

from fastapi import HTTPException, UploadFile

from backend.config import settings
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_PHOTO_SIZE = 10 * 1024 * 1024  # 10 MB

__all__ = [
    "ALLOWED_IMAGE_TYPES",
    "MAX_PHOTO_SIZE",
    "validate_and_read_photo",
    "fetch_record_for_upload",
    "upload_photo_to_storage",
    "append_photo_url",
]


async def validate_and_read_photo(file: UploadFile) -> tuple[bytes, str]:
    """Validate content-type + size, return (data, content_type). Raises HTTP 400 on rejection."""
    content_type = file.content_type or ""
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed: {content_type}. Accepted: JPEG, PNG, WebP.",
        )
    data = await file.read()
    if len(data) > MAX_PHOTO_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")
    return data, content_type


def fetch_record_for_upload(db: Any, tenant_id: str, record_id: str) -> dict:
    """Fetch service record (id, photos_json). Raises 404 if missing, 500 on DB error."""
    try:
        existing = (
            tenant_table(db, "service_records", tenant_id)
            .select("id, photos_json")
            .eq("id", record_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Failed to fetch service record %s for photo upload", record_id)
        raise HTTPException(status_code=500, detail="Failed to fetch service record")
    if not existing.data:
        raise HTTPException(status_code=404, detail="Service record not found")
    return existing.data[0]


def upload_photo_to_storage(
    db: Any, tenant_id: str, record_id: str, filename: str | None, data: bytes, content_type: str
) -> str:
    """Upload to service-photos bucket, return public URL. Raises HTTP 500 on storage error."""
    ext = (filename or "photo.jpg").rsplit(".", 1)[-1][:10]
    unique_name = f"{uuid.uuid4().hex[:12]}.{ext}"
    path = f"{tenant_id}/{record_id}/{unique_name}"
    try:
        db.storage.from_("service-photos").upload(
            path,
            data,
            file_options={"content-type": content_type},
        )
    except Exception:
        logger.exception("Photo upload to storage failed for record %s", record_id)
        raise HTTPException(status_code=500, detail="Photo upload failed")
    return f"{settings.supabase_url}/storage/v1/object/public/service-photos/{path}"


def append_photo_url(
    db: Any, tenant_id: str, record_id: str, current_photos: list, public_url: str
) -> dict:
    """Append URL to photos_json and persist. Returns updated record. Raises HTTP 500 on error."""
    updated_photos = current_photos + [public_url]
    try:
        result = (
            tenant_table(db, "service_records", tenant_id)
            .update({"photos_json": updated_photos})
            .eq("id", record_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
    except Exception:
        logger.exception("Failed to update photos_json for record %s", record_id)
        raise HTTPException(status_code=500, detail="Failed to update service record")
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to update service record")
    return result.data[0]
