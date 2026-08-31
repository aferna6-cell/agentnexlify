# Improvement Backlog — Run 114 (2026-08-31-pm)

## Active
- Step 9K: Stale subconscious draft PR audit in nightly-commit-review SKILL.md (IMPLEMENTED this run — governance mandate, 1st carry-forward)

## Parking Lot (survived debate but not chosen)
- M8 invariant scan in deploy checklist (WEAKENED — pre-commit already guards __future__ annotations; root cause is hook bypass, not checklist gap. Re-evaluate if violations recur in run 115)
- M8 OAuth blocker structured diagnostic in docs/ops/m8-staging-setup.md (deferred — lower priority while governance mandate fires)

## Rejected This Run
- os_tool_executions.py god class split (NOT DEBATED — deferred per run_113_mandate stability condition: last commit 2026-08-30, only 1 day ago, need 3+ days stable)

## Questions for Next Run
- Did Step 9K fire in nightly-2026-09-01? How many open/stale/critical subconscious PRs?
- Did Step 9J detection fix work? Dependabot PRs found by search_pull_requests?
- Is os_tool_executions.py stable (4+ days no commits) by run 115?
- M8 OAuth/service_role HOLD: resolved to deploy Calendar+CRM?
