"""Unit tests for scripts/autonomy/backlog.py — the loop's value floor.

This module is the answer to a documented failure: an autonomous loop with no
floor does not stop when the worthwhile backlog runs out, it starts
manufacturing niche work. So the contract under test is mostly about *refusing*:

  1. `WorkItem.score` ranks value per unit effort, discounted by confidence, so
     a cheap moderate win beats an expensive high-value one.
  2. Every exclusion reports the RIGHT reason, in the documented precedence
     order (blocked > owner_gated > risk > floor). A wrong reason sends the
     driving session off fixing the wrong thing.
  3. `select` is deterministic — a rerun on unchanged input picks the same item,
     whatever order the candidates arrived in.
  4. An empty actionable set is a first-class answer with an explanation, and
     becomes "dry" once it has happened DRY_AFTER_IDLE_ROUNDS times.
  5. `load_items` reads what the driving session actually writes.

No model, no network, no subprocess. The guardrail is inspectable without
running an agent at all, which is the whole reason it lives in plain code.
"""

import json
import os
import random
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from scripts.autonomy.backlog import (  # noqa: E402
    ACTIONABLE_RISK,
    DRY_AFTER_IDLE_ROUNDS,
    VALUE_FLOOR,
    Selection,
    WorkItem,
    load_items,
    select,
)
from scripts.autonomy.backlog import _EPSILON as EPSILON  # noqa: E402


# --------------------------------------------------------------------------
# Builders
# --------------------------------------------------------------------------


def item(item_id="task-1", **overrides):
    """An actionable item by default — override one field to make it not."""
    fields = {
        "id": item_id,
        "title": f"do {item_id}",
        "value": 1.0,
        "effort": 0.2,
        "confidence": 0.9,
        "risk": "low",
    }
    fields.update(overrides)
    return WorkItem(**fields)


def reason_for(selection: Selection, item_id: str) -> str:
    reasons = [reason for skipped_id, reason in selection.skipped if skipped_id == item_id]
    assert reasons, f"{item_id!r} was not skipped: {selection.skipped}"
    return reasons[0]


# --------------------------------------------------------------------------
# WorkItem.score
# --------------------------------------------------------------------------


def test_score_is_value_times_confidence_over_effort():
    scored = item(value=0.8, confidence=0.5, effort=0.2)

    assert scored.score == pytest.approx((0.8 * 0.5) / (0.2 + EPSILON))


def test_a_cheap_moderate_win_outranks_an_expensive_high_value_one():
    """Effort divides rather than subtracts, which is what buys this ordering."""
    cheap = item("cheap", value=0.5, confidence=0.9, effort=0.1)
    expensive = item("expensive", value=1.0, confidence=0.9, effort=1.0)

    assert cheap.score > expensive.score
    assert select([expensive, cheap]).chosen.id == "cheap"


def test_confidence_discounts_an_otherwise_identical_item():
    sure = item("sure", confidence=0.9)
    unsure = item("unsure", confidence=0.3)

    assert sure.score > unsure.score


def test_zero_effort_does_not_divide_by_zero():
    free = item(value=1.0, confidence=1.0, effort=0.0)

    assert free.score == pytest.approx(1.0 / EPSILON)
    assert free.score == pytest.approx(20.0)


def test_zero_value_scores_zero_regardless_of_effort():
    assert item(value=0.0, effort=0.01).score == 0.0


# --------------------------------------------------------------------------
# WorkItem.from_dict
# --------------------------------------------------------------------------


def test_from_dict_ignores_unknown_keys():
    """The session ships whatever GitHub gave it; extra keys must not explode."""
    parsed = WorkItem.from_dict(
        {
            "id": "gh-42",
            "title": "Fix the thing",
            "value": 0.7,
            "assignee": "octocat",
            "reactions": {"+1": 3},
            "milestone": None,
        }
    )

    assert parsed.id == "gh-42"
    assert parsed.value == 0.7
    assert not hasattr(parsed, "assignee")


def test_from_dict_coerces_labels_to_a_tuple():
    parsed = WorkItem.from_dict({"id": "x", "title": "T", "labels": ["bug", "backend"]})

    assert parsed.labels == ("bug", "backend")
    assert isinstance(parsed.labels, tuple)


def test_from_dict_leaves_labels_alone_when_absent():
    assert WorkItem.from_dict({"id": "x", "title": "T"}).labels == ()


def test_from_dict_without_an_id_is_a_hard_error():
    with pytest.raises(ValueError) as exc:
        WorkItem.from_dict({"title": "no id here"})

    assert "needs an id" in str(exc.value)


