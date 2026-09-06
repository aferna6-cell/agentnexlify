# Debate Log — Run 117 (2026-09-06-pm)

Top 3 ideas ranked by impact: Idea 1 (Step 9L SKILL.md), Idea 2 (Step 9G cloud fix), Idea 3 (os_tool_executions.py split).

---

## Idea 1: Step 9L SKILL.md block

### Challenge Round 1
**Objection:** `check_ai_metering.py` was committed TODAY (1c5b749). Has it been validated in the repo's real backend? The 30+ violations could include false positives — functions that ARE metered via a wrapper not recognized by the AST scanner.

**Defense:** 325 lines of tests shipped with the detector (tests/test_check_ai_metering.py + two scope fixtures). Tests cover all 11 regression fixtures defined in run 115 winning-concept.md including alias-resolved calls, METERED_WRAPPERS, and per-function exemption markers. The scan ran live this session and output is factual file:function:line paths — spot-checking `bids.py:ai_generate_bid:295` and `menu.py:import_menu_from_website:210` shows these are real Claude-calling functions without `Depends(ai_usage_guard)`. False-positive risk is low because guard detection requires Depends keyword in function signature defaults (router) or reserve/record/release in body (service) — not heuristic.

### Challenge Round 2
**Objection:** 30+ issues filed in one nightly run could flood the tracker and create noise. GH #399 (AUTOPILOT_GH_TOKEN) is expired — the issue-to-pr-loop is stalled. Filing 30 issues no one can action is waste.

**Defense:** Step 9L uses dedup guard (search_issues before filing). Many of the 30 violations may already have GH issues from the 7-PR emergency retrofit sprint (#792-#799). Actual net-new issues will be a subset. Also, Step 9I (block_demo_role) has been filing security issues since run 107 without tracker flooding — pattern is proven. Even with GH #399 stalled, the issues create visibility and can be manually actioned.

### Challenge Round 3
**Objection:** Has something similar been tried before for billing guards? Is this repeating a rejected path?

**Defense:** No equivalent in rejected_paths or frozen_ideas. The closest prior work was the 7-PR emergency sprint (#792-#799) which was REACTIVE — this is the PREVENTIVE equivalent. Step 9I (block_demo_role) is the structural precedent: same grep-then-file mechanism, same nightly step pattern. Step 9I has been in production 3+ weeks with zero false-positive issues. Step 9L extends the proven pattern to a second guard class.

**Verdict: SURVIVES** — Evidence strong (30+ violations confirmed by live scan), mechanism proven (Step 9I analogue), dedup guard mitigates flood risk, governance mandate active at run 117.

---

## Idea 2: Step 9G cloud fix (gh CLI → mcp__github__actions_run_trigger)

### Challenge Round 1
**Objection:** The ROOT CAUSE of KB staleness is GH #403 (ANTHROPIC_API_KEY missing from GH Actions). Even with a fixed trigger, the kb-autopopulate workflow fails and KB stays stale. Fixing the trigger mechanism doesn't fix the underlying problem.

**Defense:** True — but fixing the trigger changes the failure mode from SILENT to OBSERVABLE. Currently: trigger fails, no workflow run created, no diagnostic URL, GH #403 gets no new signal. After fix: trigger fires, workflow run created, run fails with specific error, Step 9G comments on GH #403 with the run URL + exact error. This surfaces the real blocker (ANTHROPIC_API_KEY) in an actionable way. Also: if the human adds ANTHROPIC_API_KEY to GH Actions at any point, KB self-heals immediately.

### Challenge Round 2
**Objection:** Is `mcp__github__actions_run_trigger` verified available in nightly sessions? The nightly-commit-review runs as a headless Routine — does it have GitHub MCP access?

**Defense:** The nightly-commit-review SKILL.md extensively uses `mcp__github__*` tools (search_issues, issue_write, add_issue_comment, list_pull_requests, search_pull_requests). All those calls work in headless nightly sessions. `mcp__github__actions_run_trigger` is in the same MCP server. This assumption is reasonable, but not 100% confirmed — the nightly logs don't show a prior `actions_run_trigger` call.

### Challenge Round 3
**Objection:** Compared to Idea 1 (30+ billing violations, immediate risk), is fixing the KB trigger really the highest-leverage thing? KB staleness is a quality degradation; unguarded billing is revenue/compliance risk.

**Defense:** This objection is correct — Idea 2 is secondary to Idea 1. The KB fix is operational hygiene; the billing gaps are financial exposure. If choosing between the two, Idea 1 wins.

**Verdict: WEAKENED** — Legitimate fix, valuable diagnostic improvement, but secondary to Idea 1 in current priority stack. Demoted to parking lot. S effort, single SKILL.md edit — could be run 118 winner.

---

## Idea 3: os_tool_executions.py god class split

### Challenge Round 1
**Objection:** Is the evidence strong enough that this should happen NOW? The file is 783L but has been stable 8+ days. M9 sprint is active but may not be touching this file directly.

**Defense:** Governance explicitly listed this as run 117 candidate since run 115. Rule 9 fires at 600L. The M9 sprint's `shadow_planner.py` is in `os_workflows/` — adjacent to `os_tool_executions.py`. Any M9 PR that adds tool execution features will extend this file further. Splitting now (while stable) is cheaper than splitting later (during active M9 work).

### Challenge Round 2
**Objection:** This is M effort, requires understanding all callers, and is NOT autonomous-executable. The subconscious recommends but cannot implement. A human needs to split a 783-line file with potentially many callers. Is this a good use of the recommendation slot?

**Defense:** The subconscious recommendation slot should go to the highest-value item. Idea 1 (Step 9L SKILL.md) is higher value (billing exposure, proven mechanism, S effort, autonomous-executable). The god class split is valuable but can wait for run 118 when Step 9L is confirmed in SKILL.md.

### Challenge Round 3
**Objection:** Has this been in the parking lot long enough? Runs 115, 116, 117 all had it as parking lot. Does repeated non-selection indicate lower real priority?

**Defense:** It was always deferred because a higher-priority item (Step 9L) was pending. Once Step 9L is in SKILL.md, the god class split becomes the natural next winner. This is the correct sequencing, not deprioritization.

**Verdict: WEAKENED** — High value, correct timing, but M effort and secondary to Step 9L's autonomous-executable billing fix. Parking lot with clear run 118 promotion condition: Step 9L confirmed present in SKILL.md.

---

## Synthesis

| Idea | Verdict | Disposition |
|------|---------|-------------|
| Step 9L SKILL.md block | SURVIVES | **WINNER** |
| Step 9G cloud fix (gh CLI → MCP) | WEAKENED | Parking lot (run 118 candidate) |
| os_tool_executions.py god class split | WEAKENED | Parking lot (run 118 candidate if Step 9L confirmed) |
| Step 9J token-budget fix | Not debated | Parking lot |
| check_ai_metering.py CI gate | Not debated | Rejected (needs suppression baseline first) |

**Winner: Step 9L SKILL.md block** — Governance mandate active (autonomous_executable_run: 117), detector confirmed working (30+ violations), mechanism proven (Step 9I analogue), S effort.
