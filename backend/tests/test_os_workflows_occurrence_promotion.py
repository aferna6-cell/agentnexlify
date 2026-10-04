"""Occurrence-safe M9.4 promotion gates. Offline only — no provider calls."""

import json
import time
from typing import List, Sequence
from unittest.mock import patch

from backend.services.os_workflows.plan_eval import (
    CUSTOMER_COMMUNICATION_TOOLS,
    MATERIAL_DEPARTMENT_MIN_SUPPORT,
    MATERIAL_DEPARTMENTS,
    score_department_integrity,
    score_plan,
    score_required_verification,
)
from backend.services.os_workflows.plan_schema import (
    CandidatePlan,
    ExpectedPlan,
    FrozenCase,
    PlanStepSpec,
)
from backend.services.os_workflows.planner_bakeoff import (
    MISS_OK,
    PROMOTION_BAR,
    BakeoffCaseResult,
    ModelBakeoffReport,
    PlannerAttempt,
    _integrity_metrics,
    _provenance_digest,
    evaluate_promotion,
    freeze_promotion_provenance,
    run_model_bakeoff,
)
from backend.services.os_workflows.tool_catalog import (
    TOOL_CATALOG,
    tool_verification_required,
)

_CLIENT = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
_N = 100


def _zero_attempt(plan: CandidatePlan) -> PlannerAttempt:
    return PlannerAttempt(
        raw_text=plan.model_dump_json(),
        evidence_type="live_output",
        input_tokens=0,
        output_tokens=0,
        total_tokens=0,
        cost_usd=0.0,
    )


def _duplicate_case() -> FrozenCase:
    return FrozenCase(
        id="dup-get-customer",
        category="verification_requirements",
        goal="read the customer twice",
        client_id=_CLIENT,
        expected=ExpectedPlan(
            departments=["admin_records"],
            required_tools=["get_customer", "get_customer"],
            allowed_tools=["get_customer"],
            verification_required_tools=["get_customer", "get_customer"],
            max_steps=4,
            terminal="valid_plan",
        ),
    )


def _duplicate_plan(case: FrozenCase) -> CandidatePlan:
    return CandidatePlan(
        client_id=case.client_id,
        owner_goal=case.goal,
        terminal="valid_plan",
        steps=[
            PlanStepSpec(
                id="s0",
                tool_name="get_customer",
                department="admin_records",
                risk_level=0,
                approval_required=False,
                verification_required=False,
            ),
            PlanStepSpec(
                id="s1",
                tool_name="get_customer",
                department="admin_records",
                risk_level=0,
                approval_required=False,
                verification_required=True,
            ),
        ],
    )


def _lookup_case(tool: str, *, case_id: str) -> FrozenCase:
    meta = TOOL_CATALOG[tool]
    return FrozenCase(
        id=case_id,
        category="verification_requirements",
        goal=f"use {tool}",
        client_id=_CLIENT,
        expected=ExpectedPlan(
            departments=[meta["department"]] if meta["department"] else [],
            required_tools=[tool],
            allowed_tools=[tool],
            verification_required_tools=(
                [tool] if meta["verification_required"] else []
            ),
            max_steps=3,
            terminal="valid_plan",
        ),
    )


def _catalog_plan(case: FrozenCase, tool: str, *, department: str | None = None) -> CandidatePlan:
    meta = TOOL_CATALOG[tool]
    return CandidatePlan(
        client_id=case.client_id,
        owner_goal=case.goal,
        terminal="valid_plan",
        steps=[
            PlanStepSpec(
                id="s0",
                tool_name=tool,
                department=meta["department"] if department is None else department,
                risk_level=meta["risk_level"],
                approval_required=bool(meta["requires_approval"]),
                verification_required=bool(meta["verification_required"]),
            )
        ],
    )


def _passing_report(**overrides) -> ModelBakeoffReport:
    report = ModelBakeoffReport(
        model="offline-probe",
        attempts=1,
        parse_success_count=1,
        parse_success_rate=1.0,
        valid_plan_rate=1.0,
        required_step_recall=1.0,
        risk_approval_accuracy=1.0,
        dependency_accuracy=1.0,
        clarify_reject_correctness=1.0,
        required_verification_recall=1.0,
        verification_precision=1.0,
        unnecessary_verification_rate=0.0,
        department_accuracy=1.0,
        missing_required_verification_count=0,
        harness_scoring_failure_count=0,
    )
    for key, value in overrides.items():
        setattr(report, key, value)
    return report


