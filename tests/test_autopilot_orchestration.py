import pytest

from scripts.autopilot.classify_and_dispatch import (
    AutopilotError,
    ClassificationResult,
    ProofOfWork,
    _format_pr_body,
    _max_active_runs_from_env,
)


def test_max_active_runs_defaults_to_one(monkeypatch):
    monkeypatch.delenv("AUTOPILOT_MAX_ACTIVE_RUNS", raising=False)

    assert _max_active_runs_from_env() == 1


def test_max_active_runs_rejects_non_positive(monkeypatch):
    monkeypatch.setenv("AUTOPILOT_MAX_ACTIVE_RUNS", "0")

    with pytest.raises(AutopilotError, match="at least 1"):
        _max_active_runs_from_env()


def test_format_pr_body_includes_review_packet():
    body = _format_pr_body(
        {"number": 123},
        ClassificationResult(
            classification="READY",
            reason="Acceptance criteria and surface are clear.",
            proposed_plan="Update the widget copy and run the local gate.",
        ),
        ProofOfWork(
            changed_files="M\tfrontend/src/widget.jsx",
            local_check="bash scripts/hooks/pre-commit: passed",
            residual_risks="Human visual review still required.",
        ),
    )

    assert "Closes #123" in body
    assert "## Autopilot Proof Of Work" in body
    assert "docs/AUTOPILOT_WORKFLOW.md" in body
    assert "M\tfrontend/src/widget.jsx" in body
    assert "bash scripts/hooks/pre-commit: passed" in body
