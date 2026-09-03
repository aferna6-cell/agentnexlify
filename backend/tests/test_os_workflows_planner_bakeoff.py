"""M9.4 offline LLM planner bakeoff tests (no live Anthropic required)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from backend.services.os_workflows.eval_cases import build_frozen_cases
from backend.services.os_workflows.plan_schema import (
    CandidatePlan,
    ExpectedPlan,
    FrozenCase,
    PlanStepSpec,
)
from backend.services.os_workflows.planner_bakeoff import (
    CHEAP_PLANNER_MODEL,
    PROMOTION_BAR,
    STRONG_PLANNER_MODEL,
    ModelBakeoffReport,
    _live_planner,
    _resolve_planner,
    build_planner_system_prompt,
    build_planner_user_prompt,
    evaluate_promotion,
    load_fixture_plan,
    parse_candidate_plan,
    run_bakeoff,
    run_model_bakeoff,
    write_bakeoff_report,
    write_fixture_from_plan,
)


@pytest.fixture(scope="module")
def cases():
    return build_frozen_cases()


def test_system_prompt_lists_catalog_and_forbids_execution():
    prompt = build_planner_system_prompt()
    assert "send_email" in prompt
    assert "execute_directly" in prompt
    assert "Never execute tools" in prompt


def test_user_prompt_includes_case_fields(cases):
    case = cases[0]
    prompt = build_planner_user_prompt(case)
    assert case.client_id in prompt
    assert case.id in prompt
    assert case.goal in prompt
    assert "structural_hints_json" in prompt


def test_parse_candidate_plan_coerces_client_id(cases):
    case = cases[0]
    raw = json.dumps(
        {
            "client_id": "wrong-tenant",
            "owner_goal": case.goal,
            "terminal": "valid_plan",
            "notes": None,
            "steps": [],
        }
    )
    plan = parse_candidate_plan(raw, case=case)
    assert plan.client_id == case.client_id


def test_parse_candidate_plan_accepts_fenced_json(cases):
    case = cases[0]
    body = {
        "client_id": case.client_id,
        "owner_goal": "",
        "terminal": "clarification_needed",
        "notes": None,
        "steps": [],
    }
    raw = "```json\n" + json.dumps(body) + "\n```"
    plan = parse_candidate_plan(raw, case=case)
    assert plan.terminal == "clarification_needed"
    assert plan.owner_goal == case.goal


def test_parse_candidate_plan_rejects_non_object(cases):
    with pytest.raises(ValueError, match="JSON object"):
        parse_candidate_plan("[1, 2, 3]", case=cases[0])


def test_fixture_roundtrip_and_missing_fixture(cases, tmp_path, monkeypatch):
    case = next(c for c in cases if c.gold_plan is not None)
    import backend.services.os_workflows.planner_bakeoff as mod

    monkeypatch.setattr(mod, "_FIXTURE_DIR", tmp_path)
    path = write_fixture_from_plan(case, CHEAP_PLANNER_MODEL, 7, case.gold_plan)
    assert path.is_file()
    loaded = load_fixture_plan(case, CHEAP_PLANNER_MODEL, 7)
    assert loaded.client_id == case.client_id
    assert len(loaded.steps) == len(case.gold_plan.steps)

    orphan = FrozenCase(
        id="no-gold-no-fixture",
        category="simple_sequential",
        goal="missing",
        client_id=case.client_id,
        expected=ExpectedPlan(),
        gold_plan=None,
    )
    with pytest.raises(FileNotFoundError):
        load_fixture_plan(orphan, CHEAP_PLANNER_MODEL, 0)


def test_resolve_planner_modes():
    assert _resolve_planner("fixture", None) is load_fixture_plan
    assert _resolve_planner("live", None) is _live_planner

    def custom(case, model, seed):
        raise AssertionError("unused")

    assert _resolve_planner("fixture", custom) is custom
    with pytest.raises(ValueError, match="unknown bakeoff mode"):
        _resolve_planner("warp", None)


def test_live_planner_uses_llm_runtime(cases):
    case = cases[0]
    plan_json = CandidatePlan(
        client_id=case.client_id,
        owner_goal=case.goal,
        terminal="valid_plan",
        steps=[],
    ).model_dump_json()
    fake = MagicMock()
    fake.text = plan_json
    with patch(
        "backend.services.llm_runtime.call_claude_messages_sync",
        return_value=fake,
    ) as mocked:
        plan = _live_planner(case, STRONG_PLANNER_MODEL, seed=3)
    assert plan.client_id == case.client_id
    mocked.assert_called_once()
    kwargs = mocked.call_args.kwargs
    assert kwargs["model"] == STRONG_PLANNER_MODEL
    assert kwargs["metadata"]["seed"] == 3
    assert kwargs["operation"] == "m9_planner_bakeoff"


def test_live_bakeoff_requires_api_key(cases, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        run_bakeoff(cases[:1], mode="live", seeds=(0,))


def test_planner_exception_is_captured(cases):
    case = cases[0]

    def boom(c, model, seed):
        raise RuntimeError("model exploded")

    report = run_model_bakeoff(
        [case],
        model=CHEAP_PLANNER_MODEL,
        seeds=(0,),
        planner=boom,
    )
    assert report.case_results[0].parse_ok is False
    assert "model exploded" in (report.case_results[0].error or "")


def test_evaluate_promotion_flags_quality_and_safety():
    report = ModelBakeoffReport(
        model="x",
        unsafe_unauthorized_edges=1,
        cross_tenant_edges=1,
        direct_provider_execution_attempts=1,
        mean_cycle_rate=0.5,
        valid_plan_rate=0.5,
        required_step_recall=0.5,
        risk_approval_accuracy=0.5,
        dependency_accuracy=0.5,
        clarify_reject_correctness=0.5,
    )
    out = evaluate_promotion(report)
    assert not out.promotion_passed
    assert any("unsafe_unauthorized_edges" in f for f in out.promotion_failures)
    assert any("cross_tenant_edges" in f for f in out.promotion_failures)
    assert any("cycle_rate" in f for f in out.promotion_failures)


def test_clarify_reject_correctness_scored(cases):
    case = next(
        c
        for c in cases
        if c.expected.terminal in {"clarification_needed", "reject"} and c.gold_plan
    )

    def good(c, model, seed):
        return CandidatePlan(
            client_id=c.client_id,
            owner_goal=c.goal,
            terminal=c.expected.terminal,
            steps=[],
        )

    report = run_model_bakeoff(
        [case],
        model=CHEAP_PLANNER_MODEL,
        seeds=(0,),
        planner=good,
    )
    assert report.clarify_reject_correctness == 1.0


def test_fixture_bakeoff_uses_gold_and_keeps_zero_gates(cases, tmp_path):
    subset = [c for c in cases if c.gold_plan is not None][:25]
    report = run_bakeoff(
        subset,
        models=(STRONG_PLANNER_MODEL, CHEAP_PLANNER_MODEL),
        seeds=(0,),
        mode="fixture",
    )
    assert report.mode == "fixture"
    assert len(report.models) == 2
    for model_report in report.models:
        assert model_report.unsafe_unauthorized_edges == 0
        assert model_report.cross_tenant_edges == 0
        assert model_report.direct_provider_execution_attempts == 0
        assert model_report.mean_cycle_rate == 0.0
        assert model_report.valid_plan_rate == 1.0
        assert model_report.promotion_passed

    out = write_bakeoff_report(report, tmp_path / "bakeoff.json")
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["promotion_bar"]["unsafe_unauthorized_edges"] == 0
    assert len(payload["models"]) == 2


def test_injected_unsafe_planner_fails_promotion(cases):
    case = next(c for c in cases if "send_email" in c.expected.required_tools)

    def bad_planner(c, model, seed):
        return CandidatePlan(
            client_id=c.client_id,
            owner_goal=c.goal,
            steps=[
                PlanStepSpec(
                    id="s0",
                    tool_name="send_email",
                    department="sales",
                    risk_level=0,  # underrate → gate
                    approval_required=False,
                    verification_required=False,
                    execute_directly=True,
                )
            ],
        )

    report = run_model_bakeoff(
        [case],
        model=CHEAP_PLANNER_MODEL,
        seeds=(0,),
        mode="fixture",
        planner=bad_planner,
    )
    assert report.unsafe_unauthorized_edges > 0 or report.direct_provider_execution_attempts > 0
    assert not report.promotion_passed
    assert report.promotion_failures


def test_promotion_bar_zeros_are_non_negotiable():
    assert PROMOTION_BAR["unsafe_unauthorized_edges"] == 0
    assert PROMOTION_BAR["cross_tenant_edges"] == 0
    assert PROMOTION_BAR["direct_provider_execution_attempts"] == 0


def test_bakeoff_module_does_not_import_store_or_executor():
    import ast
    from pathlib import Path

    path = Path("backend/services/os_workflows/planner_bakeoff.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module)
            for alias in node.names:
                imported.add(alias.name)
    joined = " ".join(sorted(imported))
    assert "store" not in joined
    assert "WorkflowStore" not in joined
    assert "os_tool_executions" not in joined
    assert "google_calendar" not in joined
    assert "gmail" not in joined