def test_material_departments_and_support_are_explicit():
    derived = {
        meta["department"]
        for meta in TOOL_CATALOG.values()
        if meta.get("department")
    }
    assert MATERIAL_DEPARTMENTS == frozenset({"admin_records", "sales"})
    assert MATERIAL_DEPARTMENTS == frozenset(derived)
    assert CUSTOMER_COMMUNICATION_TOOLS == frozenset({"send_email"})
    assert MATERIAL_DEPARTMENT_MIN_SUPPORT == 20
    assert PROMOTION_BAR["material_department_accuracy"] == 0.95
    assert PROMOTION_BAR["department_accuracy"] == 0.98
    assert PROMOTION_BAR["mutation_department_accuracy"] == 1.0
    assert PROMOTION_BAR["customer_communication_department_accuracy"] == 1.0
    assert PROMOTION_BAR["required_verification_recall"] == 1.0
    assert PROMOTION_BAR["verification_precision"] == 0.98
    assert PROMOTION_BAR["unnecessary_verification_rate"] == 0.02
    assert PROMOTION_BAR["missing_required_verification_count"] == 0
    assert PROMOTION_BAR["harness_scoring_failure_count"] == 0


def test_material_department_gate_applies_only_at_frozen_min_support():
    below = evaluate_promotion(
        _passing_report(
            material_department_support={"admin_records": 19},
            material_department_accuracy={"admin_records": 0.0},
        )
    )
    assert below.promotion_passed is True
    assert below.promotion_failures == []

    at_floor = evaluate_promotion(
        _passing_report(
            material_department_support={"sales": 20},
            material_department_accuracy={"sales": 0.95},
        )
    )
    assert at_floor.promotion_passed is True

    under_floor = evaluate_promotion(
        _passing_report(
            material_department_support={"sales": 20},
            material_department_accuracy={"sales": 0.90},
        )
    )
    assert under_floor.promotion_passed is False
    assert under_floor.promotion_failures == [
        "material_department_accuracy[sales]=0.9000 < 0.95 (support=20)"
    ]


def test_recall_gate_fires_when_missing_count_is_zero():
    report = evaluate_promotion(_passing_report(required_verification_recall=0.5))
    assert report.promotion_passed is False
    assert report.promotion_failures == ["required_verification_recall=0.5000 < 1.0"]


def test_n100_duplicate_occurrence_fails_only_on_missing_verification():
    """Frozen N=100 repeat of two get_customer occurrences, first flag omitted.

    Per-attempt ground truth stays denominator=2, verified=1, missing=1,
    recall=.5. The absolute counter sums every omitted occurrence (100) so
    the miss cannot collapse or average away. Provider usage stays 0/0/0/$0.
    """
    case = _duplicate_case()
    plan = _duplicate_plan(case)

    def planner(c, model, seed, _plan=plan):
        del c, model, seed
        return _zero_attempt(_plan)

    report = run_model_bakeoff(
        [case],
        model="offline-probe",
        repetitions=tuple(range(_N)),
        mode="live",
        planner=planner,
    )
    assert report.attempts == _N
    assert report.harness_scoring_failure_count == 0
    assert report.promotion_evaluated is False
    assert report.promotion_passed is None
    assert report.promotion_failures == []
    assert report.promotion_unevaluated_reasons == ["optional_support"]
    assert report.required_verification_recall == 0.5
    assert report.required_verification_support == 200
    assert report.optional_verification_support == 0
    assert report.verified_required_verification_count == 100
    assert report.missing_required_verification_count == 100
    assert report.verification_precision == 1.0
    assert report.unnecessary_verification_rate is None
    assert report.required_step_recall == 1.0
    assert report.input_tokens_total == 0
    assert report.output_tokens_total == 0
    assert report.total_tokens_total == 0
    assert report.estimated_total_cost_usd == 0.0
    for row in report.case_results:
        assert row.score is not None
        assert row.score.required_verification_occurrences == 2
        assert row.score.verified_required_verification_count == 1
        assert row.score.missing_required_verification_count == 1
        assert row.score.required_verification_recall == 0.5
        assert row.score.verification_placement_accuracy == 0.5
        assert row.score.optional_verification_support == 0
        assert row.score.unnecessary_verification_rate is None
        assert row.input_tokens == 0
        assert row.output_tokens == 0
        assert row.cost_usd == 0.0


