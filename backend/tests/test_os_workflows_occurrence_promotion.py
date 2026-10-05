"""Occurrence-safe M9.4 promotion gates. Offline only — no provider calls."""

import gc
import json
import time
from typing import List, Sequence
from unittest.mock import patch

import pytest

from backend.services.os_workflows.plan_eval import (
    CUSTOMER_COMMUNICATION_TOOLS,
    MATERIAL_DEPARTMENT_MIN_SUPPORT,
    MATERIAL_DEPARTMENTS,
    _score_bound_occurrences,
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
    CANONICAL_ACTION_MANIFEST_FINGERPRINT,
    CANONICAL_CASE_CONTENT_FINGERPRINT,
    CANONICAL_CATALOG_FINGERPRINT,
    action_manifest_fingerprint,
    case_content_fingerprint,
    catalog_fingerprint,
    run_model_bakeoff,
    seal_promotion_manifest,
)
from backend.services.os_workflows.eval_cases import build_frozen_cases
from backend.services.os_workflows.tool_catalog import (
    RISK_EXTERNAL_COMMUNICATION,
    TOOL_CATALOG,
    tool_verification_required,
)

_CLIENT = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
_N = 100


def _sealed(cases, planner=None, repetitions=(0,), mode="live", **kwargs):
    kwargs.pop("model", None)
    sealed = kwargs.pop("sealed_manifest", None)
    if sealed is None:
        sealed = seal_promotion_manifest(list(cases), repetitions)
    return run_model_bakeoff(
        cases,
        model="offline-probe",
        repetitions=repetitions,
        mode=mode,
        planner=planner,
        sealed_manifest=sealed,
        **kwargs,
    )


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
    for tool_id in CUSTOMER_COMMUNICATION_TOOLS:
        meta = TOOL_CATALOG[tool_id]
        assert meta["risk_level"] >= RISK_EXTERNAL_COMMUNICATION
        assert meta["mutating"] is True
    assert "cancel_calendar_event" not in CUSTOMER_COMMUNICATION_TOOLS
    assert "reschedule_calendar_event" not in CUSTOMER_COMMUNICATION_TOOLS
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


def _corpus_case(index: int, *, required_count: int) -> FrozenCase:
    required = ["get_customer"] * required_count
    tools = required + ["search_customers"]
    return FrozenCase(
        id=f"row-{index:03d}",
        category="verification_requirements",
        goal=f"verify customer row {index}",
        client_id=_CLIENT,
        expected=ExpectedPlan(
            departments=["admin_records"],
            required_tools=tools,
            allowed_tools=tools,
            verification_required_tools=required,
            max_steps=4,
            terminal="valid_plan",
        ),
    )


def _corpus_plan(case: FrozenCase, *, required_flags: List[bool], optional_flag: bool) -> CandidatePlan:
    steps = [
        PlanStepSpec(
            id=f"g{index}",
            tool_name="get_customer",
            department="admin_records",
            risk_level=0,
            approval_required=False,
            verification_required=flag,
        )
        for index, flag in enumerate(required_flags)
    ]
    steps.append(
        PlanStepSpec(
            id="opt",
            tool_name="search_customers",
            department="admin_records",
            risk_level=0,
            approval_required=False,
            verification_required=optional_flag,
        )
    )
    return CandidatePlan(
        client_id=case.client_id,
        owner_goal=case.goal,
        terminal="valid_plan",
        steps=steps,
    )


def test_n100_one_mutated_duplicate_occurrence_fails_only_on_missing():
    """100 sealed rows. Exactly one candidate has two required get_customer flags, false then true."""
    mutated_index = 7
    cases = [
        _corpus_case(index, required_count=2 if index == mutated_index else 1)
        for index in range(_N)
    ]
    plans = {
        case.id: _corpus_plan(
            case,
            required_flags=[False, True] if index == mutated_index else [True],
            optional_flag=False,
        )
        for index, case in enumerate(cases)
    }

    def planner(case, model, seed, _plans=plans):
        del model, seed
        return _zero_attempt(_plans[case.id])

    report = _sealed(cases, planner=planner, repetitions=(0,))
    mutated = report.case_results[mutated_index]
    assert mutated.score is not None
    assert mutated.score.verification_true_positives == 1
    assert mutated.score.verification_false_negatives == 1
    assert mutated.score.required_verification_support == 2
    assert mutated.score.required_verification_recall == 0.5
    assert report.attempts == _N
    assert report.harness_scoring_failure_count == 0
    assert report.missing_required_verification_count == 1
    assert report.verification_true_positives == 100
    assert report.verification_false_negatives == 1
    assert report.promotion_evaluated is False
    assert report.promotion_passed is None
    assert report.promotion_unevaluated_reasons == ["unsealed_provenance"]
    assert [row.case_id for row in report.case_results] == [case.id for case in cases]
    assert report.input_tokens_total == 0
    assert report.output_tokens_total == 0
    assert report.total_tokens_total == 0
    assert report.estimated_total_cost_usd == 0.0


