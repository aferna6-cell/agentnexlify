# Improvement Backlog — Run 2026-09-18-pm (Run 123)

## Active

- **Step 9E: 10-Day P0 Credential Expiry Escalation Tier** — add days_remaining <= 10 branch to Step 9E with new P0 GH issue filing. AUTOPILOT_GH_TOKEN expires 2026-10-02 (14 days). 4th carry-forward. Autonomous-executable threshold reached at run 122 (task prompt prevents execution).

## Parking Lot (survived debate but not chosen)

- **Step 9J.2: Major-bump Dependabot triage issue** — when Step 9J skips major-bump PRs, file one GH issue per batch (dedup 7d) listing them. 5 PRs today (React 19, vitest 5) aging with no tracking. Run 124 candidate.
- **Step 9N: AI metering violation trend tracking** — store Step 9L violation count in `subconscious/state/step9l-history.json` per nightly; alert on count increase (regression). GH #827 (P1, 45 violations) is the current owner's sprint — Step 9N guards against regression. Run 125 candidate.
- **Step 9G governance correction** — governance.json active_directions Step 9G entry still shows `status: pending`. Today's nightly confirms the fix works. Corrected in Phase 6 of this run.

## Rejected This Run

- None formally rejected — Idea 2 and Idea 3 weakened to bonus/parking-lot, not killed.

## Questions for Next Run

1. Was Step 9E P0 tier implemented in SKILL.md? (grep: `days_remaining`, `P0`, `<= 10`)
2. Did the P0 tier fire correctly on nightly-2026-09-22 when AUTOPILOT_GH_TOKEN hits day 80?
3. Has AUTOPILOT_GH_TOKEN been rotated before 2026-10-02?
4. os_tool_executions.py GH issue: filed as bonus action this run? If not, file in run 124.
5. Step 9G governance correction: verified in run 124 governance check?