def test_fixture_provenance_of_duplicate_case_stays_unevaluated():
    case = _duplicate_case()
    plan = _duplicate_plan(case)

    def planner(c, model, seed, _plan=plan):
        del c, model, seed
        return _zero_attempt(_plan)

    report = run_model_bakeoff(
        [case],
        model="offline-probe",
        repetitions=(0,),
        mode="fixture",
        planner=planner,
    )
    assert report.promotion_evaluated is False
    assert report.promotion_passed is None
    assert report.promotion_failures == []
    assert report.promotion_unevaluated_reasons == ["fixture_provenance"]
    assert report.case_results[0].score.required_verification_recall == 0.5


def test_clean_control_without_required_support_stays_unevaluated():
    case = _lookup_case("get_customer", case_id="clean-get-customer")
    plan = _catalog_plan(case, "get_customer")

    def planner(c, model, seed, _plan=plan):
        del c, model, seed
        return _zero_attempt(_plan)

    report = run_model_bakeoff(
        [case],
        model="offline-probe",
        repetitions=(0,),
        mode="live",
        planner=planner,
    )
    assert report.promotion_evaluated is False
    assert report.promotion_passed is None
    assert report.promotion_failures == []
    assert report.promotion_unevaluated_reasons == ["required_support"]
    assert report.required_verification_support == 0
    assert report.optional_verification_support == 1
    assert report.verification_true_negatives == 1
    assert report.unnecessary_verification_rate == 0.0
    assert report.required_verification_recall is None
    assert report.input_tokens_total == 0
    assert report.output_tokens_total == 0
    assert report.total_tokens_total == 0
    assert report.estimated_total_cost_usd == 0.0


def _balanced_case() -> FrozenCase:
    return FrozenCase(
        id="balanced-get-customer",
        category="verification_requirements",
        goal="read the customer, then read it again",
        client_id=_CLIENT,
        expected=ExpectedPlan(
            departments=["admin_records"],
            required_tools=["get_customer", "get_customer"],
            allowed_tools=["get_customer"],
            verification_required_tools=["get_customer"],
            max_steps=4,
            terminal="valid_plan",
        ),
    )


def _balanced_plan(case: FrozenCase, *, optional_flag: bool) -> CandidatePlan:
    return CandidatePlan(
        client_id=case.client_id,
        owner_goal=case.goal,
        terminal="valid_plan",
        steps=[
            PlanStepSpec(
                id="s0",
                tool_name="get_customer",
                department="admin_records",
                risk_level=0,
                approval_required=False,
                verification_required=True,
            ),
            PlanStepSpec(
                id="s1",
                tool_name="get_customer",
                department="admin_records",
                risk_level=0,
                approval_required=False,
                verification_required=optional_flag,
            ),
        ],
    )


def test_optional_false_positive_is_not_diluted_by_required_support():
    """49 required hits must not dilute 1 optional false positive to 0.02."""
    case = FrozenCase(
        id="optional-fp",
        category="verification_requirements",
        goal="read the customer fifty times",
        client_id=_CLIENT,
        expected=ExpectedPlan(
            departments=["admin_records"],
            required_tools=["get_customer"] * 50,
            allowed_tools=["get_customer"],
            verification_required_tools=["get_customer"] * 49,
            max_steps=50,
            terminal="valid_plan",
        ),
    )
    plan = CandidatePlan(
        client_id=case.client_id,
        owner_goal=case.goal,
        terminal="valid_plan",
        steps=[
            PlanStepSpec(
                id=f"s{index}",
                tool_name="get_customer",
                department="admin_records",
                risk_level=0,
                approval_required=False,
                verification_required=True,
            )
            for index in range(50)
        ],
    )

    def planner(c, model, seed, _plan=plan):
        del c, model, seed
        return _zero_attempt(_plan)

    report = run_model_bakeoff(
        [case],
        model="offline-probe",
        repetitions=(0,),
        mode="live",
        planner=planner,
    )
    score = report.case_results[0].score
    assert score is not None
    assert score.verification_true_positives == 49
    assert score.verification_false_negatives == 0
    assert score.verification_false_positives == 1
    assert score.verification_true_negatives == 0
    assert score.required_verification_support == 49
    assert score.optional_verification_support == 1
    assert score.verification_positive_support == 50
    assert score.verification_precision == 49 / 50
    assert score.required_verification_recall == 1.0
    assert score.unnecessary_verification_rate == 1.0
    assert report.promotion_evaluated is True
    assert report.promotion_passed is False
    assert report.promotion_failures == [
        "unnecessary_verification_rate=1.0000 > 0.02"
    ]
    assert report.input_tokens_total == 0
    assert report.output_tokens_total == 0
    assert report.total_tokens_total == 0
    assert report.estimated_total_cost_usd == 0.0
    payload = report.case_results[0].to_dict()
    assert payload["verification_true_positives"] == 49
    assert payload["verification_false_positives"] == 1
    assert payload["optional_verification_support"] == 1
    assert payload["unnecessary_verification_rate"] == 1.0


