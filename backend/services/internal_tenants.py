"""Internal-tenant denylist helper.

These are accounts used by AgentNexLiFy staff for smoke-testing,
demos, and onboarding — NOT real paying customers.  Counting them
in admin metrics (funnel, health, churn-watch) inflates every number
and masks real customer data.

Known internal accounts (2026-06-23 audit):
  - "AgentNexLiFy"          — platform owner default account
  - "AgentNexLiFy Smoke Test" — automated regression tenant
  - "Agent Nexlify"         — variant name used in older seeds

Matching is case-insensitive substring matching against
``business_name`` so future test accounts with similar names are
caught automatically.

Usage
-----
    from backend.services.internal_tenants import is_internal_tenant

    tenants = [t for t in all_tenants if not is_internal_tenant(t)]
"""

# ---------------------------------------------------------------------------
# Denylist
# ---------------------------------------------------------------------------

# Lowercase substrings that identify an internal / test tenant.
# Match is: any pattern in INTERNAL_TENANT_NAME_PATTERNS is a substring of
# business_name.lower().strip()
INTERNAL_TENANT_NAME_PATTERNS: tuple[str, ...] = (
    "agentnexlify",   # covers "AgentNexLiFy", "AgentNexLiFy Smoke Test", "Agent NexLiFy"
    "smoke test",     # belt-and-suspenders for any "Smoke Test" account
    "test account",   # generic internal test accounts
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_internal_tenant(tenant: dict) -> bool:
    """Return True when *tenant* is an internal / test account.

    Parameters
    ----------
    tenant:
        A dict with at least a ``business_name`` key (as returned by
        the Supabase ``tenants`` table).  Missing or null names are
        treated as NOT internal (conservative — real customers with no
        name yet should not be hidden).

    Returns
    -------
    bool
        True  → internal / test account; exclude from metrics.
        False → real customer; include in metrics.
    """
    raw_name: str | None = tenant.get("business_name")
    if not raw_name:
        return False

    normalised = raw_name.strip().lower()
    return any(pattern in normalised for pattern in INTERNAL_TENANT_NAME_PATTERNS)
