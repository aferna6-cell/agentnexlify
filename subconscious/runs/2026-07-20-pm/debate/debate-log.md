# Debate Log — Run 100 (2026-07-20-pm)

Top 3 ideas ranked by impact: Idea 1 (MCP wiring), Idea 4 (plan-gating audit), Idea 2 (GH #399 runbook).

---

## Idea 1: Wire MCP Client Into Agent Execution Path

### Challenge
1. **Evidence strength**: Is this confirmed broken or just not observed? Maybe `os_thread_runner.py` dispatches through a different abstraction that eventually calls `mcp_client`.
2. **Timing**: PR #514 landed today (2026-07-20). Is the ink dry enough to wire the execution layer, or is there a pending follow-up PR?
3. **Blast radius**: Wiring into `agent_os_bridge.py` touches the production agent execution path. A bug here crashes all agent conversations for all tenants.
4. **Scope creep**: "Add import + dispatch helper" sounds small, but MCP tool execution needs: error handling, timeout, output schema validation, outbound guard integration, trace logging. This might be a multi-file change with migration.
5. **Is there a better idea**: The loop-health digest (Idea 5) has lower blast radius and addresses the #1 enterprise audit gap (observability), while MCP wiring addresses gap #4.

### Defend
1. **Confirmed broken by grep**: `grep -r "mcp_client" backend/` returns only `backend/routers/os_mcp.py` and `backend/services/mcp_client.py`. `os_thread_runner.py` and `agent_os_bridge.py` have zero references. No abstraction layer found. This is not conjecture.
2. **PR #514 explicitly shipped this as a feature**: The commit message and enterprise sprint notes say "native tool execution" is one of 7 features. Shipping configuration without execution makes the feature completely inert — tenants who configure MCP servers will see zero effect. Day-0 bug.
3. **Blast radius is manageable with proper scoping**: The fix is additive — a new dispatch branch in the existing tool-dispatch switch, behind a guard (`if tool_call.type == "mcp"`). The existing execution path is unchanged. `apply_outbound_guard` (already wired) provides the safety net.
4. **Scope is bounded**: The MCP client service already handles timeout, error handling, and output schema. The wiring is ~20-30 lines in `os_thread_runner.py` to detect MCP tool calls and route them through the existing `mcp_client.execute_tool()` interface.
5. **Day-0 bugs compound**: Every day this stays unwired, tenants who configured MCP tools get silent non-execution. They'll assume the feature is broken and distrust the platform.

### Verdict: SURVIVES
Evidence is strong (confirmed by grep), action is bounded (additive dispatch branch), impact is concrete (closes Day-0 execution gap for PR #514's flagship feature). Blast radius risk is real but mitigated by additive-only change.

---

## Idea 4: Audit Agent OS Plan-Gating on New PR #514 Routers

### Challenge
1. **Evidence gap**: We haven't actually grepped the PR #514 router files for `require_plan`. We're inferring the problem from historical patterns ("gating bugs happen"). This is pattern-based, not evidence-based.
2. **PR #514 was a large, deliberate sprint**: A 34-file, 3355-insertion PR likely had plan-gating in mind. The developer who wrote it (the subconscious itself, in run 99 instructions) was aware of gating rules.
3. **Low urgency compared to broken execution**: If plan-gating IS missing, it's a revenue leak — but it only leaks if `chatbot` tenants discover and use the `agent_os` endpoints. Those endpoints require agent configuration, which most `chatbot` tenants haven't done.
4. **Audit is a research task, not an implementation task**: The subconscious recommends but doesn't implement. An "audit and add missing gates" action is implementation work that should go through nightly-commit-review or compound-engineering.

### Defend
1. **Historical precedent**: CLAUDE.md explicitly notes "new gates → add to `backend/tests/test_plan_gating_new_plans.py`" as a mandatory step. This is a documented pattern because it has been missed before.
2. **PR #514 size increases risk**: 34-file PRs are where details get missed. The bigger the sprint, the more likely a per-router detail like `require_plan("agent_os")` was overlooked on one of the 7 new routers.
3. **Revenue impact is real**: A chatbot tenant ($19.99/mo) accessing agent_os features ($99.99/mo) without paying is $960/yr lost per tenant. If even 5 tenants exploit this gap, it's $4,800/yr before discovery.
4. **Audit is scoped**: The action is grep + verify + document missing gates in a new GitHub issue. Writing an issue is within subconscious scope. Implementation goes to nightly-commit-review or issue-to-pr-loop.

### Verdict: WEAKENED
Evidence is pattern-based, not confirmed. Action must be scoped to "verify via grep + create issue if gaps found", not "implement the gates" (that's implementation work). Lower priority than MCP wiring (confirmed Day-0 bug). Goes to parking lot.

---

## Idea 2: Document GH #399 Railway Token Rotation Steps in New Issue

### Challenge
1. **Not a code improvement**: Creating a GitHub issue is an operational action, not a code quality, workflow, or agent performance improvement. The subconscious loop is for software improvements, not ops runbook creation.
2. **Day 18+ without resolution suggests the fix isn't Claude's to give**: If #399 has been open 18+ days, the blocker is human action (someone needs to log into Railway and rotate the token). Documenting steps in a new issue doesn't solve the human bottleneck.
3. **Two issues for the same problem**: An existing issue (#399) already documents the expired token. Creating a second issue risks fragmentation.
4. **Scope conflict**: The SKILL.md says subconscious RECOMMENDS but does NOT implement. Creating GitHub issues IS implementation — it has real-world effects.

### Defend
1. **The current issue (#399) lacks remediation steps**: Day 18 with no human action suggests the issue doesn't give people enough information to act. A new issue with exact steps (what URL, what scope, what Railway var name) reduces the cognitive barrier to fixing it.
2. **Blocking 30 ai-ready issues is a compounding operational debt**: Every day without fix, the autonomous loop falls further behind. The cost isn't the expired token — it's the accumulation of un-processed issues in the backlog.
3. **docs/dev-knowledge/bug-patterns.md addition IS code**: Adding a runbook section to `bug-patterns.md` is a code change (documentation file edit), not just a GitHub comment.
4. **Compounding win**: A written procedure in `bug-patterns.md` prevents this exact 18-day stall from recurring. Worth more than the immediate fix.

### Verdict: WEAKENED
Core action (rotate the token in Railway) requires human access to Railway dashboard — beyond subconscious implementation scope. The documentation win (adding to `bug-patterns.md`) is valid but ancillary. Lower than MCP wiring. Goes to parking lot with revised scope: "add token rotation runbook to `bug-patterns.md`" only, not GitHub issue creation.

---

## Summary Table

| Idea | Verdict | Notes |
|---|---|---|
| Idea 1: MCP execution wiring | SURVIVES → **WINNER** | Confirmed bug, bounded action, high impact |
| Idea 4: Plan-gating audit | WEAKENED → parking lot | Pattern-based concern; scope to grep+issue only |
| Idea 2: GH #399 runbook | WEAKENED → parking lot | Revised scope: `bug-patterns.md` addition only |
| Idea 3: KB compile | Not debated | Operational; goes directly to parking lot |
| Idea 5: Loop-health digest | Not debated | Customer value; goes to parking lot |
