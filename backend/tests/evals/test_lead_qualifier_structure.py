"""Offline structural checks for the Lead Qualifier golden eval.

Unlike ``test_lead_qualifier_golden.py`` (which is skip-gated behind
``RUN_LEAD_QUALIFIER_EVAL=1`` and burns live Anthropic credits), these tests
run on every PR. They are deterministic, free, and catch the two most common
ways the eval silently rots:

1. The golden dataset drifts out of the shape the live harness expects.
2. A qualifier symbol the harness imports gets renamed or removed.

Wired into CI via ``.github/workflows/lead-qualifier-eval.yml`` so a PR that
touches the qualifier or the rubrics fails fast instead of discovering the
breakage on the Monday cron run.
"""

import json
from pathlib import Path

GOLDEN_PATH = Path(__file__).parent / "lead_qualifier_golden.json"

REQUIRED_EXAMPLE_KEYS = {"id", "input", "expected"}
REQUIRED_INPUT_KEYS = {"lead", "tenant"}
REQUIRED_EXPECTED_KEYS = {"recommendation", "intent_score_range", "fit_score_range"}


def _load_golden() -> dict:
    return json.loads(GOLDEN_PATH.read_text())


def test_golden_dataset_parses_and_has_examples() -> None:
    data = _load_golden()
    assert "examples" in data, "golden dataset missing top-level 'examples'"
    assert isinstance(data["examples"], list)
    assert len(data["examples"]) > 0, "golden dataset has no examples"


def test_golden_examples_have_required_shape() -> None:
    data = _load_golden()
    seen_ids: set[str] = set()

    for i, ex in enumerate(data["examples"]):
        ctx = f"example[{i}]"
        missing = REQUIRED_EXAMPLE_KEYS - ex.keys()
        assert not missing, f"{ctx} missing keys: {missing}"

        ex_id = ex["id"]
        assert ex_id not in seen_ids, f"{ctx} duplicate id {ex_id!r}"
        seen_ids.add(ex_id)
        ctx = f"example {ex_id!r}"

        missing_input = REQUIRED_INPUT_KEYS - ex["input"].keys()
        assert not missing_input, f"{ctx} input missing keys: {missing_input}"

        expected = ex["expected"]
        missing_expected = REQUIRED_EXPECTED_KEYS - expected.keys()
        assert not missing_expected, f"{ctx} expected missing keys: {missing_expected}"

        for range_key in ("intent_score_range", "fit_score_range"):
            rng = expected[range_key]
            assert isinstance(rng, list) and len(rng) == 2, (
                f"{ctx} {range_key} must be a [lo, hi] pair, got {rng!r}"
            )
            lo, hi = rng
            assert lo <= hi, f"{ctx} {range_key} has lo > hi: {rng!r}"


def test_qualifier_harness_symbols_importable() -> None:
    """The live harness imports these inside ``_run_qualifier``. If any get
    renamed, the cron eval explodes at runtime — catch it here instead."""
    from backend.services.lead_qualification import (
        _build_prompt,
        _extract_json_from_reply,
        _extract_text_blocks,
        _normalize_qualification,
        _run_qualifier_session,
    )

    for symbol in (
        _build_prompt,
        _extract_json_from_reply,
        _extract_text_blocks,
        _normalize_qualification,
        _run_qualifier_session,
    ):
        assert callable(symbol)


def test_rubric_resolver_importable_and_total() -> None:
    """The qualifier moat: every business type resolves to a rubric, and an
    unknown type falls back to the default rather than raising."""
    from backend.services.qualification_rubrics import get_qualification_rubric

    default_rubric = get_qualification_rubric("some_unmapped_vertical_xyz")
    assert isinstance(default_rubric, str) and default_rubric.strip()

    hvac_rubric = get_qualification_rubric("hvac")
    assert isinstance(hvac_rubric, str) and hvac_rubric.strip()
