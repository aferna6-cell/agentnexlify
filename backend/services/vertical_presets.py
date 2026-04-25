"""Vertical presets for Onboarding v2 auto-KB.

Used as fallback when website scrape returns empty content. Keyed to
``tenants.business_type``. Matches 6 SMB verticals from spec onboarding-v2 §3.
"""

DEFAULT_HOURS = {
    "Mon": "8am-5pm",
    "Tue": "8am-5pm",
    "Wed": "8am-5pm",
    "Thu": "8am-5pm",
    "Fri": "8am-5pm",
    "Sat": "9am-2pm",
    "Sun": "closed",
}


_PRESETS: dict[str, dict] = {
    "plumbing": {
        "services": [
            "Drain cleaning",
            "Water heater repair",
            "Pipe leak repair",
            "Sewer line service",
            "Toilet repair",
            "Faucet installation",
        ],
        "hours": DEFAULT_HOURS,
        "kb": "# About\nLocal plumbing service.\n## Services\nDrain cleaning, water heater repair, pipe leaks, sewer lines.\n## Hours\nMon-Fri 8am-5pm, Sat 9am-2pm, Sun closed.",
        "ci": "You are the plumbing assistant. Collect name, phone, and issue. NEVER mention AgentNexLiFy.",
        "faqs": [
            {"question": "Do you offer emergency service?", "answer": "Yes, 24/7 for burst pipes and floods.", "category": "emergency"},
            {"question": "Are you licensed and insured?", "answer": "Yes, fully licensed and insured.", "category": "credentials"},
            {"question": "Do you offer free estimates?", "answer": "Yes, free estimates for most jobs.", "category": "pricing"},
        ],
    },
    "hvac": {
        "services": [
            "AC repair",
            "Furnace repair",
            "AC installation",
            "Furnace installation",
            "Duct cleaning",
            "Maintenance plans",
        ],
        "hours": DEFAULT_HOURS,
        "kb": "# About\nLocal HVAC service.\n## Services\nAC and furnace repair, installation, duct cleaning, maintenance.\n## Hours\nMon-Fri 8am-5pm, Sat 9am-2pm, Sun closed.",
        "ci": "You are the HVAC assistant. Collect name, phone, and system issue. NEVER mention AgentNexLiFy.",
        "faqs": [
            {"question": "How fast can you come out?", "answer": "Same-day for emergencies.", "category": "scheduling"},
            {"question": "Do you service all brands?", "answer": "Yes, all major brands.", "category": "scope"},
            {"question": "Do you offer financing?", "answer": "Yes, on installations.", "category": "pricing"},
        ],
    },
    "cleaning": {
        "services": [
            "Recurring house cleaning",
            "Deep cleaning",
            "Move-in/move-out cleaning",
            "Office cleaning",
            "Post-construction cleaning",
            "Carpet cleaning",
        ],
        "hours": {
            "Mon": "8am-6pm", "Tue": "8am-6pm", "Wed": "8am-6pm",
            "Thu": "8am-6pm", "Fri": "8am-6pm", "Sat": "9am-3pm", "Sun": "closed",
        },
        "kb": "# About\nLocal residential and commercial cleaning service.\n## Services\nRecurring, deep, move-in/out, office, post-construction.\n## Hours\nMon-Fri 8am-6pm, Sat 9am-3pm.",
        "ci": "You are the cleaning service assistant. Collect name, phone, address, square footage. NEVER mention AgentNexLiFy.",
        "faqs": [
            {"question": "Do you bring supplies?", "answer": "Yes, all supplies and equipment included.", "category": "scope"},
            {"question": "Are you bonded and insured?", "answer": "Yes, fully bonded and insured.", "category": "credentials"},
            {"question": "How do you set pricing?", "answer": "Based on square footage and frequency.", "category": "pricing"},
        ],
    },
    "power_washing": {
        "services": [
            "House washing",
            "Driveway cleaning",
            "Deck cleaning",
            "Roof cleaning",
            "Concrete cleaning",
            "Commercial power washing",
        ],
        "hours": DEFAULT_HOURS,
        "kb": "# About\nLocal power washing service.\n## Services\nHouse, driveway, deck, roof, concrete, commercial.\n## Hours\nMon-Fri 8am-5pm, Sat 9am-2pm.",
        "ci": "You are the power washing assistant. Collect name, phone, address, surface type. NEVER mention AgentNexLiFy.",
        "faqs": [
            {"question": "How long does it take?", "answer": "Most jobs 1-3 hours.", "category": "scope"},
            {"question": "Are your chemicals safe for plants?", "answer": "Yes, biodegradable and plant-safe.", "category": "safety"},
            {"question": "Do you do free estimates?", "answer": "Yes, free on-site estimates.", "category": "pricing"},
        ],
    },
    "landscaping": {
        "services": [
            "Lawn mowing",
            "Hedge trimming",
            "Mulching",
            "Seasonal cleanup",
            "Tree pruning",
            "Landscape design",
        ],
        "hours": DEFAULT_HOURS,
        "kb": "# About\nLocal landscaping service.\n## Services\nLawn care, hedge trimming, mulching, cleanup, design.\n## Hours\nMon-Fri 8am-5pm, Sat 9am-2pm.",
        "ci": "You are the landscaping assistant. Collect name, phone, address, service type. NEVER mention AgentNexLiFy.",
        "faqs": [
            {"question": "Do you offer recurring service?", "answer": "Yes, weekly or biweekly plans.", "category": "scheduling"},
            {"question": "Do you handle large properties?", "answer": "Yes, residential and commercial.", "category": "scope"},
            {"question": "Are you insured?", "answer": "Yes, fully insured.", "category": "credentials"},
        ],
    },
    "electrical": {
        "services": [
            "Outlet repair",
            "Panel upgrade",
            "Lighting installation",
            "EV charger installation",
            "Wiring repair",
            "Generator installation",
        ],
        "hours": DEFAULT_HOURS,
        "kb": "# About\nLocal electrical service.\n## Services\nOutlets, panels, lighting, EV chargers, wiring, generators.\n## Hours\nMon-Fri 8am-5pm, Sat 9am-2pm.",
        "ci": "You are the electrical assistant. Collect name, phone, address, issue description. NEVER mention AgentNexLiFy.",
        "faqs": [
            {"question": "Are you licensed?", "answer": "Yes, master electrician license.", "category": "credentials"},
            {"question": "Do you offer emergency service?", "answer": "Yes, 24/7 for outages and hazards.", "category": "emergency"},
            {"question": "Do you give free estimates?", "answer": "Yes, free in-home estimates.", "category": "pricing"},
        ],
    },
}

# Aliases — map common business_type variants to canonical preset key.
_ALIASES = {
    "plumber": "plumbing",
    "plumbers": "plumbing",
    "heating_cooling": "hvac",
    "ac": "hvac",
    "house_cleaning": "cleaning",
    "maid": "cleaning",
    "pressure_washing": "power_washing",
    "powerwash": "power_washing",
    "lawn_care": "landscaping",
    "landscaper": "landscaping",
    "electrician": "electrical",
}


def get_vertical_preset(business_type: str | None) -> dict | None:
    """Return preset dict for a business_type, or None if no match."""
    if not business_type:
        return None
    key = business_type.strip().lower().replace(" ", "_").replace("-", "_")
    key = _ALIASES.get(key, key)
    return _PRESETS.get(key)


def get_default_hours_for(business_type: str | None) -> dict[str, str]:
    """Return 7-key hours dict for a vertical, or the global default."""
    preset = get_vertical_preset(business_type)
    return dict(preset["hours"]) if preset else dict(DEFAULT_HOURS)
