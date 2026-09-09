# Improvement Backlog — Run 118 (2026-09-09)

## Active

- **Split `os_tool_executions.py` god class** (783L → 3×~260L modules: dispatch/handlers/context). Governance-mandated run 118 candidate. Pure refactor, CI validates, stable window.

## Parking Lot (survived debate, not chosen)

- **Step 9M: KB autopopulate via MCP trigger** — replace broken `gh workflow run` path in Step 9G with `mcp__github__actions_run_trigger`. XS effort, operational. Blocked: human must add ANTHROPIC_API_KEY to GH Actions (#403) first. Activate once #403 resolved.
- **Step 9N: auto-fix test `__future__` annotations** — add `backend/tests/` to nightly annotation scan. GH #823 tracks 5 files. Nightly can self-implement as a LOW-risk autonomous fix. Activate on next nightly with clear mandate.
- **AI metering violation trend tracker** — append Step 9L violation count per run to `docs/dev-knowledge/ai-metering-trend.md`. S effort. Low urgency now that Step 9L is wired.
- **Step 9J token budget investigation** — profile which nightly step exhausts context before Step 9J checks all 19 Dependabot PRs. Many PRs now merging, may self-resolve.

## Rejected This Run

- **None killed outright** — all 5 ideas survive in some form. Top 3 debated; Idea 3 and 4 weakened to parking lot (not killed).

## Questions for Next Run

1. Has the os_tool_executions.py split been approved and implemented? Verify by checking if `os_tool_dispatch.py`, `os_tool_handlers.py`, `os_tool_context.py` exist in `backend/services/`.
2. Did the nightly fire Step 9L? How many violations were found vs. filed? Is the count trending down after the billing sprint?
3. GH #403 (ANTHROPIC_API_KEY in GH Actions): resolved? If yes, Step 9M is the next winner.
4. os_tool_executions.py: any new commits since 2026-08-30? If yes, split window may have closed.
5. Step 9J: are all 19 Dependabot PRs now checked per nightly, or still hitting token budget at 2?