def test_a_missing_title_degrades_instead_of_raising():
    """`id` is identity and is enforced; `title` is a human label and is not.

    The backlog is written by a model, so a cosmetic field going missing must
    not take the whole cycle down — a hard failure here would turn "the scorer
    forgot a label" into "the loop did nothing today". The cost is a less
    readable journal line, which is the right trade.
    """
    parsed = WorkItem.from_dict({"id": "x", "value": 1.0, "effort": 0.2})

    assert parsed.title == ""
    assert select([parsed]).has_work is True


def test_from_dict_treats_an_empty_id_as_missing():
    with pytest.raises(ValueError):
        WorkItem.from_dict({"id": "", "title": "blank"})


def test_from_dict_defaults_match_the_dataclass():
    parsed = WorkItem.from_dict({"id": "x", "title": "T"})

    assert (parsed.value, parsed.effort, parsed.confidence) == (0.0, 0.5, 0.5)
    assert parsed.risk == "medium"
    assert parsed.blocked is False
    assert parsed.owner_gated is False
    assert parsed.touches_frontend is False


# --------------------------------------------------------------------------
# select — ordering and determinism
# --------------------------------------------------------------------------


def test_select_picks_the_highest_scorer():
    best = item("best", value=1.0, effort=0.1)
    ok = item("ok", value=0.6, effort=0.3)

    chosen = select([ok, best]).chosen

    assert chosen.id == "best"


def test_select_returns_exactly_one_item():
    selection = select([item("a"), item("b"), item("c")])

    assert selection.has_work is True
    assert selection.chosen is not None
    assert selection.skipped == []


def test_ties_are_broken_by_id():
    later = item("b-second", value=0.8, effort=0.2, confidence=0.9)
    earlier = item("a-first", value=0.8, effort=0.2, confidence=0.9)

    assert earlier.score == later.score
    assert select([later, earlier]).chosen.id == "a-first"


def test_selection_is_stable_across_shuffled_input():
    """A rerun on unchanged input must pick the same item, or the loop retries
    a different task every cycle and finishes none of them."""
    items = [
        item("alpha", value=0.8, effort=0.2),
        item("bravo", value=0.8, effort=0.2),  # exact tie with alpha
        item("charlie", value=0.7, effort=0.2),
        item("delta", value=0.6, effort=0.4),
    ]
    rng = random.Random(1234)

    picks = set()
    for _ in range(25):
        shuffled = list(items)
        rng.shuffle(shuffled)
        picks.add(select(shuffled).chosen.id)

    assert picks == {"alpha"}


# --------------------------------------------------------------------------
# select — exclusions and their reasons
# --------------------------------------------------------------------------


def test_blocked_items_are_excluded_with_their_reason():
    selection = select([item("blocked", blocked=True, blocked_reason="waiting on #500")])

    assert selection.has_work is False
    assert reason_for(selection, "blocked") == "blocked: waiting on #500"


def test_blocked_without_a_reason_still_says_so():
    selection = select([item("blocked", blocked=True)])

    assert reason_for(selection, "blocked") == "blocked: no reason given"


def test_owner_gated_items_are_excluded():
    selection = select([item("gated", owner_gated=True)])

    assert selection.has_work is False
    assert "owner-gated" in reason_for(selection, "gated")


def test_high_risk_is_escalated_rather_than_implemented():
    selection = select([item("risky", risk="high")])

    assert selection.has_work is False
    assert "risk=high" in reason_for(selection, "risky")
    assert "escalate" in reason_for(selection, "risky")


@pytest.mark.parametrize("risk", sorted(ACTIONABLE_RISK))
def test_low_and_medium_risk_are_actionable(risk):
    selection = select([item("ok", risk=risk)])

    assert selection.has_work is True
    assert selection.chosen.risk == risk


def test_below_floor_items_are_excluded_and_name_the_floor():
    selection = select([item("meh", value=0.1, effort=0.9, confidence=0.5)])

    assert selection.has_work is False
    reason = reason_for(selection, "meh")
    assert "below floor" in reason
    assert f"{VALUE_FLOOR:.2f}" in reason


def test_an_item_exactly_at_the_floor_is_actionable():
    """`score < floor` excludes; equality must not."""
    at_floor = item("edge", value=VALUE_FLOOR, confidence=1.0, effort=1.0 - EPSILON)

    assert at_floor.score == pytest.approx(VALUE_FLOOR)
    assert select([at_floor]).has_work is True


def test_a_custom_floor_is_honoured():
    modest = item("modest", value=0.3, effort=0.4, confidence=0.5)

    assert select([modest], floor=VALUE_FLOOR).has_work is False
    assert select([modest], floor=0.1).has_work is True