@pytest.mark.parametrize("width", [24, 49, 50, 51, 100])
def test_one_missing_required_verification_fails_at_every_boundary(width: int):
    cases = [_corpus_case(index, required_count=1) for index in range(width)]
    plans = {
        case.id: _corpus_plan(
            case,
            required_flags=[False] if index == 0 else [True],
            optional_flag=False,
        )
        for index, case in enumerate(cases)
    }

    def planner(case, model, seed, _plans=plans):
        del model, seed
        return _zero_attempt(_plans[case.id])

    report = _sealed(cases, planner=planner, repetitions=(0,))
    assert report.missing_required_verification_count == 1
    assert report.harness_scoring_failure_count == 0
    assert report.promotion_passed is None
    assert report.promotion_unevaluated_reasons == ["unsealed_provenance"]


@pytest.mark.parametrize(
    ("width", "must_fail"),
    [(24, True), (49, True), (50, False), (51, False), (100, False)],
)
def test_optional_fp_dilution_boundary(width: int, must_fail: bool):
    cases = [_corpus_case(index, required_count=1) for index in range(width)]
    plans = {
        case.id: _corpus_plan(
            case,
            required_flags=[True],
            optional_flag=index == 0,
        )
        for index, case in enumerate(cases)
    }

    def planner(case, model, seed, _plans=plans):
        del model, seed
        return _zero_attempt(_plans[case.id])

    report = _sealed(cases, planner=planner, repetitions=(0,))
    assert report.verification_false_positives == 1
    assert report.verification_true_negatives == width - 1
    assert report.unnecessary_verification_rate == 1 / width
    assert report.verification_precision == width / (width + 1)
    assert (report.unnecessary_verification_rate > 0.02) is must_fail or (
        report.verification_precision < 0.98
    ) is must_fail
    assert report.promotion_passed is None
    assert report.promotion_unevaluated_reasons == ["unsealed_provenance"]


def test_optional_false_positive_is_not_diluted_by_required_hits():
    """100 correct required get_customer hits plus one optional search false positive."""
    tools = ["get_customer"] * 100 + ["search_customers"]
    case = FrozenCase(
        id="dilute-optional",
        category="verification_requirements",
        goal="many required reads and one optional search",
        client_id=_CLIENT,
        expected=ExpectedPlan(
            departments=["admin_records"],
            required_tools=tools,
            allowed_tools=tools,
            verification_required_tools=["get_customer"] * 100,
            max_steps=101,
            terminal="valid_plan",
        ),
    )
    steps = [
        PlanStepSpec(
            id=f"g{index}",
            tool_name="get_customer",
            department="admin_records",
            risk_level=0,
            verification_required=True,
        )
        for index in range(100)
    ]
    steps.append(
        PlanStepSpec(
            id="opt",
            tool_name="search_customers",
            department="admin_records",
            risk_level=0,
            verification_required=True,
        )
    )
    plan = CandidatePlan(
        client_id=case.client_id,
        owner_goal=case.goal,
        terminal="valid_plan",
        steps=steps,
    )

    def planner(c, model, seed, _plan=plan):
        del c, model, seed
        return _zero_attempt(_plan)

    report = _sealed([case], planner=planner)
    score = report.case_results[0].score
    assert score is not None
    assert score.verification_true_positives == 100
    assert score.verification_false_positives == 1
    assert score.verification_true_negatives == 0
    assert score.optional_verification_support == 1
    assert score.verification_precision == 100 / 101
    assert score.unnecessary_verification_rate == 1.0
    assert report.promotion_passed is None
    assert report.promotion_unevaluated_reasons == ["unsealed_provenance"]
    assert report.estimated_total_cost_usd == 0.0


