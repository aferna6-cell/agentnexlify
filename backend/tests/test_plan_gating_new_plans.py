"""Plan-gating contract for the 2026-06-15 repricing (chatbot / agent_os).

Background (GH #292): repricing commit 9bed342 introduced two paid plans —
`chatbot` ($19.99, widget/chat only) and `agent_os` ($99.99, full platform) —
but the feature gates kept hard-coding the retired plan names
(growth/autopilot/professional/enterprise). New paying tenants were locked out
of features they bought.

Intended mapping (from stripe_service.py comments + plan_gate.MARKETING_PLANS):
  - agent_os  → full platform: unlocks every premium gate
  - chatbot   → widget/chat only: stays OUT of premium back-office gates,
                but gets entry-tier widget branding (no white-label)

If product later decides a specific premium feature should also be available on
`chatbot`, add it to that one gate + flip the assertion here.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# --- agent_os unlocks every premium gate -----------------------------------

def test_agent_os_allowed_zapier_api_keys():
    from backend.services.api_key_auth import _ALLOWED_PLANS
    assert "agent_os" in _ALLOWED_PLANS


def test_agent_os_unlimited_sms():
    from backend.services.sms_rate_limiter import _UNLIMITED_PLANS
    assert "agent_os" in _UNLIMITED_PLANS


def test_agent_os_eligible_document_drafting():
    from backend.services.document_drafting import _ELIGIBLE_PLANS
    assert "agent_os" in _ELIGIBLE_PLANS


def test_agent_os_eligible_lead_qualification():
    from backend.services.lead_qualification import _ELIGIBLE_PLANS
    assert "agent_os" in _ELIGIBLE_PLANS


def test_agent_os_can_white_label_branding():
    from backend.services.branding_helpers import _filter_branding_for_plan
    full = {
        "primary_color": "#111",
        "logo_url": "https://x/logo.png",
        "hide_powered_by": True,
        "custom_css": ".x{color:red}",
    }
    out = _filter_branding_for_plan(full, "agent_os")
    # Full platform = enterprise-grade branding: white-label + logo + custom CSS
    assert out.get("hide_powered_by") is True
    assert "logo_url" in out
    assert "custom_css" in out


# --- chatbot is the widget/chat entry tier ----------------------------------

def test_chatbot_excluded_from_premium_backoffice_gates():
    from backend.services.api_key_auth import _ALLOWED_PLANS
    from backend.services.sms_rate_limiter import _UNLIMITED_PLANS
    from backend.services.document_drafting import _ELIGIBLE_PLANS
    from backend.services.lead_qualification import _ELIGIBLE_PLANS as LQ
    # chatbot ($19.99) is "widget/chat only" — not the premium back-office set.
    assert "chatbot" not in _ALLOWED_PLANS
    assert "chatbot" not in _UNLIMITED_PLANS
    assert "chatbot" not in _ELIGIBLE_PLANS
    assert "chatbot" not in LQ


def test_reconciliation_baseline_tokens_match_canonical():
    # billing_reconciliation (read-only audit) must mirror the canonical
    # ai_usage_guard.PLAN_BASELINE_TOKENS for the new plans, or audit reports
    # mis-state caps for chatbot/agent_os tenants (GH #293 issue 2).
    from backend.services.ai_usage_guard import PLAN_BASELINE_TOKENS
    from backend.services.billing_reconciliation import _PLAN_BASELINE_AI_TOKENS
    assert _PLAN_BASELINE_AI_TOKENS["chatbot"] == PLAN_BASELINE_TOKENS["chatbot"]
    assert _PLAN_BASELINE_AI_TOKENS["agent_os"] == PLAN_BASELINE_TOKENS["agent_os"]


def test_chatbot_gets_widget_branding_but_no_white_label():
    from backend.services.branding_helpers import _filter_branding_for_plan
    full = {
        "primary_color": "#111",
        "widget_title": "Chat with us",
        "hide_powered_by": True,
        "custom_css": ".x{color:red}",
    }
    out = _filter_branding_for_plan(full, "chatbot")
    # Entry tier: widget look-and-feel yes, white-label no.
    assert out.get("primary_color") == "#111"
    assert out.get("widget_title") == "Chat with us"
    assert "hide_powered_by" not in out
    assert "custom_css" not in out


# --- Agent OS suite gate (round-3, 2026-07-21) ------------------------------

def test_agent_os_in_suite_gate():
    from backend.services.agent_os_gate import AGENT_OS_PLANS
    assert "agent_os" in AGENT_OS_PLANS


def test_legacy_plans_grandfathered_in_suite_gate():
    from backend.services.agent_os_gate import AGENT_OS_PLANS
    for plan in ("growth", "autopilot", "professional", "enterprise"):
        assert plan in AGENT_OS_PLANS


def test_chatbot_and_free_excluded_from_suite_gate():
    from backend.services.agent_os_gate import AGENT_OS_PLANS
    assert "chatbot" not in AGENT_OS_PLANS
    assert "free" not in AGENT_OS_PLANS


# --- Marketing gate aligned with the suite gate (round-4, 2026-07-21) -------

def test_marketing_plans_match_suite_gate():
    # Marketing is surfaced through the Agent OS marketing department, so the
    # standalone marketing routers honor exactly the plans that have the
    # workforce. Until 2026-07-21 MARKETING_PLANS was {"agent_os"} only,
    # wrongly 402-ing grandfathered contracts (CLAUDE.md: gates include them).
    from backend.services.agent_os_gate import AGENT_OS_PLANS
    from backend.services.plan_gate import MARKETING_PLANS
    assert MARKETING_PLANS == set(AGENT_OS_PLANS)


def test_legacy_plans_grandfathered_in_marketing_gate():
    from backend.services.plan_gate import MARKETING_PLANS
    for plan in ("growth", "autopilot", "professional", "enterprise"):
        assert plan in MARKETING_PLANS


def test_chatbot_and_free_still_excluded_from_marketing_gate():
    from backend.services.plan_gate import MARKETING_PLANS
    assert "chatbot" not in MARKETING_PLANS
    assert "free" not in MARKETING_PLANS


def test_campaign_send_plans_share_marketing_source_of_truth():
    from backend.routers.marketing_campaigns import _CAMPAIGN_SEND_PLANS
    from backend.services.plan_gate import MARKETING_PLANS
    assert _CAMPAIGN_SEND_PLANS is MARKETING_PLANS


def test_appointment_briefs_router_carries_full_guard_stack():
    # GH #643: both brief endpoints call Claude; the router must carry the
    # demo block + agent_os plan gate (chatbot/free get 402 from the gate).
    from backend.dependencies import block_demo_role
    from backend.routers.appointment_briefs import router
    from backend.services.agent_os_gate import require_agent_os_access
    deps = [d.dependency for d in router.dependencies]
    assert block_demo_role in deps
    assert require_agent_os_access in deps
