"""Form & Survey Builder — aggregator router.

Splits originally lived in this file as a 720-line god class. Refactored
2026-05-24 (Rule 9: factor god classes >600 lines, Rule 12: new files over bloat).

Layout:
  - forms_models.py — Pydantic models
  - forms_public.py — public unauthenticated endpoints (rate-limited)
  - forms_admin.py — authenticated dashboard CRUD

Route ordering: public router is included FIRST so the literal `/public/{token}`
prefix is matched before the dynamic `/{tenant_id}/{form_id}` patterns in the
admin router. Static admin paths (`/stats`, `/presets`) are handled inside
forms_admin.py by registering them before the dynamic `/{form_id}` routes.

Models are re-exported here for backward compatibility with existing test
patches that reference `backend.routers.forms.FormCreate` etc.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI — do not
add a future-annotations import here.
"""

from fastapi import APIRouter

from backend.models.database import get_service_supabase
from backend.routers.forms_admin import router as _admin_router
from backend.routers.forms_models import (
    FormCreate,
    FormFieldModel,
    FormSettingsModel,
    FormUpdate,
    PublicFormSubmission,
)
from backend.routers.forms_public import router as _public_router
from backend.services.form_defaults import _FORM_PRESETS

__all__ = [
    "router",
    "FormCreate",
    "FormFieldModel",
    "FormSettingsModel",
    "FormUpdate",
    "PublicFormSubmission",
    "_FORM_PRESETS",
    "get_service_supabase",
]

router = APIRouter(prefix="/api/v1/forms", tags=["forms"])
router.include_router(_public_router)
router.include_router(_admin_router)
