"""Tests for KPI-based agent escalation thresholds.

Pattern source: knowledge-base/raw/competitors/solo-agency-7-agent-pattern-2026-05-06.md
Bounded autonomy — agents wake human on KPI drift, not just confidence drop.
"""

from backend.services.agent_escalation import (
    ESCALATION_THRESHOLDS,
    EscalationDecision,
    check_escalation,
)


def test_no_escalation_when_kpis_healthy():
    decision = check_escalation(
        "lead_qualifier",
        {"qualified_rate_24h": 0.25},
    )
    assert decision.should_escalate is False
    assert decision.reasons == ()
    assert decision.reason is None


def test_escalates_when_qualified_rate_below_threshold():
    decision = check_escalation(
        "lead_qualifier",
        {"qualified_rate_24h": 0.05},
    )
    assert decision.should_escalate is True
    assert "qualified_rate_24h" in decision.reasons[0]


def test_escalates_on_high_value_deal():
    decision = check_escalation(
        "appointment_booker",
        {"booking_success_rate_24h": 0.50, "deal_value_usd": 3400.0},
    )
    assert decision.should_escalate is True
    deal_reasons = [r for r in decision.reasons if "deal_value_usd" in r]
    assert len(deal_reasons) == 1
    assert "3,400" in deal_reasons[0]


def test_escalates_on_low_booking_rate():
    decision = check_escalation(
        "appointment_booker",
        {"booking_success_rate_24h": 0.20, "deal_value_usd": 500.0},
    )
    assert decision.should_escalate is True
    assert any("booking_success_rate_24h" in r for r in decision.reasons)


def test_no_escalation_when_deal_at_threshold():
    """Threshold is strict greater-than. $3000 exactly does NOT trigger."""
    decision = check_escalation(
        "appointment_booker",
        {"booking_success_rate_24h": 0.50, "deal_value_usd": 3000.0},
    )
    assert decision.should_escalate is False


def test_unknown_agent_never_escalates():
    decision = check_escalation(
        "no_such_agent",
        {"qualified_rate_24h": 0.0, "deal_value_usd": 999_999.0},
    )
    assert decision.should_escalate is False


def test_missing_kpi_does_not_escalate():
    """If a metric isn't reported, that threshold can't fire."""
    decision = check_escalation("lead_qualifier", {})
    assert decision.should_escalate is False


def test_multiple_reasons_collected():
    decision = check_escalation(
        "appointment_booker",
        {"booking_success_rate_24h": 0.10, "deal_value_usd": 5000.0},
    )
    assert decision.should_escalate is True
    assert len(decision.reasons) == 2


def test_threshold_override_for_testing():
    thresholds = {"lead_qualifier": {"min_qualified_rate_24h": 0.50}}
    decision = check_escalation(
        "lead_qualifier",
        {"qualified_rate_24h": 0.40},
        thresholds=thresholds,
    )
    assert decision.should_escalate is True


def test_unresolved_escalation_rate_threshold():
    decision = check_escalation(
        "support_agent",
        {"unresolved_escalation_rate_24h": 0.30},
    )
    assert decision.should_escalate is True
    assert "unresolved_escalation_rate_24h" in decision.reasons[0]


def test_default_thresholds_have_required_agents():
    assert "lead_qualifier" in ESCALATION_THRESHOLDS
    assert "appointment_booker" in ESCALATION_THRESHOLDS
    assert "support_agent" in ESCALATION_THRESHOLDS
    assert (
        ESCALATION_THRESHOLDS["appointment_booker"]["max_deal_value_usd_no_approval"]
        == 3000.0
    )


def test_decision_dataclass_is_frozen():
    decision = EscalationDecision(should_escalate=False, reasons=())
    try:
        decision.should_escalate = True  # type: ignore[misc]
    except (AttributeError, Exception):
        return
    raise AssertionError("EscalationDecision should be immutable")


def test_decision_reason_returns_first_reason():
    decision = check_escalation(
        "appointment_booker",
        {"booking_success_rate_24h": 0.10, "deal_value_usd": 5000.0},
    )
    assert decision.reason == decision.reasons[0]
