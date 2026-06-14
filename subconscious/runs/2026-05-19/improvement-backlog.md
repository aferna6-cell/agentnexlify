# Improvement Backlog — 2026-05-19 (Run 25)

## Active

- **Invoke /moratorium-sprint** — execute 4 S-effort items in one session, open draft PR, begin moratorium exit path. Skill exists (7985fbb). ~50 min total.

## Parking Lot (survived debate, not chosen this run)

- **pre-commit-guard-add skill** — 15-20 min saved per new guard, ~1-2/month cadence. WEAKENED (moratorium still active, moratorium-sprint not yet invoked). Promote to run 26 winner if moratorium-sprint executes successfully.
- **AI-to-Human Handoff v1 GH issue** — Critical gap, 33 days pending, all 7 industries. WEAKENED (requires issue-to-pr-loop running, M-effort, not a moratorium-clearing action). Promote to first post-moratorium winner.
- **Merge safe dep PRs** (#102, #103, #163, #164) — independent of moratorium, safe to execute any time as a bonus action. ~5 min via mcp__github__merge_pull_request.
- **Zapier plan_status enforcement** — security bug, GH #107, ROI 2.5. Post-moratorium candidate.
- **Email sequences N+1 fix** — GH #112, ROI 2.3. Post-moratorium candidate.

## Rejected This Run

- **Governance cleanup as winner** (Idea 5) — trivially obvious bookkeeping; applied directly in Phase 6, not a worthy winner slot.

## Questions for Next Run

- Was /moratorium-sprint invoked? If yes: moratorium exit path begins, shift to customer value (AI-to-Human Handoff). If no: escalate — wire moratorium-sprint invocation into nightly-commit-review as automatic trigger when moratorium_active AND oldest > 14 days.
- Are the 4 safe dep PRs (#102, #103, #163, #164) merged? If not, recommend dep-batch-merge as a morning-routine addition.
- Is the issue-to-pr-loop confirmed running? Required before AI-to-Human Handoff GH issue is useful.
