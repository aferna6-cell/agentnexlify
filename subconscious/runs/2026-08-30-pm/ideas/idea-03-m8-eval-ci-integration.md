# Idea 03 — M8 Calendar/CRM Eval → CI Gate

## Category
agent_performance

## Summary
Promote `eval/calendar-crm-eval-v1.json` to a CI gate that blocks merges when pass rate drops below threshold, catching Calendar/CRM regressions before production.

## Evidence
- 14 commits in last 3 days all M8 Calendar/CRM sprint (PRs #709-#712)
- `eval/calendar-crm-eval-v1.json` created this sprint (new eval harness)
- os_calendar_crm.py: 700 lines, os_tool_executions.py: 758 lines — large surface area
- CI currently has no eval gate for AI-facing features
- nightly-commit-review-2026-08-30 fixed block_demo_role miss — indicates rapid iteration with potential misses

## Implementation
1. Add `scripts/ci/run-calendar-crm-eval.py` — runs eval, asserts pass_rate >= 0.85
2. Wire to `.github/workflows/pr-validation.yml` as new check
3. Track pass_rate trend in `ops/routines/logs/`

## Weakness
- Eval harness is brand-new (created 2026-08-30) — needs stabilization before CI gate
- TypeScript execution environment uncertainty
- M effort (CI + script + threshold tuning)
- Risk: flaky eval blocks legitimate PRs

## Risk
MEDIUM — new eval may have false negatives, requires calibration period

## Confidence
MEDIUM (strong motivation, but eval too new for CI gate today)