def test_omitted_expected_department_occurrences_stay_in_support():
    tools = ["get_customer"] * 20 + ["send_email"]
    case = FrozenCase(
        id="dept-omit",
        category="verification_requirements",
        goal="twenty lookups then email",
        client_id=_CLIENT,
        expected=ExpectedPlan(
            departments=["admin_records", "sales"],
            required_tools=tools,
            allowed_tools=tools,
            verification_required_tools=["send_email"],
            max_steps=21,
            terminal="valid_plan",
        ),
    )
    plan = CandidatePlan(
        client_id=case.client_id,
        owner_goal=case.goal,
        terminal="valid_plan",
        steps=[
            PlanStepSpec(
                id="g0",
                tool_name="get_customer",
                department="admin_records",
                risk_level=0,
                verification_required=False,
            ),
            PlanStepSpec(
                id="mail",
                tool_name="send_email",
                department="sales",
                risk_level=2,
                approval_required=True,
                verification_required=True,
            ),
        ],
    )

    def planner(c, model, seed, _plan=plan):
        del c, model, seed
        return _zero_attempt(_plan)

    report = _sealed([case], planner=planner)
    assert report.required_step_recall == 1.0
    assert report.material_department_expected["admin_records"] == 20
    assert report.material_department_candidate["admin_records"] == 1
    assert report.material_department_support["admin_records"] == 20
    assert report.material_department_missing["admin_records"] == 19
    assert report.department_accuracy is not None and report.department_accuracy < 0.98
    assert report.promotion_passed is None
    assert report.promotion_unevaluated_reasons == ["unsealed_provenance"]
    assert report.estimated_total_cost_usd == 0.0


def test_required_only_optional_only_and_empty_support_stay_unevaluated():
    send = TOOL_CATALOG["send_email"]
    required_only = FrozenCase(
        id="required-only",
        category="verification_requirements",
        goal="email only",
        client_id=_CLIENT,
        expected=ExpectedPlan(
            departments=["sales"],
            required_tools=["send_email"],
            allowed_tools=["send_email"],
            max_steps=2,
        ),
    )
    required_plan = CandidatePlan(
        client_id=_CLIENT,
        owner_goal="email only",
        steps=[
            PlanStepSpec(
                id="m",
                tool_name="send_email",
                department="sales",
                risk_level=send["risk_level"],
                approval_required=True,
                verification_required=True,
            )
        ],
    )
    optional_only = _lookup_case("get_customer", case_id="optional-only")
    optional_plan = _catalog_plan(optional_only, "get_customer")
    empty = FrozenCase(
        id="empty-support",
        category="terminal",
        goal="nothing",
        client_id=_CLIENT,
        expected=ExpectedPlan(
            terminal="clarification_needed",
            expect_no_side_effects=True,
            max_steps=0,
        ),
    )
    empty_plan = CandidatePlan(
        client_id=_CLIENT,
        owner_goal="nothing",
        terminal="clarification_needed",
        steps=[],
    )

    def planner(case, model, seed, plans=None):
        del model, seed
        return _zero_attempt(plans[case.id])

    required_report = _sealed(
        [required_only],
        planner=lambda c, m, s: planner(c, m, s, {required_only.id: required_plan}),
    )
    assert required_report.required_verification_support == 1
    assert required_report.optional_verification_support == 0
    assert required_report.unnecessary_verification_rate is None
    assert required_report.promotion_evaluated is False
    assert required_report.promotion_passed is None
    assert required_report.promotion_unevaluated_reasons == ["optional_support"]

    optional_report = _sealed(
        [optional_only],
        planner=lambda c, m, s: planner(c, m, s, {optional_only.id: optional_plan}),
    )
    assert optional_report.required_verification_support == 0
    assert optional_report.optional_verification_support == 1
    assert optional_report.required_verification_recall is None
    assert optional_report.promotion_passed is None
    assert optional_report.promotion_unevaluated_reasons == ["required_support"]

    empty_report = _sealed(
        [empty],
        planner=lambda c, m, s: planner(c, m, s, {empty.id: empty_plan}),
    )
    assert empty_report.required_verification_support == 0
    assert empty_report.optional_verification_support == 0
    assert empty_report.required_verification_recall is None
    assert empty_report.verification_precision is None
    assert empty_report.unnecessary_verification_rate is None
    assert empty_report.promotion_passed is None
    assert empty_report.promotion_unevaluated_reasons == [
        "required_support",
        "optional_support",
    ]