def test_clean_optional_true_negative_promotes():
    case = _balanced_case()
    plan = _balanced_plan(case, optional_flag=False)

    def planner(c, model, seed, _plan=plan):
        del c, model, seed
        return _zero_attempt(_plan)

    report = run_model_bakeoff(
        [case],
        model="offline-probe",
        repetitions=(0,),
        mode="live",
        planner=planner,
    )
    score = report.case_results[0].score
    assert score is not None
    assert score.verification_true_positives == 1
    assert score.verification_false_negatives == 0
    assert score.verification_false_positives == 0
    assert score.verification_true_negatives == 1
    assert score.unnecessary_verification_rate == 0.0
    assert score.verification_precision == 1.0
    assert score.required_verification_recall == 1.0
    assert report.promotion_evaluated is True
    assert report.promotion_passed is True
    assert report.promotion_failures == []
    assert report.promotion_unevaluated_reasons == []
    assert report.estimated_total_cost_usd == 0.0


def test_omitted_optional_occurrence_keeps_expected_support():
    case = _balanced_case()
    plan = CandidatePlan(
        client_id=case.client_id,
        owner_goal=case.goal,
        terminal="valid_plan",
        steps=[
            PlanStepSpec(
                id="s0",
                tool_name="get_customer",
                department="admin_records",
                risk_level=0,
                verification_required=True,
            )
        ],
    )
    score = score_plan(case, plan, mode="gold")
    assert score.required_verification_support == 1
    assert score.verification_true_positives == 1
    assert score.optional_verification_support == 1
    assert score.verification_false_positives == 1
    assert score.verification_true_negatives == 0
    assert score.unnecessary_verification_rate == 1.0
    assert score.department_checks == 2
    assert score.department_hits == 1
    assert score.department_accuracy == 0.5


def test_one_unscored_attempt_cannot_promote():
    case = _balanced_case()
    plan = _balanced_plan(case, optional_flag=False)
    calls = {"n": 0}

    def planner(c, model, seed, _plan=plan):
        del c, model, seed
        return _zero_attempt(_plan)

    def flaky(case, plan, mode="gold"):
        calls["n"] += 1
        if calls["n"] == 50:
            raise RuntimeError("harness scoring failed")
        return score_plan(case, plan, mode=mode)

    with patch(
        "backend.services.os_workflows.planner_bakeoff.score_plan",
        side_effect=flaky,
    ):
        report = run_model_bakeoff(
            [case],
            model="offline-probe",
            repetitions=tuple(range(50)),
            mode="live",
            planner=planner,
        )
    assert report.attempts == 50
    assert report.harness_scoring_failure_count == 1
    assert report.parse_success_rate == 1.0
    assert report.required_verification_support == 50
    assert report.optional_verification_support == 50
    assert report.verification_true_positives == 49
    assert report.missing_required_verification_count == 1
    assert report.verification_false_positives == 1
    assert report.verification_true_negatives == 49
    assert report.required_verification_recall == 49 / 50
    assert report.promotion_evaluated is True
    assert report.promotion_passed is False
    assert any(
        failure.startswith("harness_scoring_failure_count=1")
        for failure in report.promotion_failures
    )
    unscored = [row for row in report.case_results if row.score is None]
    assert len(unscored) == 1
    assert unscored[0].parse_ok is True
    assert report.input_tokens_total == 0
    assert report.estimated_total_cost_usd == 0.0


