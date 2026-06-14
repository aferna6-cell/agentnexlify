"""Golden-dataset eval for the Lead Qualifier Managed Agent.

Gated behind RUN_LEAD_QUALIFIER_EVAL=1 so CI does not burn API credits on
every push. Run locally with:

    RUN_LEAD_QUALIFIER_EVAL=1 \
    LEAD_QUALIFIER_AGENT_ID=<id> \
    ANTHROPIC_API_KEY=<key> \
    pytest backend/tests/evals/test_lead_qualifier_golden.py -v

Pass criteria per example:
- recommendation matches exactly
- intent_score within expected range (inclusive)
- fit_score within expected range (inclusive)

The harness reports a per-example PASS/FAIL line plus a summary at the end.
Threshold default: 80% of examples must pass overall.
"""

import json
import os
from pathlib import Path

import pytest

GOLDEN_PATH = Path(__file__).parent / "lead_qualifier_golden.json"
PASS_THRESHOLD = float(os.environ.get("LEAD_QUALIFIER_EVAL_THRESHOLD", "0.8"))

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LEAD_QUALIFIER_EVAL", "0") != "1",
    reason="Set RUN_LEAD_QUALIFIER_EVAL=1 to run the live golden eval",
)


def _load_examples() -> list[dict]:
    data = json.loads(GOLDEN_PATH.read_text())
    return data["examples"]


def _run_qualifier(lead: dict, tenant: dict) -> dict:
    """Call the live qualifier and return the normalized result.

    Imports happen inside the function so collection does not require
    Anthropic creds when the eval is skipped.
    """
    from backend.services.lead_qualification import (
        _build_prompt,
        _extract_json_from_reply,
        _extract_text_blocks,
        _normalize_qualification,
        _run_qualifier_session,
    )
    from backend.services.managed_agents import ManagedAgentsClient
    from backend.services.managed_agents_registry import lead_qualifier

    handle = lead_qualifier()
    prompt = _build_prompt(lead, tenant)
    client = ManagedAgentsClient()
    _, final_text = _run_qualifier_session(
        client,
        agent_id=handle.agent_id,
        environment_id=handle.environment_id,
        prompt=prompt,
        tenant_id="eval-tenant",
        lead_id="eval-lead",
    )
    parsed = _extract_json_from_reply(final_text)
    if parsed is None:
        raise AssertionError(f"Qualifier returned unparseable reply: {final_text[:300]}")
    return _normalize_qualification(parsed)


def _evaluate(actual: dict, expected: dict) -> tuple[bool, list[str]]:
    failures: list[str] = []

    rec = actual.get("recommendation")
    if rec != expected["recommendation"]:
        failures.append(f"recommendation={rec!r} expected={expected['recommendation']!r}")

    intent = actual.get("intent_score")
    intent_lo, intent_hi = expected["intent_score_range"]
    if intent is None or not (intent_lo <= intent <= intent_hi):
        failures.append(f"intent_score={intent} expected in [{intent_lo},{intent_hi}]")

    fit = actual.get("fit_score")
    fit_lo, fit_hi = expected["fit_score_range"]
    if fit is None or not (fit_lo <= fit <= fit_hi):
        failures.append(f"fit_score={fit} expected in [{fit_lo},{fit_hi}]")

    return (len(failures) == 0, failures)


@pytest.mark.parametrize("example", _load_examples(), ids=lambda e: e["id"])
def test_lead_qualifier_example(example: dict, request: pytest.FixtureRequest) -> None:
    """One assertion per example. Aggregate result tracked in conftest."""
    actual = _run_qualifier(example["input"]["lead"], example["input"]["tenant"])
    passed, failures = _evaluate(actual, example["expected"])

    bucket = request.config.cache.get("lead_qualifier_eval/results", []) or []
    bucket.append({"id": example["id"], "passed": passed, "failures": failures, "actual": actual})
    request.config.cache.set("lead_qualifier_eval/results", bucket)

    assert passed, f"{example['id']}: " + "; ".join(failures)


def test_lead_qualifier_aggregate_pass_rate(request: pytest.FixtureRequest) -> None:
    """Final gate — overall pass rate must clear PASS_THRESHOLD."""
    bucket = request.config.cache.get("lead_qualifier_eval/results", []) or []
    if not bucket:
        pytest.skip("No per-example results recorded yet")
    passed = sum(1 for r in bucket if r["passed"])
    rate = passed / len(bucket)
    assert rate >= PASS_THRESHOLD, (
        f"Pass rate {rate:.0%} below threshold {PASS_THRESHOLD:.0%} "
        f"({passed}/{len(bucket)} examples passed)"
    )