def test_source_change_before_run_is_unevaluated_against_prior_seal():
    original = [
        _corpus_case(0, required_count=1),
        _corpus_case(1, required_count=1),
    ]
    seal = seal_promotion_manifest(original, (0,))
    altered = [
        original[0],
        FrozenCase(
            id=original[1].id,
            category="other_stratum",
            goal=original[1].goal,
            client_id=original[1].client_id,
            expected=ExpectedPlan(
                required_tools=["send_email"],
                allowed_tools=["send_email"],
                verification_required_tools=["send_email"],
                max_steps=2,
            ),
        ),
    ]

    def planner(case, model, seed):
        del model, seed
        if case.expected.required_tools == ["send_email"]:
            meta = TOOL_CATALOG["send_email"]
            plan = CandidatePlan(
                client_id=case.client_id,
                owner_goal=case.goal,
                steps=[
                    PlanStepSpec(
                        id="m",
                        tool_name="send_email",
                        department="sales",
                        risk_level=meta["risk_level"],
                        approval_required=True,
                        verification_required=True,
                    )
                ],
            )
        else:
            plan = _corpus_plan(case, required_flags=[True], optional_flag=False)
        return _zero_attempt(plan)

    report = _sealed(altered, planner=planner, sealed_manifest=seal)
    assert report.promotion_evaluated is False
    assert report.promotion_passed is None
    assert "provenance" in report.promotion_unevaluated_reasons

    reordered = _sealed(list(reversed(original)), planner=planner, sealed_manifest=seal)
    assert reordered.promotion_passed is None
    assert "ordering" in reordered.promotion_unevaluated_reasons


def test_caller_minted_seal_cannot_promote_synthetic_corpus():
    case = _balanced_case()
    plan = _balanced_plan(case, optional_flag=False)
    seal = seal_promotion_manifest([case], (0,))

    def planner(c, model, seed, _plan=plan):
        del c, model, seed
        return _zero_attempt(_plan)

    report = run_model_bakeoff(
        [case],
        model="offline-probe",
        repetitions=(0,),
        mode="live",
        planner=planner,
        sealed_manifest=seal,
    )
    assert report.promotion_evaluated is False
    assert report.promotion_passed is None
    assert report.promotion_failures == []
    assert report.promotion_unevaluated_reasons == ["unsealed_provenance"]
    assert report.input_tokens_total == 0
    assert report.output_tokens_total == 0
    assert report.estimated_total_cost_usd == 0.0


def test_unmatched_candidate_occurrence_is_fp_and_department_miss():
    tools = ["get_customer"] * 49 + ["search_customers"]
    case = FrozenCase(
        id="extra-step",
        category="verification_requirements",
        goal="forty nine required and one optional",
        client_id=_CLIENT,
        expected=ExpectedPlan(
            departments=["admin_records"],
            required_tools=tools,
            allowed_tools=["get_customer", "search_customers"],
            verification_required_tools=["get_customer"] * 49,
            max_steps=51,
        ),
    )
    steps = [
        PlanStepSpec(
            id=f"g{index}",
            tool_name="get_customer",
            department="admin_records",
            risk_level=0,
            verification_required=True,
        )
        for index in range(49)
    ]
    steps.append(
        PlanStepSpec(
            id="opt",
            tool_name="search_customers",
            department="admin_records",
            risk_level=0,
            verification_required=False,
        )
    )
    steps.append(
        PlanStepSpec(
            id="extra",
            tool_name="search_customers",
            department="sales",
            risk_level=0,
            verification_required=True,
        )
    )
    plan = CandidatePlan(
        client_id=case.client_id,
        owner_goal=case.goal,
        terminal="valid_plan",
        steps=steps,
    )
    score = score_plan(case, plan, mode="gold")
    assert len(plan.steps) == 51
    assert score.verification_true_positives == 49
    assert score.verification_false_negatives == 0
    assert score.verification_false_positives == 1
    assert score.verification_true_negatives == 1
    assert score.optional_verification_support == 2
    assert score.unnecessary_verification_rate == 0.5
    assert score.verification_precision == 49 / 50
    assert score.material_department_expected["admin_records"] == 50
    assert score.material_department_candidate["admin_records"] == 51
    assert score.department_checks == 51
    assert score.department_hits == 50
    assert score.material_department_missing["admin_records"] == 1
    assert score.department_accuracy == 50 / 51

    def planner(c, model, seed, _plan=plan):
        del c, model, seed
        return _zero_attempt(_plan)

    report = _sealed([case], planner=planner)
    assert report.verification_false_positives == 1
    assert report.material_department_candidate["admin_records"] == 51
    assert report.material_department_expected["admin_records"] == 50
    assert report.promotion_passed is None
    assert report.promotion_unevaluated_reasons == ["unsealed_provenance"]
    assert report.estimated_total_cost_usd == 0.0


