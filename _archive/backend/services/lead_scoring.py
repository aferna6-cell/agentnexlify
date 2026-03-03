"""Lead scoring logic — computes score and temperature from lead attributes."""

from __future__ import annotations


def compute_lead_score(
    timeline: str | None = None,
    budget: str | None = None,
    pre_approved: bool | None = None,
    has_email: bool = False,
    has_phone: bool = False,
    wants_appointment: bool = False,
) -> tuple[int, str]:
    """Return (score 1-10, temperature hot/warm/cold) based on lead signals."""
    score = 1  # baseline

    # Contact info
    if has_email:
        score += 1
    if has_phone:
        score += 1

    # Timeline urgency
    if timeline:
        tl = timeline.lower()
        if any(w in tl for w in ["asap", "immediately", "this week", "this month", "1 month", "under 1"]):
            score += 3
        elif any(w in tl for w in ["1-3", "2-3", "next few months", "within 3", "spring", "summer"]):
            score += 2
        elif any(w in tl for w in ["3-6", "6 month", "later this year"]):
            score += 1

    # Budget specificity
    if budget:
        score += 1

    # Pre-approval
    if pre_approved:
        score += 2

    # Wants appointment = high intent
    if wants_appointment:
        score += 2

    score = min(score, 10)

    if score >= 8:
        temperature = "hot"
    elif score >= 5:
        temperature = "warm"
    else:
        temperature = "cold"

    return score, temperature
