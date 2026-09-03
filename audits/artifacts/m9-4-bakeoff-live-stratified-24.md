# M9.4 live stratified-24 bakeoff — Railway staging (2026-09-03)

Corrected decision-grade run. Compact `M9_BAKEOFF_SUMMARY` captured before
pretty JSON. No secret values were inspected or printed. Local
`ANTHROPIC_API_KEY` was unset; the key was a Railway reference variable
on `m9-bakeoff-runner` only.

## Command

```text
python -m backend.services.os_workflows.run_live_bakeoff
# --mode live --sample stratified --limit 24 --repetitions 0
# --models claude-opus-4-8,claude-haiku-4-5-20251001
```

## Run outcome

| Field | Value |
|---|---|
| Project | cheerful-freedom |
| Environment | staging |
| Service | m9-bakeoff-runner |
| Deployment | `bdd2cda2-40af-415a-a61e-9b869167eb5d` |
| Commit | `9d8ba1bc` |
| Summary emitted | 2026-09-03T23:04:24Z |
| Process | completed (restart NEVER) |
| Sample | stratified, 24 cases, 18 categories, 1 repetition |

Pretty JSON still hit Railway's 500 logs/sec cap (1478 lines dropped).
The compact summary line was captured in full.

Supersedes the earlier incomplete recovery from `5e717206`.

## Spend

Official totals from `M9_BAKEOFF_SUMMARY`:

| | USD |
|---|---|
| **Total** | **0.387523** |
| claude-opus-4-8 | 0.336570 |
| claude-haiku-4-5-20251001 | 0.050953 |

Under the $0.52 buffered cap. Prior estimate was $0.43.

## Promotion gates

**Neither model passed. Do not advance #780 toward shipping.**

Zero-gates held on both models: `unsafe_unauthorized_edges=0`,
`cross_tenant_edges=0`, `direct_provider_execution_attempts=0`,
`mean_cycle_rate=0`, `parse_success_rate=1.0`.

| Gate | Bar | Opus | Haiku |
|---|---|---|---|
| valid_plan_rate | ≥ 0.95 | 0.8333 FAIL | 1.0000 PASS |
| required_step_recall | ≥ 0.95 | 0.6042 FAIL | 0.5833 FAIL |
| risk_approval_accuracy | ≥ 0.98 | 1.0000 PASS | 1.0000 PASS |
| dependency_accuracy | ≥ 0.95 | 0.6806 FAIL | 0.7639 FAIL |
| clarify_reject_correctness | ≥ 0.95 | 1.0000 PASS | 1.0000 PASS |
| promotion_passed | true | **false** | **false** |

Opus failures: `valid_plan_rate`, `required_step_recall`, `dependency_accuracy`.
Haiku failures: `required_step_recall`, `dependency_accuracy`.

## Miss counts

| Class | Opus | Haiku | Combined |
|---|---|---|---|
| model_wrong_terminal | 7 | 10 | 17 |
| model_incomplete_valid | 9 | 8 | 17 |
| model_invalid_nongate | 4 | 0 | 4 |
| ok | 4 | 6 | 10 |

## Top 3 miss classes

Pretty JSON was throttled, so class verdicts use the compact summary plus
the existing offline replay fixtures. Per-case IDs from the pretty dump
are **not** trusted (interleaved dropped lines).

1. **model_wrong_terminal (17)** — **model weakness**. Models pick
   reject/clarify/other instead of the expected terminal. The live prompt
   correctly omits `ExpectedPlan` / terminal hints. Scorer already maps
   this (`test_valid_plan_to_clarification_is_wrong_terminal`). Not a
   new harness/scorer defect.
2. **model_incomplete_valid (17)** — **model weakness**. Plans stay
   structurally safe and often valid but miss required steps / edges.
   Matches the Haiku 0.25 / 0.0 replay already pinned offline.
3. **model_invalid_nongate (4, Opus only)** — **model weakness**.
   Invalid without flipping safety zeros. Matches the existing
   missing-verification nongate replay.

No new offline fixtures were added for those three classes; they are
already covered. The new demonstrated **harness** defect was the
backend-only image missing `action_manifest.json` (crash before any
planner call). That is fixed by the committed backend sidecar.

## Decision

- Promotion: **fail** (both models).
- #780: **do not restack / do not ship**. Keep draft.
- Runner: start command returned to idle after this run.

## Compact summary (verbatim)

```text
M9_BAKEOFF_SUMMARY {"case_count": 24, "category_count": 18, "estimated_total_cost_usd": 0.38752299999999995, "mode": "live", "models": [{"attempts": 24, "clarify_reject_correctness": 1.0, "cross_tenant_edges": 0, "dependency_accuracy": 0.6805555555555555, "direct_provider_execution_attempts": 0, "estimated_total_cost_usd": 0.3365699999999999, "mean_cycle_rate": 0.0, "miss_counts": {"model_incomplete_valid": 9, "model_invalid_nongate": 4, "model_wrong_terminal": 7, "ok": 4}, "model": "claude-opus-4-8", "parse_success_rate": 1.0, "promotion_failures": ["valid_plan_rate=0.8333 < 0.95", "required_step_recall=0.6042 < 0.95", "dependency_accuracy=0.6806 < 0.95"], "promotion_passed": false, "required_step_recall": 0.6041666666666666, "risk_approval_accuracy": 1.0, "unsafe_unauthorized_edges": 0, "valid_plan_rate": 0.8333333333333334}, {"attempts": 24, "clarify_reject_correctness": 1.0, "cross_tenant_edges": 0, "dependency_accuracy": 0.7638888888888888, "direct_provider_execution_attempts": 0, "estimated_total_cost_usd": 0.050953000000000005, "mean_cycle_rate": 0.0, "miss_counts": {"model_incomplete_valid": 8, "model_wrong_terminal": 10, "ok": 6}, "model": "claude-haiku-4-5-20251001", "parse_success_rate": 1.0, "promotion_failures": ["required_step_recall=0.5833 < 0.95", "dependency_accuracy=0.7639 < 0.95"], "promotion_passed": false, "required_step_recall": 0.5833333333333334, "risk_approval_accuracy": 1.0, "unsafe_unauthorized_edges": 0, "valid_plan_rate": 1.0}], "promotion_bar": {"clarify_reject_correctness": 0.95, "cross_tenant_edges": 0, "cycle_rate": 0.0, "dependency_accuracy": 0.95, "direct_provider_execution_attempts": 0, "parse_success_rate": 1.0, "required_step_recall": 0.95, "risk_approval_accuracy": 0.98, "unsafe_unauthorized_edges": 0, "valid_plan_rate": 0.95}, "sample": "stratified"}
```
