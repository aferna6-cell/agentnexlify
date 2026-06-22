"""Canonical plan catalog — single source of truth for plan-name sets.

Repricing has repeatedly left feature-gate dicts holding stale plan names while new
paid plans were locked out of features they bought (GH #81, #181, #292, #293). This module
names the canonical sets once; `backend/tests/test_plan_catalog_coverage.py` asserts every
live gate matches, so the *next* repricing fails loudly here instead of silently in prod.

Canonical pricing (CLAUDE.md, repriced 2026-06-15):
  - chatbot  ($19.99/mo) = "AI Front Desk" — widget/chat entry tier.
  - agent_os ($99.99/mo) = "AI Workforce" — full platform; unlocks every premium gate.
  - free = internal lapsed/no-subscription state, never sold.
  - growth / autopilot / professional / enterprise = legacy, grandfathered, still honored.
  - foundation / operations = retired names; must appear in NO gate.
"""

# Current sellable paid plans.
CURRENT_PAID_PLANS: frozenset[str] = frozenset({"chatbot", "agent_os"})

# Legacy paid plans still honored on old contracts (grandfathered).
LEGACY_PAID_PLANS: frozenset[str] = frozenset(
    {"growth", "autopilot", "professional", "enterprise"}
)

# Plans that unlock the premium back-office gates (Zapier API keys, unlimited SMS,
# document drafting, lead qualification, branded automation, white-label).
# = agent_os (current full platform) + every legacy paid plan. chatbot is entry-tier.
PREMIUM_PLANS: frozenset[str] = frozenset({"agent_os"}) | LEGACY_PAID_PLANS

# Internal / non-premium states.
INTERNAL_PLANS: frozenset[str] = frozenset({"free"})

# Every plan name that may legitimately appear anywhere in plan-gating code.
ALL_KNOWN_PLANS: frozenset[str] = (
    CURRENT_PAID_PLANS | LEGACY_PAID_PLANS | INTERNAL_PLANS
)

# Retired names that must never appear in a gate again.
RETIRED_PLANS: frozenset[str] = frozenset({"foundation", "operations"})
