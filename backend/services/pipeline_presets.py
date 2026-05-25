"""Pipeline stage presets and seeding logic.

Extracted from backend/routers/pipeline.py to keep the router under the
600-line god-class threshold (user-rules.md Rule 9).
"""

import logging

logger = logging.getLogger(__name__)


DEFAULT_STAGES = [
    {"name": "New Lead", "sort_order": 0, "color": "#3b82f6", "is_won": False, "is_lost": False},
    {"name": "Contacted", "sort_order": 1, "color": "#8b5cf6", "is_won": False, "is_lost": False},
    {"name": "Qualified", "sort_order": 2, "color": "#f59e0b", "is_won": False, "is_lost": False},
    {"name": "Proposal Sent", "sort_order": 3, "color": "#ec4899", "is_won": False, "is_lost": False},
    {"name": "Won", "sort_order": 4, "color": "#10b981", "is_won": True, "is_lost": False},
    {"name": "Lost", "sort_order": 5, "color": "#ef4444", "is_won": False, "is_lost": True},
]

_INDUSTRY_STAGES: dict[str, list[dict]] = {
    "realestate": [
        {"name": "New Lead", "sort_order": 0, "color": "#3b82f6", "is_won": False, "is_lost": False},
        {"name": "Contacted", "sort_order": 1, "color": "#8b5cf6", "is_won": False, "is_lost": False},
        {"name": "Showing Scheduled", "sort_order": 2, "color": "#f59e0b", "is_won": False, "is_lost": False},
        {"name": "Offer Submitted", "sort_order": 3, "color": "#ec4899", "is_won": False, "is_lost": False},
        {"name": "Under Contract", "sort_order": 4, "color": "#14b8a6", "is_won": False, "is_lost": False},
        {"name": "Closed", "sort_order": 5, "color": "#10b981", "is_won": True, "is_lost": False},
        {"name": "Lost", "sort_order": 6, "color": "#ef4444", "is_won": False, "is_lost": True},
    ],
    "contractor": [
        {"name": "New Lead", "sort_order": 0, "color": "#3b82f6", "is_won": False, "is_lost": False},
        {"name": "Estimate Sent", "sort_order": 1, "color": "#8b5cf6", "is_won": False, "is_lost": False},
        {"name": "Approved", "sort_order": 2, "color": "#f59e0b", "is_won": False, "is_lost": False},
        {"name": "In Progress", "sort_order": 3, "color": "#14b8a6", "is_won": False, "is_lost": False},
        {"name": "Completed", "sort_order": 4, "color": "#10b981", "is_won": True, "is_lost": False},
        {"name": "Lost", "sort_order": 5, "color": "#ef4444", "is_won": False, "is_lost": True},
    ],
    "dental": [
        {"name": "New Patient", "sort_order": 0, "color": "#3b82f6", "is_won": False, "is_lost": False},
        {"name": "Consulted", "sort_order": 1, "color": "#8b5cf6", "is_won": False, "is_lost": False},
        {"name": "Treatment Planned", "sort_order": 2, "color": "#f59e0b", "is_won": False, "is_lost": False},
        {"name": "In Treatment", "sort_order": 3, "color": "#14b8a6", "is_won": False, "is_lost": False},
        {"name": "Completed", "sort_order": 4, "color": "#10b981", "is_won": True, "is_lost": False},
        {"name": "Inactive", "sort_order": 5, "color": "#ef4444", "is_won": False, "is_lost": True},
    ],
    "legal": [
        {"name": "Inquiry", "sort_order": 0, "color": "#3b82f6", "is_won": False, "is_lost": False},
        {"name": "Consultation", "sort_order": 1, "color": "#8b5cf6", "is_won": False, "is_lost": False},
        {"name": "Retained", "sort_order": 2, "color": "#f59e0b", "is_won": False, "is_lost": False},
        {"name": "Active Case", "sort_order": 3, "color": "#14b8a6", "is_won": False, "is_lost": False},
        {"name": "Resolved", "sort_order": 4, "color": "#10b981", "is_won": True, "is_lost": False},
        {"name": "Declined", "sort_order": 5, "color": "#ef4444", "is_won": False, "is_lost": True},
    ],
    "restaurant": [
        {"name": "Inquiry", "sort_order": 0, "color": "#3b82f6", "is_won": False, "is_lost": False},
        {"name": "Reservation", "sort_order": 1, "color": "#8b5cf6", "is_won": False, "is_lost": False},
        {"name": "Catering Quoted", "sort_order": 2, "color": "#f59e0b", "is_won": False, "is_lost": False},
        {"name": "Booked", "sort_order": 3, "color": "#10b981", "is_won": True, "is_lost": False},
        {"name": "Cancelled", "sort_order": 4, "color": "#ef4444", "is_won": False, "is_lost": True},
    ],
    "salon": [
        {"name": "New Client", "sort_order": 0, "color": "#3b82f6", "is_won": False, "is_lost": False},
        {"name": "Consulted", "sort_order": 1, "color": "#8b5cf6", "is_won": False, "is_lost": False},
        {"name": "Booked", "sort_order": 2, "color": "#f59e0b", "is_won": False, "is_lost": False},
        {"name": "Regular Client", "sort_order": 3, "color": "#10b981", "is_won": True, "is_lost": False},
        {"name": "Inactive", "sort_order": 4, "color": "#ef4444", "is_won": False, "is_lost": True},
    ],
    "fitness": [
        {"name": "Trial", "sort_order": 0, "color": "#3b82f6", "is_won": False, "is_lost": False},
        {"name": "Consulted", "sort_order": 1, "color": "#8b5cf6", "is_won": False, "is_lost": False},
        {"name": "Member", "sort_order": 2, "color": "#10b981", "is_won": True, "is_lost": False},
        {"name": "At Risk", "sort_order": 3, "color": "#f59e0b", "is_won": False, "is_lost": False},
        {"name": "Churned", "sort_order": 4, "color": "#ef4444", "is_won": False, "is_lost": True},
    ],
}

