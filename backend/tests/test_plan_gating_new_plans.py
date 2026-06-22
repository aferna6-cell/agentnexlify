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
