"""Per-platform image generation + storage upload for social posts.

Wraps ``backend.services.image_gen`` (the OpenAI gpt-image-1 provider
abstraction) with a per-platform size preset and a Supabase Storage upload,
mirroring the pattern already shipped in ``backend/routers/os_files.py``
(bucket ``os-uploads``, ``{tenant_id}/{uuid}.png`` path, public URL built
from ``settings.supabase_url``). Social post images are Agent OS assets
like any other generated file, so they share that bucket rather than
introducing a new one.

gpt-image-1 only accepts a fixed set of output sizes (square / portrait /
landscape). ``PLATFORM_IMAGE_SIZES`` maps each platform to the actual
OpenAI size closest to that platform's real marketing-image aspect ratio
(IG feed ~1080x1080 square, IG portrait ~1080x1350, FB link image
~1200x630 landscape) — the returned ``width``/``height`` are the true
pixel dimensions of the PNG that gets uploaded, not the nominal marketing
target, so callers never get a dimension mismatch against the stored file.
"""

import logging
from uuid import uuid4

from backend.config import settings
from backend.services.image_gen import (
    ImageGenError,
    ImageGenNotConfigured,
    generate_image_png,
)

logger = logging.getLogger(__name__)

# Same bucket os_files.py uses for Agent OS uploads/generated images.
_BUCKET = "os-uploads"

# platform -> {size: <gpt-image-1 size enum>, width, height}. width/height
# are the real output pixels for that size string, not the nominal target.
PLATFORM_IMAGE_SIZES: dict[str, dict[str, object]] = {
    # feed post, square (target 1080x1080)
    "instagram": {"size": "1024x1024", "width": 1024, "height": 1024},
    # story/portrait post (target 1080x1350)
    "instagram_portrait": {"size": "1024x1536", "width": 1024, "height": 1536},
    # link-preview image, landscape (target 1200x630)
    "facebook": {"size": "1536x1024", "width": 1536, "height": 1024},
    # article/share image, landscape
    "linkedin": {"size": "1536x1024", "width": 1536, "height": 1024},
    "google_business": {"size": "1024x1024", "width": 1024, "height": 1024},
}
_DEFAULT_SIZE: dict[str, object] = {"size": "1024x1024", "width": 1024, "height": 1024}


class SocialImageGenError(Exception):
    """A clean, user-facing image-generation failure.

    Callers turn this into a 422 — never a 500. Covers: provider not
    configured, provider-side failure, and storage upload failure.
    """


def _build_public_url(path: str) -> str:
    return f"{settings.supabase_url}/storage/v1/object/public/{_BUCKET}/{path}"


async def generate_post_image(db, *, tenant_id: str, prompt: str, platform: str) -> dict:
    """Generate a platform-sized image and upload it to Supabase Storage.

    Returns ``{"url": str, "width": int, "height": int}``. Raises
    ``SocialImageGenError`` with a user-facing message on any failure —
    the caller (router) should map that to a 422, never a 500.
    """
    preset = PLATFORM_IMAGE_SIZES.get(platform, _DEFAULT_SIZE)

    try:
        png_bytes = generate_image_png(prompt, size=preset["size"])
    except ImageGenNotConfigured as exc:
        raise SocialImageGenError(
            "Image generation is not configured for this deployment. "
            "Contact your administrator to enable it."
        ) from exc
    except ImageGenError as exc:
        logger.warning(
            "social_media_images.generate.provider_error tenant=%s platform=%s error=%s",
            tenant_id,
            platform,
            exc,
        )
        raise SocialImageGenError("Image generation failed. Please retry.") from exc

    storage_path = f"{tenant_id}/social_{uuid4().hex}.png"
    try:
        db.storage.from_(_BUCKET).upload(
            storage_path,
            png_bytes,
            file_options={"content-type": "image/png"},
        )
    except Exception as exc:
        logger.exception(
            "social_media_images.upload.storage_error tenant=%s path=%s",
            tenant_id,
            storage_path,
        )
        raise SocialImageGenError(
            "Image generated but storage upload failed. Please retry."
        ) from exc

    logger.info(
        "social_media_images.generate.success tenant=%s platform=%s bytes=%d",
        tenant_id,
        platform,
        len(png_bytes),
    )
    return {
        "url": _build_public_url(storage_path),
        "width": preset["width"],
        "height": preset["height"],
    }
