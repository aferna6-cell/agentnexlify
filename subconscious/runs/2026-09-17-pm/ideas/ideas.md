# Candidate Ideas — Run 2026-09-17-pm (Run 121)

Generated from evidence: nightly-2026-09-17, git log (3 days), governance.json state, memory.jsonl

---

## Idea 1 — Step 9E 10-Day Early Warning Window (2nd Carry-Forward)
**Category:** workflow_efficiency / operational
**Effort:** XS (SKILL.md block edit)
**Evidence:**
- AUTOPILOT_GH_TOKEN: 75 days since rotation (2026-09-17). Threshold 76d fires tomorrow.
- 10-day early warning NOT implemented (grep days_remaining/<=10 = 0 results in Step 9E).
- Step 9E fires at ≥76d but fires at 90d+ only — the 15-day remaining window that nightly-09-17 mentions is already inside the threshold. Existing logic IS firing soon (tomorrow).
**Urgency assessment:** WEAKENED. Threshold fires tomorrow — existing logic handles AUTOPILOT_GH_TOKEN. Future value intact for next rotation cycle but current urgency is diminished.
**Status:** 2nd carry-forward from run 119. Parking lot.

---

## Idea 2 — Fix Step 9G: Replace `gh workflow run` with `mcp__github__actions_run_trigger`
**Category:** workflow_efficiency / operational
**Effort:** XS (SKILL.md block edit)
**Evidence:**
- Step 9G uses `gh workflow run kb-autopopulate.yml` — broken since ~run 107 (2026-08-19). gh CLI unavailable in cloud/CCR sessions.
- nightly-2026-09-17.md: Step 9G ABSENT from output. KB 22 days stale (last: 2026-08-26).
- `mcp__github__actions_run_trigger` confirmed in deferred tools list for this session type.
- GH #403 tracks KB staleness (human-action-required: set ANTHROPIC_API_KEY in Actions secrets).
- Step 9G silently failing means no escalation pressure on #403 for 30 days.
- Fix restores self-healing trigger and escalation path, even if Actions job itself still fails.
**Autonomous-executable channel:** XS SKILL.md edit, same pattern as Steps 9F/9G/9I/9J/9K/9L.
**Status:** NEW this run. HIGH confidence winner.

---

## Idea 3 — Split os_tool_executions.py God Class (783L)
**Category:** code_health
**Effort:** M (code refactor, 3-4 new files)
**Evidence:**
- os_tool_executions.py at 783 lines. Rule 9: factor god classes at 600+ lines.
- 4th consecutive subconscious run mentioning this file (runs 117-121).
- File has been stable 14+ days — safe window to refactor without conflicting with active work.
- No AI usage guard violation in this file (it predates the check_ai_metering.py era).
- Splitting: tool_dispatching.py, tool_validation.py, tool_result_processing.py, os_tool_executions.py (thin coordinator).
**Risk:** Medium. Requires updating all import call sites. No schema changes.
**Status:** Recurring mention. Actionable but M effort — blocked by "human approves" gate for non-XS changes.

---

## Idea 4 — Step 9L Closed-Issue Dedup Guard
**Category:** workflow_efficiency / operational
**Effort:** XS (SKILL.md guard condition)
**Evidence:**
- GH #875 (AI metering tracking) closed as "duplicate" by owner 2026-09-16. Owner has separate tracking.
- nightly-2026-09-17: Step 9L logs "Not filing a new issue (would become noise)" — manual workaround in place.
- If Step 9L continues to find violations, it may file a new issue next run without checking for the owner's separate tracker.
- Pattern: one closure cycle only — insufficient evidence that the current workaround will fail.
**Urgency assessment:** WEAKENED. One cycle only; wait for 2nd cycle to confirm recurring problem.
**Status:** Parking lot.

---

## Idea 5 — Consolidated Dependabot Major-Version Tracking Issue
**Category:** code_health / operational
**Effort:** XS (file one GH issue via MCP)
**Evidence:**
- nightly-2026-09-17: 5 Dependabot PRs open, all stalled — 4 major version bumps (React 18→19 x2, vitest 4→5, mcp 2→3), 1 CI unstable.
- No single tracking issue. Each nightly just reports "skipped (major version bump — human review required)" without aggregating.
- A consolidated issue would give the owner a single place to acknowledge and prioritize.
- Risk: owner may already have a mental queue. Low friction to file.
**Status:** Useful but LOW leverage compared to fixing an actively broken system (Step 9G).

---

## Summary Ranking

| Rank | Idea | Category | Effort | Status |
|------|------|----------|--------|--------|
| 1 | Fix Step 9G: gh→mcp tool | workflow_efficiency | XS | NEW — WINNER |
| 2 | Split os_tool_executions.py | code_health | M | Recurring, parking lot |
| 3 | Step 9E early warning | workflow_efficiency | XS | Carry-forward, weakened |
| 4 | Dependabot tracking issue | code_health | XS | Low leverage |
| 5 | Step 9L closed-issue dedup | workflow_efficiency | XS | Insufficient evidence |
