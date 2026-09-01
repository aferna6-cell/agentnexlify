# Improvement Backlog — Run 116 (2026-09-01-pm)

## Active
- Step 9L — nightly connector auth pattern scan: grep `*_connector.py` for 401/refresh/retry handling; file GH issue (labels: security, ai-ready) when violations found

## Parking Lot (survived debate but not chosen)
- Gmail connector auth pattern KB article — bundle as bonus when implementing Step 9L
- os_tool_executions.py god-class split — deferred to run 117; condition: 4d+ stability (last commit 2026-09-01, check again 2026-09-05)

## Rejected This Run
- Wire CRM eval to CI as required gate — evidence unconfirmed, M8 sprint timing wrong; revisit post-M8
- Close stale subconscious draft PRs — Step 9K handles escalation path; needs human review, not autonomous action

## Questions for Next Run (117)
1. Did Step 9L fire in nightly-2026-09-02? Which connectors flagged?
2. os_tool_executions.py: 0 commits since 2026-09-01? If yes, file the split issue.
3. GH #684 SUPABASE_ACCESS_TOKEN: set in Railway? Brain connector still 40d stale?
4. M8 sprint: Calendar+CRM deployed? OAuth service_role HOLD resolved?
5. Step 9K: stale subconscious PR count at or above escalation threshold (≥5 or any >60d)?
