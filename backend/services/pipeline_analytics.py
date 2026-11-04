"""Pure computation for pipeline analytics metrics.

Extracted from backend/routers/pipeline.py so the router stays thin and
the math is unit-testable without a database.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Stored lead statuses (widget capture writes "new", "contacted",
# "appointment_booked", "closed", "lost") mapped onto pipeline stage names.
# Exact stage-name matches still win before this table is consulted.
_STATUS_HINTS: dict[str, tuple[str, ...]] = {
    "new": ("new", "new lead", "new patient", "new client", "inquiry", "trial"),
    "contacted": ("contacted", "consulted", "consultation", "estimate sent"),
    "appointment booked": (
        "appointment booked",
        "booked",
        "qualified",
        "reservation",
        "showing scheduled",
    ),
    "qualified": ("qualified",),
    "proposal sent": ("proposal sent",),
    "closed": ("closed", "won", "completed", "resolved", "regular client", "member"),
    "won": ("won", "closed", "completed", "resolved"),
    "lost": ("lost", "inactive", "declined", "cancelled", "canceled", "churned"),
}


def _stage_name(stage: dict) -> str:
    return (stage.get("name") or "").strip().lower()


def resolve_stage(status: str | None, stages: list[dict]) -> dict | None:
    """Map a lead status onto a pipeline stage.

    Order: exact stage name, known status aliases, won/lost flags, then the
    first open stage for a blank or ``new`` status. Unknown statuses return
    None so they are not silently filed under the wrong column.
    """
    ordered = sorted(stages, key=lambda stage: stage.get("sort_order", 0))
    if not ordered:
        return None

    raw = (status or "").strip().lower().replace("_", " ")
    by_name = {_stage_name(stage): stage for stage in ordered if _stage_name(stage)}
    if raw in by_name:
        return by_name[raw]

    for hint in _STATUS_HINTS.get(raw, ()):
        match = by_name.get(hint)
        if match is not None:
            return match

    if raw in {"closed", "won"}:
        won = [stage for stage in ordered if stage.get("is_won")]
        if won:
            return won[0]
    if raw == "lost":
        lost = [stage for stage in ordered if stage.get("is_lost")]
        if lost:
            return lost[0]
    if raw in {"", "new"}:
        open_stages = [
            stage
            for stage in ordered
            if not stage.get("is_won") and not stage.get("is_lost")
        ]
        if open_stages:
            return open_stages[0]
    return None


def group_leads_by_stage(leads: list[dict], stages: list[dict]) -> dict[str, list]:
    """Place each lead on the stage ``resolve_stage`` picks.

    Keys are stage names. Leads with no stage are returned under ``_unmatched``
    so the total still includes them and the UI can see they were not dropped.
    """
    grouped: dict[str, list] = {stage["name"]: [] for stage in stages}
    unmatched: list = []
    for lead in leads:
        stage = resolve_stage(lead.get("status"), stages)
        name = stage.get("name") if stage else None
        if name in grouped:
            grouped[name].append(lead)
        else:
            unmatched.append(lead)
    if unmatched:
        grouped["_unmatched"] = unmatched
    return grouped


def _parse_iso(value) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def compute_pipeline_metrics(leads: list[dict], stages: list[dict], now: datetime | None = None) -> dict:
    """Compute pipeline-level KPIs from raw leads + stages.

    Returns: total/won pipeline value, conversion rate, avg deal size,
    avg days-to-close, leads-by-stage counts, current-month rollups.
    """
    now = now or datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_pipeline_value = 0.0
    total_won_value = 0.0
    won_count = 0
    days_to_close_list: list[float] = []
    leads_by_stage: dict[str, int] = {}
    deals_this_month = 0
    won_this_month = 0
    total_closed = 0

    for lead in leads:
        stage = resolve_stage(lead.get("status"), stages)
        deal_value = float(lead.get("deal_value") or 0)
        is_won = bool(stage and stage.get("is_won"))
        is_lost = bool(stage and stage.get("is_lost"))

        if not is_lost:
            total_pipeline_value += deal_value

        if is_won:
            total_won_value += deal_value
            won_count += 1
            total_closed += 1

            created_dt = _parse_iso(lead.get("created_at"))
            changed_dt = _parse_iso(lead.get("stage_changed_at"))
            if created_dt and changed_dt:
                days = (changed_dt - created_dt).days
                if days >= 0:
                    days_to_close_list.append(float(days))

        if is_lost:
            total_closed += 1

        original_status = lead.get("status") or "unknown"
        leads_by_stage[original_status] = leads_by_stage.get(original_status, 0) + 1

        ref_dt = _parse_iso(lead.get("stage_changed_at") or lead.get("created_at"))
        if ref_dt and ref_dt >= month_start:
            deals_this_month += 1
            if is_won:
                won_this_month += 1

    conversion_rate = round(won_count / total_closed * 100, 1) if total_closed > 0 else 0.0
    avg_deal_value = round(total_won_value / won_count, 2) if won_count > 0 else 0.0
    avg_days_to_close = (
        round(sum(days_to_close_list) / len(days_to_close_list), 1) if days_to_close_list else 0.0
    )

    return {
        "total_pipeline_value": round(total_pipeline_value, 2),
        "total_won_value": round(total_won_value, 2),
        "conversion_rate": conversion_rate,
        "avg_deal_value": avg_deal_value,
        "avg_days_to_close": avg_days_to_close,
        "leads_by_stage": leads_by_stage,
        "deals_this_month": deals_this_month,
        "won_this_month": won_this_month,
    }


def annotate_days_in_stage(leads: list[dict], now: datetime | None = None) -> None:
    """Add `days_in_stage` key to each lead in-place using stage_changed_at or created_at."""
    now = now or datetime.now(timezone.utc)
    for lead in leads:
        changed_at = lead.get("stage_changed_at") or lead.get("created_at")
        dt = _parse_iso(changed_at)
        if dt:
            lead["days_in_stage"] = (now - dt).days
        else:
            lead["days_in_stage"] = 0
