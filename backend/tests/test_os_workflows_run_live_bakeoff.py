"""Focused tests for the staging-only M9.4 live bakeoff runner.

No live Anthropic, WorkflowStore, Action Executor, or provider calls.
"""

import ast
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.services.os_workflows.planner_bakeoff import (
    CHEAP_PLANNER_MODEL,
    PROMOTION_BAR,
    STRONG_PLANNER_MODEL,
    BakeoffReport,
    ModelBakeoffReport,
)
from backend.services.os_workflows.run_live_bakeoff import (
    COMPACT_MODEL_KEYS,
    SUMMARY_PREFIX,
    compact_bakeoff_summary,
    format_compact_summary_line,
    main,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RUNNER = Path(__file__).resolve().parents[1] / "services" / "os_workflows" / "run_live_bakeoff.py"


def _two_model_report() -> BakeoffReport:
    opus = ModelBakeoffReport(
        model=STRONG_PLANNER_MODEL,
        attempts=24,
        parse_success_rate=1.0,
        valid_plan_rate=0.5,
        required_step_recall=0.7,
        risk_approval_accuracy=0.9,
        dependency_accuracy=0.8,
        clarify_reject_correctness=0.75,
        unsafe_unauthorized_edges=0,
        cross_tenant_edges=0,
        direct_provider_execution_attempts=0,
        mean_cycle_rate=0.0,
        estimated_total_cost_usd=0.321,
        promotion_passed=False,
        promotion_failures=["valid_plan_rate=0.5000 < 0.95"],
        miss_counts={"model_incomplete_valid": 8, "model_invalid_nongate": 4},
    )
    haiku = ModelBakeoffReport(
        model=CHEAP_PLANNER_MODEL,
        attempts=24,
        parse_success_rate=1.0,
        valid_plan_rate=1.0,
        required_step_recall=0.4,
        risk_approval_accuracy=0.85,
        dependency_accuracy=0.2,
        clarify_reject_correctness=0.6,
        unsafe_unauthorized_edges=0,
        cross_tenant_edges=0,
        direct_provider_execution_attempts=0,
        mean_cycle_rate=0.0,
        estimated_total_cost_usd=0.048,
        promotion_passed=False,
        promotion_failures=["required_step_recall=0.4000 < 0.95"],
        miss_counts={"model_incomplete_valid": 12},
    )
    return BakeoffReport(
        models=[opus, haiku],
        mode="live",
        sample="stratified",
        case_ids=[f"c-{i}" for i in range(24)],
        category_counts={"l2_l3_approval_placement": 6, "clarify": 18},
    )


def test_compact_summary_includes_both_models_spend_and_all_gates():
    report = _two_model_report()
    summary = compact_bakeoff_summary(report)
    assert summary["estimated_total_cost_usd"] == 0.369
    assert summary["mode"] == "live"
    assert summary["sample"] == "stratified"
    assert {m["model"] for m in summary["models"]} == {
        STRONG_PLANNER_MODEL,
        CHEAP_PLANNER_MODEL,
    }
    for model in summary["models"]:
        assert tuple(model) == COMPACT_MODEL_KEYS
        assert model["estimated_total_cost_usd"] is not None
        assert "promotion_passed" in model
        assert "promotion_failures" in model
        for gate in PROMOTION_BAR:
            if gate == "cycle_rate":
                assert "mean_cycle_rate" in model
            else:
                assert gate in model
    assert summary["promotion_bar"] == dict(PROMOTION_BAR)


def test_run_live_bakeoff_emits_exactly_one_summary_before_pretty_json():
    report = _two_model_report()
    buf = io.StringIO()
    with (
        patch(
            "backend.services.os_workflows.run_live_bakeoff.build_frozen_cases",
            return_value=["unused"],
        ) as cases,
        patch(
            "backend.services.os_workflows.run_live_bakeoff.run_bakeoff",
            return_value=report,
        ) as baked,
        redirect_stdout(buf),
    ):
        rc = main()

    assert rc == 0
    cases.assert_called_once_with()
    baked.assert_called_once()
    kwargs = baked.call_args.kwargs
    assert kwargs["mode"] == "live"
    assert kwargs["sample"] == "stratified"
    assert kwargs["limit"] == 24
    assert kwargs["repetitions"] == (0,)
    assert kwargs["models"] == (STRONG_PLANNER_MODEL, CHEAP_PLANNER_MODEL)

    text = buf.getvalue()
    summary_lines = [
        line for line in text.splitlines() if line.startswith(SUMMARY_PREFIX + " ")
    ]
    assert len(summary_lines) == 1
    first_line = text.splitlines()[0]
    assert first_line == summary_lines[0]
    assert first_line == format_compact_summary_line(report)
    payload = json.loads(first_line[len(SUMMARY_PREFIX) + 1 :])
    assert payload["estimated_total_cost_usd"] == 0.369
    assert [m["model"] for m in payload["models"]] == [
        STRONG_PLANNER_MODEL,
        CHEAP_PLANNER_MODEL,
    ]
    rest = text[len(first_line) :].lstrip()
    assert rest.startswith("{")
    pretty = json.loads(rest)
    assert "models" in pretty
    assert pretty["models"][0]["model"] == STRONG_PLANNER_MODEL


def test_run_live_bakeoff_has_no_store_or_executor_imports():
    tree = ast.parse(_RUNNER.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
            imported.extend(alias.name for alias in node.names)
    joined = " ".join(imported)
    assert "store" not in joined
    assert "WorkflowStore" not in joined
    assert "engine" not in joined
    assert "Action" not in joined
    assert "executor" not in joined.lower()


def test_production_dockerfile_does_not_copy_bakeoff_manifest():
    production = (_REPO_ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
    staging = (_REPO_ROOT / "Dockerfile.m9-bakeoff").read_text(encoding="utf-8")
    sidecar = (
        _REPO_ROOT
        / "backend"
        / "services"
        / "os_workflows"
        / "action_manifest.json"
    )
    canonical = (
        _REPO_ROOT
        / "agent-service"
        / "src"
        / "agent-os"
        / "actions"
        / "action_manifest.json"
    )
    railway = (_REPO_ROOT / "railway.m9-bakeoff.json").read_text(encoding="utf-8")
    assert "action_manifest.json" not in production
    assert "run_live_bakeoff" not in production
    assert "action_manifest.json" in staging
    assert "Staging-only" in staging
    assert "m9-bakeoff-runner idle" in staging
    assert "--mode" not in staging
    assert "claude-opus" not in staging
    assert "m9-bakeoff-runner idle" in railway
    assert sidecar.is_file()
    assert sidecar.read_text(encoding="utf-8") == canonical.read_text(encoding="utf-8")


def test_catalog_loads_from_backend_sidecar_when_agent_service_missing(tmp_path, monkeypatch):
    """Railway backend-only images crash without this sidecar (2026-09-03)."""
    import backend.services.os_workflows.tool_catalog as catalog

    missing = tmp_path / "missing-agent-service-manifest.json"
    sidecar = Path(catalog._BACKEND_MANIFEST_PATH)
    assert sidecar.is_file()
    monkeypatch.setattr(catalog, "_MANIFEST_PATH", missing)
    catalog._catalog.cache_clear()
    loaded = catalog._load_manifest()
    assert catalog._manifest_path() == sidecar
    assert "send_email" in (loaded.get("tools") or {})
    catalog._catalog.cache_clear()


def test_catalog_prefers_canonical_manifest_when_present():
    import backend.services.os_workflows.tool_catalog as catalog

    assert catalog._MANIFEST_PATH.is_file()
    assert catalog._manifest_path() == catalog._MANIFEST_PATH


def test_catalog_raises_when_canonical_and_sidecar_missing(tmp_path, monkeypatch):
    import backend.services.os_workflows.tool_catalog as catalog

    monkeypatch.setattr(catalog, "_MANIFEST_PATH", tmp_path / "no-canonical.json")
    monkeypatch.setattr(catalog, "_BACKEND_MANIFEST_PATH", tmp_path / "no-sidecar.json")
    with pytest.raises(FileNotFoundError, match="sidecar"):
        catalog._manifest_path()


def test_compact_summary_omits_total_when_any_model_cost_missing():
    report = _two_model_report()
    report.models[1].estimated_total_cost_usd = None
    summary = compact_bakeoff_summary(report)
    assert summary["estimated_total_cost_usd"] is None
    assert summary["models"][0]["estimated_total_cost_usd"] == 0.321
    assert summary["models"][1]["estimated_total_cost_usd"] is None
    assert summary["models"][0]["model"] == STRONG_PLANNER_MODEL
    assert summary["models"][1]["model"] == CHEAP_PLANNER_MODEL


def test_run_live_bakeoff_exits_nonzero_on_safety_gate():
    report = _two_model_report()
    report.models[0].unsafe_unauthorized_edges = 1
    buf = io.StringIO()
    with (
        patch(
            "backend.services.os_workflows.run_live_bakeoff.build_frozen_cases",
            return_value=["unused"],
        ),
        patch(
            "backend.services.os_workflows.run_live_bakeoff.run_bakeoff",
            return_value=report,
        ),
        redirect_stdout(buf),
    ):
        rc = main()
    assert rc == 1
    first_line = buf.getvalue().splitlines()[0]
    assert first_line.startswith(SUMMARY_PREFIX + " ")
    payload = json.loads(first_line[len(SUMMARY_PREFIX) + 1 :])
    assert payload["models"][0]["unsafe_unauthorized_edges"] == 1
