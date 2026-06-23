"""Read-only vertical preset endpoints for the onboarding wizard.

GET /api/v1/onboarding/presets
    Returns a list of available verticals with a brief summary of each
    (greeting preview, service count, FAQ count).  No auth required.

GET /api/v1/onboarding/presets/{vertical}
    Returns the full preset for a single vertical.  Falls back to the
    generic preset for unknown verticals.  No auth required.

Auth convention: these endpoints follow the same pattern as the existing
``GET /api/v1/onboarding/industry-packs`` endpoint in onboarding.py --
read-only, no tenant scope, no authentication needed beyond what the
client already holds.  Widget and wizard callers can hit these without
a tenant JWT.
"""

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.vertical_preset_loader import list_verticals, load_vertical_preset

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class VerticalSummary(BaseModel):
    vertical: str
    greeting_preview: str
    service_count: int
    faq_count: int


class VerticalListResponse(BaseModel):
    verticals: list[VerticalSummary]


class FaqEntry(BaseModel):
    question: str
    answer: str


class VerticalPresetResponse(BaseModel):
    vertical: str
    greeting: str
    services: list[str]
    business_hours: str
    faqs: list[FaqEntry]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

# NOTE: static path (/presets) is declared before the dynamic path
# (/presets/{vertical}) so FastAPI matches it correctly.


@router.get("/presets", response_model=VerticalListResponse)
def list_preset_verticals() -> VerticalListResponse:
    """Return all available verticals with brief summaries.

    The ``generic`` fallback is excluded from this list -- it is implicit.
    """
    verticals = list_verticals()
    summaries: list[VerticalSummary] = []
    for key in verticals:
        try:
            preset = load_vertical_preset(key)
            greeting = preset.get("greeting", "")
            preview = greeting.strip()[:120]
            if len(greeting.strip()) > 120:
                preview += "..."
            summaries.append(
                VerticalSummary(
                    vertical=key,
                    greeting_preview=preview,
                    service_count=len(preset.get("services", [])),
                    faq_count=len(preset.get("faqs", [])),
                )
            )
        except Exception:
            logger.warning("Failed to load preset summary for vertical %r", key, exc_info=True)

    return VerticalListResponse(verticals=summaries)


@router.get("/presets/{vertical}", response_model=VerticalPresetResponse)
def get_preset(vertical: str) -> VerticalPresetResponse:
    """Return the full preset for a vertical.

    Unknown verticals silently fall back to the ``generic`` preset rather
    than returning a 404, because the caller can always apply whatever is
    returned and the generic preset is always better than nothing.
    """
    try:
        preset = load_vertical_preset(vertical)
        faqs = [
            FaqEntry(
                question=f.get("question", ""),
                answer=f.get("answer", ""),
            )
            for f in preset.get("faqs", [])
        ]
        return VerticalPresetResponse(
            vertical=vertical,
            greeting=preset.get("greeting", "").strip(),
            services=preset.get("services", []),
            business_hours=preset.get("business_hours", "").strip(),
            faqs=faqs,
        )
    except Exception:
        logger.exception("Unexpected error loading preset for vertical %r", vertical)
        # Return an empty-but-valid generic shell rather than a 500.
        return VerticalPresetResponse(
            vertical=vertical,
            greeting="",
            services=[],
            business_hours="",
            faqs=[],
        )