def test_case_context_changes_committed_fingerprint():
    from backend.services.os_workflows.planner_bakeoff import promotion_is_allowlisted

    cases = build_frozen_cases()
    original = case_content_fingerprint(cases)
    assert original == CANONICAL_CASE_CONTENT_FINGERPRINT
    changed = cases[0].model_copy(deep=True)
    changed.context = {"injected": "changed planner semantics"}
    mutated = [changed] + list(cases[1:])
    assert case_content_fingerprint(mutated) != original
    manifest = seal_promotion_manifest(mutated, (0,))
    assert manifest["case_content_fingerprint"] != CANONICAL_CASE_CONTENT_FINGERPRINT
    assert promotion_is_allowlisted(manifest) is False


def test_canonical_frozen_corpus_fingerprint_is_committed():
    from backend.services.os_workflows.planner_bakeoff import promotion_is_allowlisted

    cases = build_frozen_cases()
    assert action_manifest_fingerprint() == CANONICAL_ACTION_MANIFEST_FINGERPRINT
    assert catalog_fingerprint() == CANONICAL_CATALOG_FINGERPRINT
    assert case_content_fingerprint(cases) == CANONICAL_CASE_CONTENT_FINGERPRINT
    assert promotion_is_allowlisted(seal_promotion_manifest(cases, (0,))) is True
    assert promotion_is_allowlisted(seal_promotion_manifest(cases, (0, 1))) is True


def test_action_manifest_fingerprint_is_checkout_newline_invariant(tmp_path, monkeypatch):
    """LF and CRLF copies of the same manifest must share the committed fingerprint."""
    from backend.services.os_workflows import tool_catalog

    real_path = tool_catalog._manifest_path()
    lf_bytes = real_path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    crlf_bytes = lf_bytes.replace(b"\n", b"\r\n")
    assert crlf_bytes != lf_bytes
    lf_path = tmp_path / "action_manifest.lf.json"
    crlf_path = tmp_path / "action_manifest.crlf.json"
    lf_path.write_bytes(lf_bytes)
    crlf_path.write_bytes(crlf_bytes)

    monkeypatch.setattr(tool_catalog, "_manifest_path", lambda: lf_path)
    lf_hash = action_manifest_fingerprint()
    monkeypatch.setattr(tool_catalog, "_manifest_path", lambda: crlf_path)
    crlf_hash = action_manifest_fingerprint()
    assert lf_hash == crlf_hash
    assert lf_hash == CANONICAL_ACTION_MANIFEST_FINGERPRINT
    assert crlf_hash == CANONICAL_ACTION_MANIFEST_FINGERPRINT


def test_unsealed_custom_corpus_cannot_promote():
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
    assert report.promotion_evaluated is False
    assert report.promotion_passed is None
    assert report.promotion_unevaluated_reasons == ["unsealed_provenance"]


