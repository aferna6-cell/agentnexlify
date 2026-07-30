# Winning Concept — 2026-07-30 (Run 101)

## Recommendation
Add Step 9H to `.claude/skills/nightly-commit-review/SKILL.md`: when ALL major GitHub Actions workflows show zero successes in the last 48 hours, file a `human-action-required` + `infra` GH issue titled "INFRA: GH Actions systematic failure — check billing/spending limit."

## Why This, Why Now
GH Actions spending limit #500 has silently blocked ALL CI for 11+ days (discovered manually, morning digest called it DAY 9 #1 priority). During that window: 40+ ai-ready issues stalled, 10 PRs queued without CI validation, dependabot merges frozen, autonomy loop unable to open/validate PRs. No automated signal fired for 11 days — the failure was invisible to every monitoring layer we have. The next spending-limit event (a realistic risk any month when AI pipeline costs spike) would repeat the same 11-day blind spot without Step 9H. The SKILL.md bash channel has proven reliable for exactly this class of automated check — Steps 9B/9C/9D/9E/9F all shipped in one nightly cycle each.

## Implementation Sketch
- After the existing Step 9F/9G blocks in SKILL.md, add `## Step 9H` bash block
- Collect last 48h run data: `gh run list --limit=50 --created=">=$(date -d '48 hours ago' --iso-8601)" --json conclusion,workflowName,createdAt`
- Count unique `workflowName` values with `conclusion == "success"` → `SUCCESS_WORKFLOWS`
- Count unique `workflowName` values with `conclusion == "failure"` → `FAIL_WORKFLOWS`
- If `SUCCESS_WORKFLOWS == 0` AND `FAIL_WORKFLOWS >= 3` (at least 3 distinct workflows failing):
  - File GH issue via `gh issue create --title "INFRA: GH Actions systematic failure — check billing/spending limit" --body "Step 9H detected: 0 workflow successes, ${FAIL_WORKFLOWS} workflow types failing in last 48h. Common cause: GitHub Actions spending limit hit. Fix: github.com/settings/billing/summary → raise spending limit or add payment method. Issue auto-filed by nightly-commit-review Step 9H." --label "human-action-required,infra"`
  - Log: `"Step 9H: CI DARK — 0 successes, ${FAIL_WORKFLOWS} workflow types failing. GH issue filed."`
- Else: `"Step 9H: CI healthy — ${SUCCESS_WORKFLOWS} workflow types succeeded in last 48h."`
- Guard: if `gh issue list --search "INFRA: GH Actions systematic failure" --state open` returns a result → skip (dedupe guard, don't file duplicate)
- Guard: if `gh run list` fails (token issue) → log warning and skip gracefully
- Total new lines: ~25 bash, same template as Step 9F block

## What This Replaces
Nothing in active_directions is displaced. Step 9G (PR #577 DRAFT) remains the open carry-forward from run 100 — Bonus A comment posted on PR #577 this run. Step 9H is additive.

## Confidence
**HIGH** — Evidence is a concrete 11-day current incident. Mechanism proven across 5 prior steps. False-positive risk narrowable (0 successes × 3+ failing workflows × 48h = essentially impossible from code regression). `gh run list` works even when spending limit blocks new runs (read-only API, not blocked by billing). Dedupe guard prevents noise on repeated fires.