# --- precedence: the reported reason must be the most decisive one -----------


def test_blocked_beats_owner_gated_in_the_reported_reason():
    both = item("both", blocked=True, blocked_reason="dep", owner_gated=True)

    assert reason_for(select([both]), "both").startswith("blocked")


def test_owner_gated_beats_risk():
    both = item("both", owner_gated=True, risk="high")

    assert "owner-gated" in reason_for(select([both]), "both")


def test_risk_beats_the_floor():
    both = item("both", risk="high", value=0.0)

    assert "risk=high" in reason_for(select([both]), "both")


def test_full_precedence_chain_reports_only_the_first_reason():
    everything = item(
        "everything",
        blocked=True,
        blocked_reason="upstream",
        owner_gated=True,
        risk="high",
        value=0.0,
    )
    selection = select([everything])

    reason = reason_for(selection, "everything")
    assert reason == "blocked: upstream"
    assert "owner-gated" not in reason
    assert "risk=" not in reason
    assert "below floor" not in reason


# --- exclude_ids and the frontend pause --------------------------------------


def test_exclude_ids_skips_already_attempted_items_with_the_right_reason():
    selection = select([item("tried"), item("fresh")], exclude_ids={"tried"})

    assert selection.chosen.id == "fresh"
    assert reason_for(selection, "tried") == "already attempted this cycle"


def test_exclude_ids_can_empty_the_actionable_set():
    selection = select([item("tried")], exclude_ids={"tried"})

    assert selection.has_work is False


def test_exclude_ids_wins_over_every_other_reason():
    """It is checked first, so an excluded blocked item still reads 'attempted'."""
    selection = select([item("tried", blocked=True)], exclude_ids={"tried"})

    assert reason_for(selection, "tried") == "already attempted this cycle"


def test_allow_frontend_false_skips_frontend_work():
    selection = select(
        [item("ui", touches_frontend=True), item("api")],
        allow_frontend=False,
    )

    assert selection.chosen.id == "api"
    assert "frontend work paused" in reason_for(selection, "ui")
    assert "deploy quota" in reason_for(selection, "ui")


def test_allow_frontend_false_does_not_skip_backend_work():
    selection = select([item("api", touches_frontend=False)], allow_frontend=False)

    assert selection.has_work is True
    assert selection.skipped == []


def test_allow_frontend_true_is_the_default():
    assert select([item("ui", touches_frontend=True)]).chosen.id == "ui"


# --------------------------------------------------------------------------
# select — the idle answer
# --------------------------------------------------------------------------


def test_no_candidates_at_all_is_idle_with_an_explanation():
    selection = select([])

    assert selection.has_work is False
    assert selection.chosen is None
    assert selection.idle_reason == "no candidate work items were supplied"


def test_idle_reason_counts_the_candidates_and_names_the_floor():
    selection = select([item("a", value=0.0), item("b", value=0.0)])

    assert selection.has_work is False
    assert selection.idle_reason
    assert "2 candidates" in selection.idle_reason
    assert f"{VALUE_FLOOR:.2f}" in selection.idle_reason


def test_idle_selection_still_reports_every_skip():
    selection = select([item("a", blocked=True), item("b", owner_gated=True)])

    assert [skipped_id for skipped_id, _ in selection.skipped] == ["a", "b"]


# --------------------------------------------------------------------------
# select — the dry threshold
# --------------------------------------------------------------------------


def test_first_idle_round_is_not_yet_dry():
    selection = select([item("a", value=0.0)], idle_rounds=0)

    assert DRY_AFTER_IDLE_ROUNDS == 2
    assert selection.dry is False
    assert "this round" in selection.idle_reason


def test_dry_once_idle_rounds_plus_one_reaches_the_threshold():
    selection = select([item("a", value=0.0)], idle_rounds=DRY_AFTER_IDLE_ROUNDS - 1)

    assert selection.dry is True
    assert "dry" in selection.idle_reason
    assert "stop scheduling" in selection.idle_reason


def test_dry_stays_true_past_the_threshold():
    assert select([item("a", value=0.0)], idle_rounds=9).dry is True


def test_a_round_that_finds_work_is_never_dry():
    selection = select([item("good")], idle_rounds=99)

    assert selection.has_work is True
    assert selection.dry is False


# --------------------------------------------------------------------------
# Selection.to_dict
# --------------------------------------------------------------------------