def test_fixture_provenance_of_duplicate_case_stays_unevaluated():
    case = _duplicate_case()
    plan = _duplicate_plan(case)

    def planner(c, model, seed, _plan=plan):
        del c, model, seed
        return _zero_attempt(_plan)

    report = _sealed(
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

    report = _sealed(
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

    report = _sealed(
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
    assert report.promotion_evaluated is False
    assert report.promotion_passed is None
    assert report.promotion_unevaluated_reasons == ["unsealed_provenance"]
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

    report = _sealed(
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
    assert report.promotion_evaluated is False
    assert report.promotion_passed is None
    assert report.promotion_failures == []
    assert report.promotion_unevaluated_reasons == ["unsealed_provenance"]
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
        report = _sealed(
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
    assert report.promotion_evaluated is False
    assert report.promotion_passed is None
    assert report.promotion_unevaluated_reasons == ["unsealed_provenance"]
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

    report = _sealed(
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
    assert report.promotion_evaluated is False
    assert report.promotion_passed is None
    assert report.promotion_unevaluated_reasons == ["unsealed_provenance"]
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

    report = _sealed(
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
    assert report.promotion_passed is None
    assert report.promotion_unevaluated_reasons == ["unsealed_provenance"]
    assert any(row.parse_ok is False for row in report.case_results)
    assert len(report.case_results) == 2


def test_provenance_row_order_support_and_stratum_drift_stay_unevaluated():
    case = _balanced_case()
    plan = _balanced_plan(case, optional_flag=False)

    def planner(c, model, seed, _plan=plan):
        del c, model, seed
        return _zero_attempt(_plan)

    report = _sealed(
        [case],
        model="offline-probe",
        repetitions=(0, 1),
        mode="live",
        planner=planner,
    )
    assert report.promotion_passed is None
    assert report.promotion_unevaluated_reasons == ["unsealed_provenance"]

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


_LATENCY_LIMIT_MS = 2.0
# Windows GetProcessTimes / process_time_ns quantum. It cannot prove a 2 ms bound.
_WINDOWS_PROCESS_TIME_QUANTUM_NS = 15_625_000


def clock_can_prove_latency_limit(
    resolution_ns: int, limit_ms: float = _LATENCY_LIMIT_MS
) -> bool:
    """True only when one tick is at most one tenth of the ceiling.

    A 15.625 ms process-time quantum reports every fast sample as 0 or
    15.625 ms, so it is not admissible for a 2 ms p95 gate.
    """
    if resolution_ns <= 0:
        return False
    return resolution_ns * 10 <= int(limit_ms * 1_000_000)


def observe_clock_resolution_ns(clock, probes: int = 32) -> int:
    deltas = []
    previous = clock()
    spins = 0
    spin_limit = probes * 100_000
    while len(deltas) < probes and spins < spin_limit:
        spins += 1
        current = clock()
        if current == previous:
            continue
        delta = current - previous
        previous = current
        if delta > 0:
            deltas.append(delta)
    if not deltas:
        return 10**18
    return min(deltas)


def select_latency_clock():
    """Pick perf_counter_ns only when its resolution can prove the 2 ms ceiling."""
    resolution_ns = observe_clock_resolution_ns(time.perf_counter_ns)
    if not clock_can_prove_latency_limit(resolution_ns):
        raise AssertionError(
            "perf_counter_ns resolution "
            f"{resolution_ns} ns cannot prove a {_LATENCY_LIMIT_MS} ms bound"
        )
    return time.perf_counter_ns, "perf_counter_ns", resolution_ns


def run_paired_latency(new_fn, old_fn, *, clock, warmup: int, iterations: int):
    """Alternate which slice runs first. Restore GC even if timing raises."""
    gc_was_enabled = gc.isenabled()
    gc.disable()
    order = []
    deltas_ns = []
    new_ns = []
    old_ns = []
    try:
        for _ in range(warmup):
            new_fn()
            old_fn()
        for index in range(iterations):
            if index % 2 == 0:
                order.append("new-first")
                started = clock()
                new_fn()
                mid = clock()
                old_fn()
                finished = clock()
                new_elapsed = mid - started
                old_elapsed = finished - mid
            else:
                order.append("old-first")
                started = clock()
                old_fn()
                mid = clock()
                new_fn()
                finished = clock()
                old_elapsed = mid - started
                new_elapsed = finished - mid
            new_ns.append(new_elapsed)
            old_ns.append(old_elapsed)
            deltas_ns.append(new_elapsed - old_elapsed)
        return deltas_ns, new_ns, old_ns, order
    finally:
        if gc_was_enabled:
            gc.enable()
        else:
            gc.disable()


def test_paired_scorers_bind_once_per_plan_and_repeat_each_plan():
    """Verification and department share one bind. The next plan binds again."""
    case = _duplicate_case()
    plan = _duplicate_plan(case)
    expected = case.expected
    with patch(
        "backend.services.os_workflows.plan_eval._score_bound_occurrences",
        wraps=_score_bound_occurrences,
    ) as bound:
        verification = score_required_verification(plan, expected)
        department = score_department_integrity(plan, expected)
        assert bound.call_count == 1
        assert verification.true_positives == 1
        assert verification.false_negatives == 1
        assert verification.false_positives == 0
        assert verification.true_negatives == 0
        assert department.checks == 2
        assert department.hits == 2

        score_department_integrity(plan, expected)
        score_required_verification(plan, expected)
        assert bound.call_count == 2

        before = bound.call_count
        for item in [plan] * _N:
            score_required_verification(item, expected)
            score_department_integrity(item, expected)
        assert bound.call_count - before == _N

        plan.steps[0].department = "sales"
        score_required_verification(plan, expected)
        refreshed = score_department_integrity(plan, expected)
        assert bound.call_count - before == _N + 1
        assert refreshed.hits == 1
        assert refreshed.missing_by_department.get("admin_records") == 1

        plan.steps[0].department = "admin_records"
        score_department_integrity(plan, expected)
        plan.steps[1].verification_required = False
        repeated = score_department_integrity(plan, expected)
        assert repeated.hits == 2
        missed = score_required_verification(plan, expected)
        assert missed.true_positives == 0
        assert missed.false_negatives == 2

    mutated = _duplicate_case()
    mutated_plan = _duplicate_plan(mutated)
    score_required_verification(mutated_plan, mutated.expected)
    mutated.expected.verification_required_tools.clear()
    score_department_integrity(mutated_plan, mutated.expected)
    optional = score_required_verification(mutated_plan, mutated.expected)
    assert optional.required_support == 0
    assert optional.optional_support == 2
    assert optional.false_positives == 1
    assert optional.true_negatives == 1


def test_coarse_process_time_quantum_cannot_be_the_latency_clock():
    quantum = _WINDOWS_PROCESS_TIME_QUANTUM_NS

    class _Quantized:
        def __init__(self):
            self.now = 0

        def __call__(self):
            self.now += quantum
            return self.now

    resolution = observe_clock_resolution_ns(_Quantized(), probes=8)
    assert resolution == quantum
    assert clock_can_prove_latency_limit(resolution, _LATENCY_LIMIT_MS) is False

    clock, name, selected_resolution = select_latency_clock()
    assert name == "perf_counter_ns"
    assert clock is time.perf_counter_ns
    assert clock_can_prove_latency_limit(selected_resolution, _LATENCY_LIMIT_MS) is True
    assert selected_resolution < quantum

    seen = []

    def _new():
        seen.append("new")

    def _old():
        seen.append("old")

    gc.enable()
    _deltas, _new_ns, _old_ns, order = run_paired_latency(
        _new, _old, clock=time.perf_counter_ns, warmup=1, iterations=4
    )
    assert order == ["new-first", "old-first", "new-first", "old-first"]
    assert seen == ["new", "old", "new", "old", "old", "new", "new", "old", "old", "new"]
    assert gc.isenabled() is True

    gc.disable()
    try:
        run_paired_latency(_new, _old, clock=time.perf_counter_ns, warmup=0, iterations=2)
        assert gc.isenabled() is False
    finally:
        gc.enable()


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
    warmup = 50
    iterations = 200
    clock, clock_name, resolution_ns = select_latency_clock()

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

    gc_before = gc.isenabled()
    deltas_ns, new_ns, old_ns, order = run_paired_latency(
        lambda: _new_slice(plans),
        lambda: _old_slice(plans),
        clock=clock,
        warmup=warmup,
        iterations=iterations,
    )
    assert order[0] == "new-first"
    assert order[1] == "old-first"
    assert gc.isenabled() is gc_before

    p95_delta_ms = _p95(deltas_ns) / 1_000_000
    evidence = {
        "warmup": warmup,
        "iterations": iterations,
        "corpus_rows": _N,
        "p95_added_latency_ms": p95_delta_ms,
        "p95_new_ms": _p95(new_ns) / 1_000_000,
        "p95_old_ms": _p95(old_ns) / 1_000_000,
        "clock": clock_name,
        "clock_resolution_ns": resolution_ns,
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
