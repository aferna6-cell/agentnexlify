# Debate Log — Run 2026-09-11-pm (Run 120)

Top 3 ideas debated. Format: Challenge → Defend → Verdict.

---

## Idea 1: Step 9E Credential Expiry Early-Warning Escalation

### Challenge
"AUTOPILOT_GH_TOKEN is at 69d — 7 days to the 76d threshold. The current Step 9E already fires at 76d. Three consecutive nightlies logged this warning. Zero human action resulted. Why would an EARLIER warning (at days_remaining <= 10) produce different behavior than the current 76d warning? If the human didn't act on 3 warnings, they won't act on an earlier one either. And this is a 1st carry-forward — not even 2nd or 3rd. The urgency signal is weak."

### Defend
Three nightlies logged 'approaching threshold' — but Step 9E never filed a GH issue. It only logged to the nightly markdown file. The escalation path is missing: no GH issue means no email to subscribers, no assignee, no label, no audit trail. The carry-forward is about adding issue-filing (with dedup guard to comment on existing #399), not just an earlier log line. Additionally, days_remaining <= 10 fires at 66d — that fires TODAY for AUTOPILOT_GH_TOKEN at 69d. The alert should have fired 3 days ago. The mechanism is proven: Steps 9F/9G/9I/9J/9K all use this pattern (GH issue on threshold). The only thing broken is Step 9E lacks the GH issue step.

### Verdict
**SURVIVES → WINNER**

Evidence: Step 9E confirmed to lack GH issue filing (grep returns nothing for 'add_issue_comment' in Step 9E block). Mechanism proven by peer steps. AUTOPILOT_GH_TOKEN expires 2026-10-02 — if not rotated, loop dies. Run 119 winner same recommendation. 1st carry-forward, autonomous-executable fires at run 121 (3rd consecutive carry). Confidence: HIGH.

---

## Idea 2: Fix Step 9G — Replace gh CLI with mcp__github__actions_run_trigger

### Challenge
"Step 9G is broken — gh CLI unavailable in CCR sessions, confirmed runs 115-119. BUT: the root cause of the KB stale problem is ANTHROPIC_API_KEY missing from GH Actions (GH #403). Even if you trigger kb-autopopulate.yml via MCP, the workflow will still fail because the API key isn't there. The fix is symptom-level: replacing gh with MCP trigger doesn't fix the underlying key problem. And mcp__github__actions_run_trigger availability in nightly sessions is UNVERIFIED."

### Defend
Two separable outcomes: (1) if ANTHROPIC_API_KEY is now available (unknown — GH #403 may have been resolved), MCP trigger re-enables KB autopopulate entirely. (2) Even if key is still missing, MCP trigger gives Step 9G the actual GH Actions error message (vs current 'gh CLI not available' non-error) — better diagnostic. Current state: Step 9G silently fails with no meaningful error. KB at 16 days stale. The fix is XS effort and strictly better than current state.

### Verdict
**WEAKENED — parking lot (not this run)**

Idea has merit but WEAKENED by two factors: (1) MCP tool availability in nightly sessions unverified — if mcp__github__actions_run_trigger absent, Step 9G degrades to 'ToolSearch returned nothing', same net result. (2) Idea 1 (Step 9E) is higher urgency — token expiry causes loop death vs KB staleness causes answer degradation. AUTOPILOT_GH_TOKEN expires 2026-10-02 (21 days). Park Idea 2 for run 121.

---

## Idea 3: Step 9D Stalled Issues Auto-Nudge (14d threshold)

### Challenge
"Three ai-ready issues stalled (GH #728 10d, #669 22d, #660 27d). GH #669 is a real security gap (95 routers missing block_demo_role). Automated nudge comment would draw attention. XS effort — just add a comment step to Step 9D."

### Defend
Historical evidence: GH #413 received 5 automated comments from this same nudge mechanism. Zero human action resulted. The root cause of the stall is AUTOPILOT_GH_TOKEN expiry preventing the autopilot loop from executing. Comments on the issues don't fix the token. And Idea 1 (Step 9E) already addresses the root cause — if Step 9E fires, human rotates the token, autopilot loop resumes, stalled issues get picked up automatically. Implementing Idea 3 builds on a mechanism proven to have near-zero ROI, while failing to address root cause.

### Verdict
**KILLED**

Root cause of stall is AUTOPILOT_GH_TOKEN. Idea 1 addresses root cause. Idea 3 addresses symptoms with proven-ineffective mechanism. Eliminate.

---

## Debate Summary

| Idea | Verdict | Disposition |
|------|---------|-------------|
| 1 — Step 9E early warning | SURVIVES | WINNER |
| 2 — Step 9G MCP trigger | WEAKENED | Parking lot → run 121 |
| 3 — Step 9D stalled nudge | KILLED | Eliminated |
| 4 — os_tool_executions split | DEFERRED | Stability window broken (modified 2026-09-11) |
| 5 — governance schema drift | WEAKENED | Low urgency, parking lot |
