"""KPI-based escalation thresholds for managed agents.

Pattern source: knowledge-base/raw/competitors/solo-agency-7-agent-pattern-2026-05-06.md
Bounded autonomy — agents wake human on KPI drift, not just confidence drop.

Deterministic: no LLM call. Caller passes the latest KPI snapshot; module
compares against configured thresholds and returns an immutable decision.
"""

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class EscalationDecision:
    should_escalate: bool
    reasons: tuple[str, ...]

    @property
    def reason(self) -> str | None:
        return self.reasons[0] if self.reasons else None


ESCALATION_THRESHOLDS: dict[str, dict[str, float]] = {
    "lead_qualifier": {
        "min_qualified_rate_24h": 0.12,
    },
    "appointment_booker": {
        "min_booking_success_rate_24h": 0.40,
        "max_deal_value_usd_no_approval": 3000.0,
    },
    "support_agent": {
        "max_unresolved_escalation_rate_24h": 0.20,
    },
    "document_drafter": {
        "max_deal_value_usd_no_approval": 3000.0,
    },
}


_RATE_KEYS = {
    "min_qualified_rate_24h": "qualified_rate_24h",
    "min_booking_success_rate_24h": "booking_success_rate_24h",
    "max_unresolved_escalation_rate_24h": "unresolved_escalation_rate_24h",
}

_DEAL_KEY = "max_deal_value_usd_no_approval"
_DEAL_KPI = "deal_value_usd"


def check_escalation(
    agent_name: str,
    kpis: Mapping[str, float],
    *,
    thresholds: Mapping[str, Mapping[str, float]] | None = None,
) -> EscalationDecision:
    config = (thresholds if thresholds is not None else ESCALATION_THRESHOLDS).get(agent_name)
    if not config:
        return EscalationDecision(should_escalate=False, reasons=())

    reasons: list[str] = []

    for threshold_key, kpi_key in _RATE_KEYS.items():
        if threshold_key not in config or kpi_key not in kpis:
            continue
        limit = config[threshold_key]
        observed = kpis[kpi_key]
        if threshold_key.startswith("min_") and observed < limit:
            reasons.append(
                f"{kpi_key} {observed:.2%} below threshold {limit:.2%}"
            )
        elif threshold_key.startswith("max_") and observed > limit:
            reasons.append(
                f"{kpi_key} {observed:.2%} above threshold {limit:.2%}"
            )

    if _DEAL_KEY in config and _DEAL_KPI in kpis:
        limit = config[_DEAL_KEY]
        observed = kpis[_DEAL_KPI]
        if observed > limit:
            reasons.append(
                f"{_DEAL_KPI} ${observed:,.0f} above threshold ${limit:,.0f}"
            )

    return EscalationDecision(
        should_escalate=bool(reasons),
        reasons=tuple(reasons),
    )
