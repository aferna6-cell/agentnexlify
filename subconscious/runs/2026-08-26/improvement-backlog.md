# Improvement Backlog — Run 112 (2026-08-26)

## Active (Pending Human Approval)

| # | Idea | Run | Channel | Status |
|---|------|-----|---------|--------|
| 1 | Pre-commit block_demo_role hook for new router files | 111 | human-approve-implement | PENDING |
| 2 | Step 9J retry on mergeable_state:unknown (30s delay) | **112** | autonomous-executable | **THIS RUN — awaiting implementation** |

## Parking Lot (Future Candidates)

| # | Idea | Evidence | Priority |
|---|------|----------|----------|
| 1 | Middleware-level block_demo_role FastAPI guard | GH #669 (97 routers). Pre-commit hook (run 111) + individual endpoint fixes = short-term; middleware = long-term systemic fix. M effort. | HIGH |
| 2 | Step 9D escalation on GH #500 | GH Actions dark 37+ days. Blocks CI, Step 9J clean-state merges, autopilot-loop. Comment on GH #500 with 37d-dark timeline. Autonomous-executable. | HIGH |
| 3 | Fix voice addon double-billing path (GH #687) | `billing_change_plan` in auth_billing.py doesn't cancel voice_addon Stripe sub on agent_os upgrade. Issue filed. issue-to-pr-loop should pick up. | MEDIUM |
| 4 | Add block_demo_role to billing_addons.py POST endpoints | 2-line fix, revenue endpoints unguarded. Step 9I will flag this on next sweep. GH #669 class tracker. | MEDIUM |
| 5 | Step 9L — daily log baseline comparison | Run 110 mandate item. If ops/routines/logs/ has 2+ day baseline, add delta reporting to nightly. Autonomous-executable SKILL.md edit. | LOW |

## Rejected / Frozen

| # | Idea | Reason | Run |
|---|------|--------|-----|
| 1 | AI-human handoff | Frozen permanently (governance) | all |
| 2 | Widget drift autonomous fix | Retired run 70 — FORBIDDEN paths in nightly SKILL.md, human-only | 70 |
| 3 | Step 9K stale PR report | IMPLEMENTED run 110 — not a candidate | 110 |
| 4 | Step 9J major-version safety gate | IMPLEMENTED run 110 (audit finding) | 110 |

## Open Structural Issues (human-action required)

| Issue | Age | Blocker |
|-------|-----|---------|
| GH #399 AUTOPILOT_GH_TOKEN expired | 48+ days | 30 ai-ready issues stalled in issue-to-pr-loop |
| GH #403 KB autopopulate stale (ANTHROPIC_API_KEY missing GH Actions) | 33+ days | KB dark, Steps 9F/9G reporting stale |
| GH #500 GH Actions dark | 37+ days | All CI workflows disabled, Step 9J cannot get clean state |
| GH #669 97/97 routers missing block_demo_role | 12+ days | Class-wide security gap |
| GH #684 Brain connector stale (33 days) | 1 day old | Brain refreshes blocked |
| GH #687 Voice addon double-billing on upgrade | New | Revenue correctness on chatbot+voice → agent_os path |