def test_one_wrong_department_mutation_cannot_promote():
    meta = TOOL_CATALOG["update_customer"]
    case = FrozenCase(
        id="mutation-dept",
        category="verification_requirements",
        goal="update then read",
        client_id=_CLIENT,
        expected=ExpectedPlan(
            departments=["admin_records"],
            required_tools=["update_customer", "get_customer"],
            allowed_tools=["update_customer", "get_customer"],
            verification_required_tools=["update_customer"],
            max_steps=4,
            terminal="valid_plan",
        ),
    )

    def _steps(department: str) -> CandidatePlan:
        return CandidatePlan(
            client_id=case.client_id,
            owner_goal=case.goal,
            terminal="valid_plan",
            steps=[
                PlanStepSpec(
                    id="s0",
                    tool_name="update_customer",
                    department=department,
                    risk_level=meta["risk_level"],
                    approval_required=bool(meta["requires_approval"]),
                    verification_required=True,
                ),
                PlanStepSpec(
                    id="s1",
                    tool_name="get_customer",
                    department="admin_records",
                    risk_level=0,
                    approval_required=False,
                    verification_required=False,
                ),
            ],
        )

    good = _steps("admin_records")
    bad = _steps("sales")

    def planner(c, model, seed, _good=good, _bad=bad):
        del c, model
        return _zero_attempt(_bad if seed == 0 else _good)

    report = run_model_bakeoff(
        [case],
        model="offline-probe",
        repetitions=tuple(range(61)),
        mode="live",
        planner=planner,
    )
    assert report.department_accuracy >= 0.98
    assert report.material_department_support["admin_records"] == 122
    assert report.material_department_accuracy["admin_records"] >= 0.95
    assert report.mutation_department_checks == 61
    assert report.mutation_department_hits == 60
    assert report.mutation_department_accuracy != 1.0
    assert report.customer_communication_department_checks == 0
    assert report.missing_required_verification_count == 0
    assert report.harness_scoring_failure_count == 0
    assert report.promotion_evaluated is True
    assert report.promotion_passed is False
    assert report.promotion_failures == [
        f"mutation_department_accuracy={report.mutation_department_accuracy:.4f} < 1.0"
    ]
    assert report.estimated_total_cost_usd == 0.0


def test_parse_failure_stays_in_verification_denominator():
    case = _balanced_case()
    plan = _balanced_plan(case, optional_flag=False)

    def planner(c, model, seed, _plan=plan):
        del c, model
        if seed == 0:
            return PlannerAttempt(
                raw_text="not-json",
                evidence_type="live_output",
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                cost_usd=0.0,
            )
        return _zero_attempt(_plan)

    report = run_model_bakeoff(
        [case],
        model="offline-probe",
        repetitions=(0, 1),
        mode="live",
        planner=planner,
    )
    assert report.attempts == 2
    assert report.required_verification_support == 2
    assert report.optional_verification_support == 2
    assert report.verification_true_positives == 1
    assert report.missing_required_verification_count == 1
    assert report.verification_true_negatives == 1
    assert report.verification_false_positives == 1
    assert report.required_verification_recall == 0.5
    assert report.unnecessary_verification_rate == 0.5
    assert report.promotion_passed is False
    assert any(row.parse_ok is False for row in report.case_results)
    assert len(report.case_results) == 2


def test_provenance_row_order_support_and_stratum_drift_stay_unevaluated():
    case = _balanced_case()
    plan = _balanced_plan(case, optional_flag=False)

    def planner(c, model, seed, _plan=plan):
        del c, model, seed
        return _zero_attempt(_plan)

    report = run_model_bakeoff(
        [case],
        model="offline-probe",
        repetitions=(0, 1),
        mode="live",
        planner=planner,
    )
    assert report.promotion_passed is True

    from dataclasses import replace

    reordered = replace(report, case_results=list(reversed(report.case_results)))
    reordered_out = evaluate_promotion(reordered)
    assert reordered_out.promotion_evaluated is False
    assert reordered_out.promotion_passed is None
    assert reordered_out.promotion_failures == []
    assert "ordering" in reordered_out.promotion_unevaluated_reasons

    dropped = replace(report, case_results=report.case_results[:1])
    dropped_out = evaluate_promotion(dropped)
    assert dropped_out.promotion_passed is None
    assert "row_count" in dropped_out.promotion_unevaluated_reasons

    tampered_digest = dict(report.frozen_provenance)
    tampered_digest["digest"] = "0" * 64
    provenance_out = evaluate_promotion(
        replace(report, frozen_provenance=tampered_digest)
    )
    assert provenance_out.promotion_passed is None
    assert provenance_out.promotion_unevaluated_reasons == ["provenance"]

    support_payload = dict(report.frozen_provenance)
    support_payload["department_support"] = {"admin_records": 999}
    support_payload["digest"] = _provenance_digest(support_payload)
    support_out = evaluate_promotion(replace(report, frozen_provenance=support_payload))
    assert support_out.promotion_passed is None
    assert "support" in support_out.promotion_unevaluated_reasons
    assert "provenance" not in support_out.promotion_unevaluated_reasons

    stratum_payload = dict(report.frozen_provenance)
    stratum_payload["stratum"] = {"other": 2}
    stratum_payload["digest"] = _provenance_digest(stratum_payload)
    stratum_out = evaluate_promotion(replace(report, frozen_provenance=stratum_payload))
    assert stratum_out.promotion_passed is None
    assert "stratum" in stratum_out.promotion_unevaluated_reasons
    assert "provenance" not in stratum_out.promotion_unevaluated_reasons


