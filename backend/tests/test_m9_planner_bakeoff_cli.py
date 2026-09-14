from types import SimpleNamespace

from scripts.run_m9_planner_bakeoff import _live_exit_code


def _report(*promotion_results: bool | None) -> SimpleNamespace:
    return SimpleNamespace(
        models=[
            SimpleNamespace(promotion_passed=promotion_passed)
            for promotion_passed in promotion_results
        ]
    )


def test_live_exit_code_succeeds_only_when_all_models_promote() -> None:
    assert _live_exit_code(_report(True, True)) == 0


def test_live_exit_code_fails_on_quality_promotion_failure() -> None:
    assert _live_exit_code(_report(True, False)) == 1


def test_live_exit_code_fails_when_promotion_was_not_resolved() -> None:
    assert _live_exit_code(_report(None)) == 1
