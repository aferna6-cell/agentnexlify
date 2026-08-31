# Improvement Backlog — Run 114 (2026-08-31)

## Active
- **Step 9K: Stale subconscious draft PR audit in nightly-commit-review SKILL.md** — 1st carry-forward, autonomous-executable this run. Add Step 9K block after Step 9J in SKILL.md; bonus: fix Step 9J detection (search_pull_requests vs list_pull_requests).

## Parking Lot (survived debate but not chosen)
- **Step 9J detection fix** — use search_pull_requests for Dependabot; bundled as bonus action with Step 9K implementation. ROI high but same commit as winner.
- **os_tool_executions.py god class split** — 758 lines, deferred. Run 113 mandate condition (3+ days stable) not met (1 day old, 3 commits in 2 days). Re-evaluate run 115.
- **`__future__` annotations pre-commit gap analysis** — m8_action_flags.py slipped past pre-commit; verify if new M8 service paths are excluded from hook glob. Single instance, verify before promoting.
- **M8 Calendar/CRM production rollout gate** — formal GH issue with pre-flip checklist. Already partially tracked via explicit HOLD comments in commits; promote if M8 flag flip is imminent.

## Rejected This Run
- **os_tool_executions.py split (run 114)** — KILLED. Not stable (1 day, 3 commits in 2 days). Premature split would conflict with active M8 development.

## Questions for Next Run
1. Did Step 9K fire in nightly-2026-09-01? How many open subconscious PRs, how many stale?
2. Did Step 9J detection fix get implemented as bonus? Did Dependabot PRs become visible again?
3. Is os_tool_executions.py stable by run 115 (3+ days, 0 commits)? If yes, promote to winner.
4. Was SUPABASE_ACCESS_TOKEN finally set in Railway (GH #684)?
5. Is M8 production flag flip imminent? If yes, promote M8 rollout gate to winner.