_TYPE_ALIASES: dict[str, str] = {
    "real_estate": "realestate",
    "home_services": "contractor",
    "construction": "contractor",
    "hvac": "contractor",
    "plumbing": "contractor",
    "electrical": "contractor",
    "roofing": "contractor",
    "pest_control": "contractor",
    "painting": "contractor",
    "flooring": "contractor",
    "general_contractor": "contractor",
    "beauty": "salon",
    "medical": "dental",
    "health_wellness": "dental",
    "cleaning": "contractor",
    "landscaping": "contractor",
}


def resolve_stages_for_business_type(business_type: str | None) -> list[dict]:
    """Pick the best stage preset for a business_type, falling back to DEFAULT_STAGES."""
    btype = (business_type or "").lower()
    resolved = _TYPE_ALIASES.get(btype, btype)
    return _INDUSTRY_STAGES.get(resolved, DEFAULT_STAGES)


def seed_default_stages(tenant_id: str, db) -> list[dict]:
    """Insert default pipeline stages for a tenant, using industry-specific presets when available."""
    stages = DEFAULT_STAGES
    try:
        tenant = db.table("tenants").select("business_type").eq("id", tenant_id).limit(1).execute()
        if tenant.data:
            stages = resolve_stages_for_business_type(tenant.data[0].get("business_type"))
    except Exception:
        logger.warning("Failed to look up business_type for pipeline preset, using defaults", exc_info=True)

    rows = [{"tenant_id": tenant_id, **s} for s in stages]
    try:
        result = db.table("pipeline_stages").insert(rows).execute()
        return result.data or []
    except Exception:
        logger.exception("Failed to seed default pipeline stages for tenant %s", tenant_id)
        return []
