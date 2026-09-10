# Improvement Backlog — Run 118 (2026-09-10)

## Active
- **os_tool_executions.py god class split** — Split 783L file into store/executor/approval_handler. Governance mandate binding (runs 116+117). Step 9L confirmed. M effort. Human implementation required. Backward-compat shim approach removes import-site risk.

## Parking Lot (survived debate but not chosen)

- **CI gate for new unmetered AI calls** — Add `KNOWN_VIOLATIONS` allowlist to `check_ai_metering.py` + GitHub Actions workflow. PR #834 proves the allowlist-CI pattern works. S effort. Run 119 winner if god class split implemented. Requires revisit of run 117 kill (new evidence: PR #834 precedent).

- **Step 9J reorder: move to position 2 in nightly** — 17/19 Dependabot PRs still skipped due to token budget. Reorder Step 9J immediately after commit review (before Steps 9C-9K). S effort. Run 119 candidate.

- **Step 9G cloud trigger fix** — Replace `gh workflow run` with `mcp__github__actions_run_trigger` so KB autopopulate trigger works in cloud sessions. KB 15d stale. S effort. Operational compound fix.

- **AI-to-human handoff** — Critical for all industries per customer-gaps.md. Architecture: trigger words → owner notification → transcript handoff. M effort. Run 120+ candidate after core metering/health gaps resolved.

## Rejected This Run

- None (all 5 ideas survived initial filter)
- Debate killed: CI gate was previously killed in run 117 but REVIVED in run 118 with new evidence (PR #834). Not a new rejection — moved to parking lot.

## Questions for Next Run

1. Has the os_tool_executions.py split been implemented? (`wc -l backend/services/os_tool_executions.py` — should be dramatically lower, or file split confirmed by ls)
2. Step 9L first-nightly output: how many of the 30 violations were dedup-skipped vs. new GH issues filed?
3. CI gate for AI metering (parking lot #1): still highest-leverage next step? Or did metering sprint clear enough violations to change the calculus?
4. Step 9J still skipping 17/19? Or has reorder been applied and throughput improved?
5. GH #800 (SUPABASE_ACCESS_TOKEN brain connector): still open?
