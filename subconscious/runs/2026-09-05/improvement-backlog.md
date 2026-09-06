# Improvement Backlog — Run 115 (2026-09-05)
<!-- SUPERSEDED (2026-09-05-pm): AM draft; references file-level detection counts. Canonical spec: subconscious/runs/2026-09-05-pm/winning-concept.md -->

## Active
- Add Step 9L — AI metering coverage nightly check to `.claude/skills/nightly-commit-review/SKILL.md` (grep AI-calling files for reserve/record/release pattern; file GH issues on violations with labels `ai-ready + code_health`)

## Parking Lot (survived debate but not chosen)
- **Idea 1: compound-engineering AI metering checklist** (WEAKENED) — Pre-merge checklist reminder to verify reserve/record/release metering before merging AI-calling code. Weakened because Step 9L automates the same check nightly. Useful as follow-up once Step 9L is proven. Pick up in run 117+ if metering gaps persist after Step 9L is live.
- **Idea 3: os_tool_executions.py god class split** (SURVIVES) — 783L file, 30% over 600L threshold, handles tool execution / billing / state management (3 concerns). Stable for 4-5 days = good split window. Run 116 mandate: verify still stable, then split into `os_tool_executor.py`, `os_tool_billing.py`, `os_tool_state.py`.
- **Idea 5: Fitness trial-to-member conversion tracking** (not debated) — `conversion_events` table, `/api/conversions` endpoint, Fitness Dashboard page. Customer gap documented in `docs/dev-knowledge/customer-gaps.md`. Medium impact, low effort. Pick up when Fitness vertical gets focus.

## Rejected This Run
- (None killed in debate — only weakened/parked)

## Questions for Next Run
1. Did Step 9L fire on 2026-09-06 nightly? How many violations found?
2. Step 9J token budget: is it fixable with batch-limit logic, or does it need a separate nightly run?
3. os_tool_executions.py: still stable? If yes, proceed with split in run 116.
4. GH #684 SUPABASE_ACCESS_TOKEN: what's blocking Railway secret set?
5. GH #800 brain connector staleness: what's the path to resolution?