def test_to_dict_shape_when_work_was_chosen():
    chosen = item(
        "gh-7",
        title="Add lead enrichment column",
        value=0.8,
        confidence=0.5,
        effort=0.2,
        risk="medium",
        url="https://github.com/o/r/issues/7",
        touches_frontend=True,
    )
    payload = select([chosen, item("skipped", blocked=True)]).to_dict()

    assert payload == {
        "chosen": {
            "id": "gh-7",
            "title": "Add lead enrichment column",
            "score": round(chosen.score, 3),
            "risk": "medium",
            "url": "https://github.com/o/r/issues/7",
            "touches_frontend": True,
        },
        "skipped": [{"id": "skipped", "reason": "blocked: no reason given"}],
        "idle_reason": "",
        "dry": False,
    }


def test_to_dict_chosen_is_none_when_idle():
    payload = select([item("a", value=0.0)], idle_rounds=1).to_dict()

    assert payload["chosen"] is None
    assert payload["dry"] is True
    assert payload["idle_reason"]
    assert payload["skipped"] == [
        {"id": "a", "reason": f"score 0.00 below floor {VALUE_FLOOR:.2f}"}
    ]


def test_to_dict_is_json_serializable():
    payload = select([item("a"), item("b", blocked=True)]).to_dict()

    assert json.loads(json.dumps(payload)) == payload


# --------------------------------------------------------------------------
# load_items
# --------------------------------------------------------------------------


def write_backlog(tmp_path, payload, name="backlog.json"):
    path = tmp_path / name
    path.write_text(json.dumps(payload))
    return path


def test_load_items_accepts_a_bare_list(tmp_path):
    path = write_backlog(tmp_path, [{"id": "a", "title": "A"}, {"id": "b", "title": "B"}])

    items = load_items(path)

    assert [i.id for i in items] == ["a", "b"]
    assert items[0].title == "A"


def test_load_items_accepts_an_items_envelope(tmp_path):
    path = write_backlog(
        tmp_path,
        {
            "generated_at": "2026-07-27",
            "items": [{"id": "a", "title": "A"}, {"id": "b", "title": "B"}],
        },
    )

    assert [i.id for i in load_items(path)] == ["a", "b"]


def test_load_items_round_trips_a_full_item(tmp_path):
    original = {
        "id": "gh-99",
        "title": "Ship it",
        "value": 0.9,
        "effort": 0.3,
        "confidence": 0.8,
        "risk": "medium",
        "labels": ["backend", "loop"],
        "blocked": False,
        "blocked_reason": "",
        "owner_gated": False,
        "touches_frontend": True,
        "url": "https://github.com/o/r/issues/99",
    }
    path = write_backlog(tmp_path, {"items": [original]})

    loaded = load_items(path)[0]

    assert loaded == WorkItem.from_dict(original)
    assert loaded.labels == ("backend", "loop")
    assert loaded.touches_frontend is True


def test_load_items_accepts_a_string_path(tmp_path):
    path = write_backlog(tmp_path, [{"id": "a", "title": "A"}])

    assert [i.id for i in load_items(str(path))] == ["a"]


def test_load_items_of_an_empty_list_is_empty(tmp_path):
    assert load_items(write_backlog(tmp_path, [])) == []


def test_load_items_rejects_a_non_list_envelope(tmp_path):
    path = write_backlog(tmp_path, {"items": {"a": 1}})

    with pytest.raises(ValueError) as exc:
        load_items(path)

    assert "must be a list" in str(exc.value)
    assert "dict" in str(exc.value)


def test_load_items_rejects_a_bare_non_list_document(tmp_path):
    path = write_backlog(tmp_path, "not a backlog")

    with pytest.raises(ValueError) as exc:
        load_items(path)

    assert "must be a list" in str(exc.value)


def test_load_items_propagates_a_missing_id(tmp_path):
    path = write_backlog(tmp_path, [{"title": "no id"}])

    with pytest.raises(ValueError) as exc:
        load_items(path)

    assert "needs an id" in str(exc.value)


def test_load_items_feeds_select_directly(tmp_path):
    path = write_backlog(
        tmp_path,
        {
            "items": [
                {
                    "id": "cheap",
                    "title": "Cheap",
                    "value": 0.5,
                    "confidence": 0.9,
                    "effort": 0.1,
                },
                {
                    "id": "pricey",
                    "title": "Pricey",
                    "value": 1.0,
                    "confidence": 0.9,
                    "effort": 1.0,
                },
                {
                    "id": "gated",
                    "title": "Gated",
                    "value": 1.0,
                    "confidence": 1.0,
                    "owner_gated": True,
                },
            ]
        },
    )

    selection = select(load_items(path))

    assert selection.chosen.id == "cheap"
    assert reason_for(selection, "gated").startswith("owner-gated")
