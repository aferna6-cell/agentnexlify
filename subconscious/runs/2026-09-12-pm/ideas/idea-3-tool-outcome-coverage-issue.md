# Idea 3: File GH Issue — Tool Outcome Coverage Audit (Agent OS)

**Category:** code_health
**Effort:** XS (filing a GH issue)
**Confidence:** MEDIUM

## Evidence
- commit adb31f9 (#844, 2026-09-11): "fix(agent-os): surface send_email approval failure outcomes" — added HTTP 502 paths for `outcome.get("unknown")` and `outcome.get("failed")` that were missing.
- commit 0605d0f (#841, 2026-09-11): "fix(agent-os): terminalize deterministic Gmail send failures" — added `KnownGmailSendFailure` exception to route failures through `record_execution_outcome`.
- Same class: two independent commits in one day, both fixing incomplete outcome routing in the email approval pipeline.
- Pattern matches Step 9I (demo-role gaps), Step 9L (AI metering gaps) — class problems caught and fixed reactively.
- os_tool_executions.py handles calendar, invoice, SMS, contact, and email tools. If email needed two fixes, adjacent tools may have incomplete outcome routing.

## Action
File GH issue:
- Title: "audit: tool outcome coverage for Agent OS approval pipeline (#841/#844 pattern)"
- Labels: `code_health`, `agent_os`, `ai-ready`
- Body: describe pattern from #841/#844, list tools to audit (calendar, invoice, SMS, contact), ask for systematic review of `record_execution_outcome` call coverage per tool.

## Impact
- Prevents next reactive fix cycle for same class bug in calendar/SMS/invoice tools.
- ai-ready label means issue-to-pr-loop picks it up once AUTOPILOT_GH_TOKEN is rotated.
- Effort XS (just filing issue, not implementing the audit).
