# Candidate Ideas — Run 100 (2026-07-20-pm)

## Idea 1: Wire MCP Client Into Agent Execution Path
**Evidence:** PR #514 (b17ed5c, 2026-07-20) shipped `backend/services/mcp_client.py` with full MCP tool-call infrastructure. Grep confirms `mcp_client` is imported ONLY by `backend/routers/os_mcp.py` (admin config router). Neither `backend/services/os_thread_runner.py` nor `backend/services/agent_os_bridge.py` import or call it. Enterprise audit (PR #513, 2026-07-20) ranked "MCP tool execution from within agent conversations" as capability gap #4 vs Amazon/Microsoft/Google/Salesforce competitors. Configuration layer is complete (tenants can register MCP servers via admin UI); execution layer is missing. Agents configured with MCP tools cannot call those tools during conversations.
**Action:** Add `mcp_client` import to `os_thread_runner.py`; implement `_execute_mcp_tool_call(tool_name, tool_input, tenant_mcp_config)` helper; hook it into the existing tool-dispatch branch in `agent_os_bridge.py` alongside `apply_outbound_guard`. Add migration if MCP call log needs schema change.
**Impact:** Closes critical execution gap that makes PR #514's MCP feature completely inert. Unlocks real tool-use for Agent OS tenants — calendar, CRM, custom APIs called during widget conversations.
**Category:** agent_performance

---

## Idea 2: Document GH #399 Railway Token Rotation Steps in New Issue
**Evidence:** `subconscious/state/governance.json` run_100_mandate item 4: "GH #399 AUTOPILOT_GH_TOKEN expired — Day 18+ with 30 ai-ready issues blocked. Secondary remediation." Memory run 99 confirms still open. The `issue-to-pr-loop` skill polls assigned GitHub issues every 15 min but cannot execute because the auth token is dead. 30 issues labeled `ai-ready` are queued. Day 18+ = no forward movement on the entire autonomous dev loop that processes bug fixes and small features. No fix instructions exist in any file; there is no canonical procedure for Railway secret rotation documented in the codebase.
**Action:** Create a new GitHub issue (not comment on #399) titled "UNBLOCKS LOOP: Rotate AUTOPILOT_GH_TOKEN in Railway + re-verify issue-to-pr-loop" with exact steps: (1) generate new PAT at github.com/settings/tokens with `repo` + `workflow` scopes, (2) set `AUTOPILOT_GH_TOKEN=<new>` in Railway dashboard under Variables, (3) redeploy or restart service to pick up the new env var, (4) verify by running `gh issue list --label ai-ready` from the autopilot service. Also add these steps to `docs/dev-knowledge/bug-patterns.md` under "Operational: Expired Tokens".
**Impact:** Unblocks the entire autonomous dev loop. 30 queued ai-ready issues can progress. Prevents Day 18+ stalls from recurring without a documented runbook.
**Category:** operational

---

## Idea 3: Trigger KB Compile to Ingest Enterprise Audit Content
**Evidence:** `knowledge-base/log.md` shows last successful compile 2026-07-13 20:00 — exactly 7 days ago as of 2026-07-20. Enterprise competitive audit PR #513 (2b3116a) landed 2026-07-20 with 12 capability gaps and 7 adopt-cheaply recommendations vs Amazon Quick Suite, Microsoft Copilot Studio, Google Gemini Enterprise Agent Platform, Salesforce Agentforce. This content lives in `audits/audit-enterprise-agent-suites-2026-07-20.md` but is NOT in the knowledge base. Tenant KB responses to questions about competitive positioning, feature gaps, or enterprise requirements cannot draw on this fresh analysis. `knowledge-base/INDEX.md` header shows last compiled 2026-05-05 (stale), meaning the catalog is 75 days behind.
**Action:** Copy/symlink `audits/audit-enterprise-agent-suites-2026-07-20.md` to `knowledge-base/raw/ai-llm/enterprise-audit-2026-07-20.md`. Run `bash scripts/daily/kb-autopopulate.sh` to trigger compile. Verify `knowledge-base/log.md` shows a 2026-07-20 entry and that `knowledge-base/INDEX.md` updates.
**Impact:** Fresh competitive intelligence available for agent responses. Step 9F (KB staleness check in nightly) will pass tomorrow. Compounds: every future KB compile builds on this baseline.
**Category:** operational

---

## Idea 4: Audit Agent OS Plan-Gating on New PR #514 Routers
**Evidence:** PR #514 (b17ed5c) added 7 enterprise-tier features: conversation memory (persistent context), real-time streaming, native tool execution, knowledge base integration, multi-agent coordination, MCP client, and advanced analytics. Each has a new backend router. Enterprise audit confirms these map to `agent_os` plan tier only. However, the codebase historically has plan-gating bugs — CLAUDE.md critical rules note "new gates → add to `backend/tests/test_plan_gating_new_plans.py`". No commit in PR #514's diff has been confirmed to add those gating tests. If any new router lacks `require_plan("agent_os")` enforcement, `chatbot`-tier tenants could access enterprise-only features at no extra charge.
**Action:** Grep all new router files from PR #514 for `require_plan` decorators. For any missing, add the `agent_os` tier gate. Add corresponding tests to `backend/tests/test_plan_gating_new_plans.py` for each new endpoint. Run tests.
**Impact:** Revenue protection: closes potential billing bypass where `chatbot` ($19.99/mo) tenants access `agent_os` ($99.99/mo) features. Security/compliance: enterprise features need isolation guarantees.
**Category:** code_health

---

## Idea 5: Surface Loop-Health Digest Signals in Morning Owner Report
**Evidence:** PR #515 (mentioned in run 99 memory) added guardrail/eval signals to the admin endpoint. `backend/services/kb_evals.py` is confirmed wired (called from `tenant_kb.py:247`). The `nightly-commit-review SKILL.md` and morning digest scripts run daily but there is no evidence these new eval/guardrail signals are surfaced in the `scripts/daily/` output that tenant owners see. Customer gaps doc lists "lead source analytics (Low effort)" as open, suggesting visibility gaps are recurring. Without surfacing loop health (refusal rates, guardrail trips, eval failures) in the morning digest, tenant owners cannot detect degraded agent behavior without manually querying the admin endpoint.
**Action:** Read `scripts/daily/kb-autopopulate.sh` and the morning report script. Add a section that queries `GET /api/v1/admin/loop-health` (or equivalent) and appends refusal rate, guardrail trip count, eval pass rate to the digest email/output. Cap to last 24h window. If the endpoint is not yet stable, add a TODO issue instead.
**Impact:** Tenant owners get proactive visibility into agent health. Reduces support tickets about "bot acting weird." Closes a piece of the observability gap ranked #1 in the enterprise audit. Low implementation effort (endpoint exists, just needs to be wired into the digest).
**Category:** customer_value
