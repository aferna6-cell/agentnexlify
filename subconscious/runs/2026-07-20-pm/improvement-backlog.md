# Improvement Backlog — 2026-07-20-pm

## Active
- Wire `mcp_client.py` into agent execution path (`os_thread_runner.py` + `agent_os_bridge.py`) — closes Day-0 execution gap from PR #514's MCP feature

## Parking Lot (survived debate but not chosen)
- **Plan-gating audit for PR #514 routers**: grep new `agent_os` routers for `require_plan` decorator; create issue for any missing gates; add tests to `test_plan_gating_new_plans.py`. Low urgency but historically missed — worth a targeted grep before next sprint.
- **GH #399 token rotation runbook**: Add exact Railway AUTOPILOT_GH_TOKEN rotation steps to `docs/dev-knowledge/bug-patterns.md` under "Operational: Expired Tokens". Scope limited to documentation edit only (human must rotate in Railway UI).
- **KB compile for enterprise audit content**: Copy `audits/audit-enterprise-agent-suites-2026-07-20.md` to `knowledge-base/raw/ai-llm/` and run `kb-autopopulate.sh` to ingest. Step 9F in nightly will trigger this anyway on 2026-07-21 if KB remains at 7-day threshold.
- **Loop-health digest integration**: Wire `GET /api/v1/admin/loop-health` signals (refusal rate, guardrail trips, eval pass rate) into `scripts/daily/` morning report for tenant owners. Closes observability gap #1 from enterprise audit.

## Rejected This Run
- None killed outright. Ideas 4 and 2 weakened and scoped down, not killed. Both remain viable with narrowed scope.

## Questions for Next Run
1. After MCP execution wiring ships, does the `os_run_trace.py` router correctly capture MCP tool call events in the per-run timeline? If not, trace completeness gap needs its own run.
2. Did the plan-gating grep on PR #514 routers reveal any missing `require_plan("agent_os")` decorators? If yes, that becomes the immediate next winner.
3. GH #399: Has the token been rotated? If still expired on day 25+, this needs escalation to a direct note to the human owner — not another subconscious parking lot entry.
