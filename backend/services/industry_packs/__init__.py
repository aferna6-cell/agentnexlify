"""Industry packs registry.

Maps business_type strings (same keys as
`backend/services/business_profiles.py`) to turnkey IndustryPack bundles.

Usage:
    from backend.services.industry_packs import load_pack
    pack = load_pack("dental")
    summary = pack.summary()   # {"form_presets": 1, "sequence_templates": 4, ...}

The loader falls back to the `default` pack when an unknown business_type
is passed, so the API surface stays forgiving.
"""

from backend.services.industry_packs.base import (
    AutomationRuleTemplate,
    FormPreset,
    IndustryAIPersona,
    IndustryPack,
    KBSeedArticle,
    SeedResult,
    SequenceStep,
    SequenceTemplate,
    SmartListTemplate,
)
from backend.services.industry_packs.dental import DENTAL_PACK
from backend.services.industry_packs.default import DEFAULT_PACK
from backend.services.industry_packs.medical import MEDICAL_PACK
from backend.services.industry_packs.hvac import HVAC_PACK
from backend.services.industry_packs.home_services import HOME_SERVICES_PACK
from backend.services.industry_packs.salon import SALON_PACK
from backend.services.industry_packs.restaurant import RESTAURANT_PACK
from backend.services.industry_packs.legal import LEGAL_PACK
from backend.services.industry_packs.auto_shop import AUTO_SHOP_PACK
from backend.services.industry_packs.fitness import FITNESS_PACK
from backend.services.industry_packs.professional_services import (
    PROFESSIONAL_SERVICES_PACK,
)
from backend.services.industry_packs.retail import RETAIL_PACK
from backend.services.industry_packs.real_estate import REAL_ESTATE_PACK

_REGISTRY: dict[str, IndustryPack] = {
    "dental": DENTAL_PACK,
    "medical": MEDICAL_PACK,
    "hvac": HVAC_PACK,
    "home_services": HOME_SERVICES_PACK,
    "salon": SALON_PACK,
    "restaurant": RESTAURANT_PACK,
    "legal": LEGAL_PACK,
    "auto_shop": AUTO_SHOP_PACK,
    "fitness": FITNESS_PACK,
    "professional_services": PROFESSIONAL_SERVICES_PACK,
    "retail": RETAIL_PACK,
    "real_estate": REAL_ESTATE_PACK,
    "default": DEFAULT_PACK,
}


def load_pack(business_type: str | None) -> IndustryPack:
    """Return the pack matching `business_type`, falling back to DEFAULT_PACK.

    Uses the same alias resolution as `business_profiles.resolve_business_profile_key`
    so that e.g. "plumbing" → "home_services" → HOME_SERVICES_PACK.
    """
    from backend.services.business_profiles import resolve_business_profile_key

    key = resolve_business_profile_key(business_type)
    return _REGISTRY.get(key, DEFAULT_PACK)


def list_available_packs() -> list[dict[str, object]]:
    """Return a list of `{key, label, version, counts}` for the dashboard."""
    return [
        {
            "key": pack.key,
            "label": pack.label,
            "version": pack.version,
            "counts": pack.summary(),
        }
        for pack in _REGISTRY.values()
    ]


__all__ = [
    "AutomationRuleTemplate",
    "FormPreset",
    "IndustryAIPersona",
    "IndustryPack",
    "KBSeedArticle",
    "SeedResult",
    "SequenceStep",
    "SequenceTemplate",
    "SmartListTemplate",
    "load_pack",
    "list_available_packs",
]
