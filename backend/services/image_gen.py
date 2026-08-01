"""Image generation provider abstraction for Agent OS.

Reads IMAGE_GEN_PROVIDER and IMAGE_GEN_API_KEY from settings.
Supported providers: "openai" (gpt-image-1).
Returns b64-encoded PNG bytes on success.
"""

import base64
import logging

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

_OPENAI_IMAGES_URL = "https://api.openai.com/v1/images/generations"
_TIMEOUT_SECONDS = 60.0


class ImageGenNotConfigured(Exception):
    """Raised when no provider is configured."""


class ImageGenError(Exception):
    """Raised when the provider call fails."""


def _provider() -> str:
    return (getattr(settings, "image_gen_provider", "") or "").strip().lower()


def _api_key() -> str:
    return (getattr(settings, "image_gen_api_key", "") or "").strip()


def is_configured() -> bool:
    """Return True when a usable provider + key is present."""
    return bool(_provider() and _api_key())


def generate_image_png(prompt: str, size: str | None = None) -> bytes:
    """Generate a PNG via the configured provider. Returns raw PNG bytes.

    ``size`` overrides the provider's default output size — like this:
    ``generate_image_png(prompt, size="1024x1536")``. Callers own picking a
    size their provider actually supports; the OpenAI provider passes it
    straight through to the API and lets a bad value surface as
    ``ImageGenError`` rather than silently clamping it.

    Raises ImageGenNotConfigured when provider/key absent.
    Raises ImageGenError on provider-side failures.
    Never logs the API key or full prompt — only prompt length.
    """
    provider = _provider()
    api_key = _api_key()

    if not provider or not api_key:
        raise ImageGenNotConfigured("Image generation not configured.")

    logger.info("image_gen.generate provider=%s prompt_len=%d", provider, len(prompt))

    if provider == "openai":
        return _generate_openai(prompt, api_key, size=size)

    raise ImageGenNotConfigured(f"Unsupported provider: {provider!r}")


def _generate_openai(prompt: str, api_key: str, size: str | None = None) -> bytes:
    payload = {
        "model": "gpt-image-1",
        "prompt": prompt,
        "n": 1,
        "size": size or "1024x1024",
        "response_format": "b64_json",
    }
    try:
        response = httpx.post(
            _OPENAI_IMAGES_URL,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "image_gen.openai.http_error status=%d", exc.response.status_code
        )
        raise ImageGenError(f"OpenAI images API returned {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        logger.warning("image_gen.openai.request_error error_type=%s", type(exc).__name__)
        raise ImageGenError("Network error calling OpenAI images API") from exc

    try:
        body = response.json()
        b64 = body["data"][0]["b64_json"]
        png_bytes = base64.b64decode(b64)
    except Exception as exc:
        logger.warning("image_gen.openai.parse_error error=%s", exc)
        raise ImageGenError("Failed to parse OpenAI images response") from exc

    logger.info("image_gen.generate.done provider=openai bytes=%d", len(png_bytes))
    return png_bytes
