"""Drift guard: every premium feature gate must match the canonical plan catalog.

This is the systemic fix for the recurring plan-name-drift bug class (GH #81/#181/#292/#293).
Per-feature assertions live in test_plan_gating_new_plans.py; this test is data-driven over
ALL premium gates so a future repricing that adds a paid plan (or leaves a gate stale) fails
HERE — update backend/services/plan_catalog.py + the gate, and this goes green again.

Contract for every premium gate collection:
  - must unlock every PREMIUM_PLANS member (no current premium plan locked out),
  - must contain only ALL_KNOWN_PLANS members (no typos / retired-only names),
  - must exclude chatbot (entry tier) and every RETIRED name.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.services.plan_catalog import (  # noqa: E402
    ALL_KNOWN_PLANS,
    PREMIUM_PLANS,
    RETIRED_PLANS,
)


def _premium_gates():
    """(label, set-of-plan-names) for every premium back-office gate.

    Add a row when you add a premium gate. The import is inside the helper so a
    collection error names the offending module instead of failing collection.
    """
    from backend.services.api_key_auth import _ALLOWED_PLANS
    from backend.services.sms_rate_limiter import _UNLIMITED_PLANS
    from backend.services.document_drafting import _ELIGIBLE_PLANS as DOC
    from backend.services.lead_qualification import _ELIGIBLE_PLANS as LQ
    from backend.routers.marketing_campaigns import _CAMPAIGN_SEND_PLANS

    return [
        ("api_key_auth._ALLOWED_PLANS (Zapier)", set(_ALLOWED_PLANS)),
        ("sms_rate_limiter._UNLIMITED_PLANS", set(_UNLIMITED_PLANS)),
        ("document_drafting._ELIGIBLE_PLANS", set(DOC)),
        ("lead_qualification._ELIGIBLE_PLANS", set(LQ)),
        ("marketing_campaigns._CAMPAIGN_SEND_PLANS", set(_CAMPAIGN_SEND_PLANS)),
    ]


@pytest.mark.parametrize("label,gate", _premium_gates())
def test_premium_gate_unlocks_all_premium_plans(label, gate):
    missing = PREMIUM_PLANS - gate
    assert not missing, f"{label} locks out premium plan(s): {sorted(missing)}"


@pytest.mark.parametrize("label,gate", _premium_gates())
def test_gate_has_no_unknown_plan_names(label, gate):
    unknown = gate - ALL_KNOWN_PLANS
    assert not unknown, f"{label} has unknown/stale plan name(s): {sorted(unknown)}"


@pytest.mark.parametrize("label,gate", _premium_gates())
def test_gate_excludes_retired_names(label, gate):
    leaked = gate & RETIRED_PLANS
    assert not leaked, f"{label} contains retired plan name(s): {sorted(leaked)}"


@pytest.mark.parametrize("label,gate", _premium_gates())
def test_chatbot_stays_entry_tier(label, gate):
    # chatbot ($19.99) is widget/chat only — never in a premium back-office gate.
    assert "chatbot" not in gate, f"{label} wrongly unlocks chatbot (entry tier)"


def test_reconciliation_tokens_cover_current_paid_plans():
    # billing_reconciliation audit caps must mirror canonical baselines for the
    # plans actually sold today, or audit reports mis-state caps (GH #293 issue 2).
    from backend.services.ai_usage_guard import PLAN_BASELINE_TOKENS
    from backend.services.billing_reconciliation import _PLAN_BASELINE_AI_TOKENS
    from backend.services.plan_catalog import CURRENT_PAID_PLANS

    for plan in CURRENT_PAID_PLANS:
        assert plan in PLAN_BASELINE_TOKENS, f"{plan} missing from ai_usage_guard"
        assert _PLAN_BASELINE_AI_TOKENS.get(plan) == PLAN_BASELINE_TOKENS[plan], (
            f"reconciliation baseline for {plan} != canonical ai_usage_guard"
        )


def test_catalog_self_consistency():
    # agent_os is the current full-platform plan and must be premium.
    assert "agent_os" in PREMIUM_PLANS
    # chatbot is entry tier — not premium.
    assert "chatbot" not in PREMIUM_PLANS
    # retired names are not "known".
    assert not (RETIRED_PLANS & ALL_KNOWN_PLANS)
