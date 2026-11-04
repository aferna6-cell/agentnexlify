"""Lead status → pipeline column mapping."""

from backend.services.pipeline_analytics import group_leads_by_stage, resolve_stage
from backend.services.pipeline_presets import DEFAULT_STAGES


def test_new_status_lands_in_new_lead_column():
    lead = {"id": "l1", "status": "new", "deal_value": 0}
    grouped = group_leads_by_stage([lead], DEFAULT_STAGES)
    assert grouped["New Lead"] == [lead]
    assert grouped["Contacted"] == []
    assert "_unmatched" not in grouped


def test_closed_maps_to_won_stage():
    stage = resolve_stage("closed", DEFAULT_STAGES)
    assert stage is not None
    assert stage["name"] == "Won"
    assert stage["is_won"] is True


def test_lost_maps_to_lost_stage():
    stage = resolve_stage("lost", DEFAULT_STAGES)
    assert stage["name"] == "Lost"
    assert stage["is_lost"] is True


def test_exact_stage_name_wins_over_alias():
    stage = resolve_stage("Qualified", DEFAULT_STAGES)
    assert stage["name"] == "Qualified"


def test_blank_status_uses_first_open_stage():
    stage = resolve_stage(None, DEFAULT_STAGES)
    assert stage["name"] == "New Lead"


def test_unknown_status_stays_unmatched():
    grouped = group_leads_by_stage(
        [{"id": "x", "status": "not-a-stage", "deal_value": 250}],
        DEFAULT_STAGES,
    )
    assert grouped["_unmatched"][0]["id"] == "x"
    assert all(grouped[stage["name"]] == [] for stage in DEFAULT_STAGES)


def test_zero_deal_value_still_appears_in_the_column():
    """$0 is the stored deal_value default, not a reason to hide the deal."""
    lead = {"id": "l2", "status": "appointment_booked", "deal_value": 0}
    grouped = group_leads_by_stage([lead], DEFAULT_STAGES)
    placed = [item for rows in grouped.values() for item in rows if isinstance(rows, list)]
    assert lead in placed
    assert sum(item.get("deal_value") or 0 for item in placed) == 0


def test_appointment_booked_alias_is_case_insensitive():
    stage = resolve_stage("Appointment_Booked", DEFAULT_STAGES)
    assert stage is not None
    assert stage["name"] == "Qualified"


def test_empty_stage_list_returns_none():
    assert resolve_stage("new", []) is None


def test_two_deals_split_across_columns_match_the_total():
    leads = [
        {"id": "a", "status": "new", "deal_value": 0},
        {"id": "b", "status": "contacted", "deal_value": 0},
    ]
    grouped = group_leads_by_stage(leads, DEFAULT_STAGES)
    visible = sum(len(grouped[stage["name"]]) for stage in DEFAULT_STAGES)
    assert visible == 2
    assert grouped["New Lead"][0]["id"] == "a"
    assert grouped["Contacted"][0]["id"] == "b"