def _legacy_verification_accuracy(plan: CandidatePlan, expected: ExpectedPlan) -> float:
    required = set(expected.verification_required_tools)
    for step in plan.steps:
        if step.tool_name and tool_verification_required(step.tool_name):
            required.add(step.tool_name)
    if not required:
        return 1.0
    by_tool = {
        step.tool_name: step
        for step in plan.steps
        if step.tool_name and step.tool_name in required
    }
    hits = 0
    for tool in required:
        step = by_tool.get(tool)
        if step is not None and step.verification_required:
            hits += 1
    return hits / len(required)


def _p95(samples: Sequence[float]) -> float:
    ordered = sorted(samples)
    index = int(round((len(ordered) - 1) * 0.95))
    return ordered[index]


def test_added_scorer_p95_latency_stays_within_2ms():
    case = _duplicate_case()
    plan = _duplicate_plan(case)
    plans = [plan] * _N
    expected = case.expected
    shared_score = score_plan(case, plan, mode="gold")
    rows = [
        BakeoffCaseResult(
            case_id=case.id,
            category=case.category,
            model="offline-probe",
            repetition=index,
            parse_ok=True,
            score=shared_score,
            latency_ms=0,
            evidence_type="live_output",
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            cost_usd=0.0,
            miss_class=MISS_OK,
        )
        for index in range(_N)
    ]
    warmup = 20
    iterations = 200

    def _new_slice(batch: List[CandidatePlan]) -> int:
        missing = 0
        for item in batch:
            scored = score_required_verification(item, expected)
            score_department_integrity(item, expected)
            missing += scored.missing
        _integrity_metrics(rows)
        return missing

    def _old_slice(batch: List[CandidatePlan]) -> float:
        total = 0.0
        for item in batch:
            total += _legacy_verification_accuracy(item, expected)
        return total

    for _ in range(warmup):
        _new_slice(plans)
        _old_slice(plans)

    deltas_ns = []
    new_ns = []
    old_ns = []
    for index in range(iterations):
        if index % 2 == 0:
            started = time.perf_counter_ns()
            _new_slice(plans)
            mid = time.perf_counter_ns()
            _old_slice(plans)
            finished = time.perf_counter_ns()
            new_elapsed = mid - started
            old_elapsed = finished - mid
        else:
            started = time.perf_counter_ns()
            _old_slice(plans)
            mid = time.perf_counter_ns()
            _new_slice(plans)
            finished = time.perf_counter_ns()
            old_elapsed = mid - started
            new_elapsed = finished - mid
        new_ns.append(new_elapsed)
        old_ns.append(old_elapsed)
        deltas_ns.append(new_elapsed - old_elapsed)

    p95_delta_ms = _p95(deltas_ns) / 1_000_000
    evidence = {
        "warmup": warmup,
        "iterations": iterations,
        "corpus_rows": _N,
        "p95_added_latency_ms": p95_delta_ms,
        "p95_new_ms": _p95(new_ns) / 1_000_000,
        "p95_old_ms": _p95(old_ns) / 1_000_000,
        "provider_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0.0,
    }
    with open("/tmp/m9-occurrence-bench.json", "w", encoding="utf-8") as handle:
        json.dump(evidence, handle)
    assert p95_delta_ms <= 2.0, evidence


def test_empty_frozen_provenance_has_a_stable_digest():
    row = BakeoffCaseResult(
        case_id="x",
        category="verification_requirements",
        model="offline-probe",
        repetition=0,
        parse_ok=True,
        score=None,
        latency_ms=0,
    )
    frozen = freeze_promotion_provenance([], ())
    assert frozen["row_count"] == 0
    assert frozen["digest"]
    assert row.case_id == "x"
