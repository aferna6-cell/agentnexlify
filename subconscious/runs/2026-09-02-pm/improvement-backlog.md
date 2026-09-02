# Improvement Backlog — Run 115 (2026-09-02-pm)

## Active
- **Step 9J Diagnostic Enhancement** — Add "Step 9J: N Dependabot PRs found" log line before skip decision in nightly-commit-review SKILL.md Step 9J block (~3-line edit, autonomous-executable)

## Parking Lot (survived debate but not chosen)

- **Step 9L: Per-Tenant Widget Health Alert** — Nightly query `widget_configs` for tenants last active >7d, file weekly GH issue. HIGH value (prevents Keys Koffee–class silent churn). BLOCKED: Supabase MCP unavailable in headless sessions. Revisit when headless DB access is unblocked or a validated REST pattern exists.

- **os_tool_executions.py God Class Split** — 775 lines, 3 concerns (persist / apply / approve-reject). Split into `os_persist.py`, `os_apply.py`, `os_approval.py`. BLOCKED: 2 commits since 2026-08-30, stability threshold (4d+ clean) not met. Recheck run 116.

## Rejected This Run
- None killed in debate (all 3 debated ideas survived with varying verdicts).

## Not Debated (de-prioritized)
- **M9.2 Schema Migration Guard** — File `migrations/NNN_m9_workflow_state.sql` before M9.2 backend work. Implementation task, not subconscious scope. Human should execute directly.
- **Step 9M: SUPABASE_ACCESS_TOKEN Escalation** — Add nightly escalation step if brain connector stale >7d. Viable candidate for run 116/117 if GH #684 remains unresolved.

## Questions for Next Run (116)
1. Did nightly-2026-09-03 show "Step 9J: N Dependabot PRs found" — confirming the fix was implemented and fired?
2. os_tool_executions.py: 0 commits since 2026-09-02 (4d+ clean window)?
3. GH #684 SUPABASE_ACCESS_TOKEN: resolved?
4. M9.2 persistence engine schema migration filed?
5. Step 9L: any update on Supabase MCP headless access?
6. Stale subconscious PRs: count approaching escalation threshold?
