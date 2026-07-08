# Idea 5 — SMS Compliance Dashboard Follow-Through Check

**Category:** customer_value
**Effort:** XS (verification only — no new recommendation)
**Confidence:** MEDIUM

## What
GH #385 (SMS Compliance Dashboard) had the `ai-ready` label applied by nightly 2026-07-08 (run 81 winner implemented). The issue-to-pr-loop polls for `ai-ready` labels every 15 min and opens draft PRs autonomously. This idea recommends verifying the loop picked up #385 and opened a PR. If not, diagnose the loop.

## Evidence
- Run 81 winner: "Add ai-ready label to GH #385 — activate issue-to-pr-loop for SMS Compliance Dashboard"
- governance.json active_directions[1]: status "implemented" — "nightly-commit-review 2026-07-08 — ai-ready label added to GH #385 via mcp__github__issue_write"
- Run 82 improvement-backlog.md Q2: "Did the issue-to-pr-loop open a PR for GH #385 SMS Compliance Dashboard? Check open PRs for a new draft since this run."
- SMS Compliance Dashboard: backend migration 160 + compliance_reports router shipped (from run history). Outstanding: 1 frontend page + 1 additional endpoint.
- 12/12 council score from run 70. 14+ days since backend shipped with no frontend completion.

## Why MEDIUM not HIGH
- Loop is automated — if it worked, there's nothing for subconscious to recommend
- If it didn't work, the diagnosis is: check loop health, which is a separate investigation
- Subconscious recommending "verify X" is lower leverage than recommending an atomic improvement
- This is more of a run-83-question answer than a standalone winner

## Autonomous-Executable?
NO — requires checking GitHub for open PRs (can be done via mcp__github__list_pull_requests).

## Verdict
This idea is best served as a "run 83 question answered" item in the run summary, not a standalone winner. The loop handles it autonomously if working. If not working, the fix is diagnosing the loop — a separate, higher-effort investigation outside subconscious scope.
