# Improvement Backlog — Run 2026-09-12-pm (Run 122)

## Active (current winner + parking lot)

### [WINNER] Step 9E: Threshold Fix + days_remaining Display
- **Effort:** XS
- **File:** `.claude/skills/nightly-commit-review/SKILL.md` lines ~289, ~298, ~300
- **Urgency:** HIGH — AUTOPILOT_GH_TOKEN expires 2026-10-02
- **Change:** Replace `days_since_rotation >= 76` with `days_remaining = interval_days - days_since_rotation; if days_remaining <= 14`. Add countdown to log line and GH comment.

### [PARKING LOT] Step 9J: Cap search_pull_requests to limit=5
- **Effort:** XS
- **File:** `.claude/skills/nightly-commit-review/SKILL.md` Step 9J block
- **Evidence:** 17/19 PRs skipped due to token budget (runs 115-117, plus run 121 nightly found 19 PRs again)
- **Fix:** `limit=5` + `created_at asc`. Promote to winner at run 123.

### [PARKING LOT] Step 9G: MCP trigger replacement (run 121 winner)
- **Status:** Recommendation from run 121. Verify `mcp__github__actions_run_trigger` availability in nightly CCR before implementing.
- **Blocker:** GH #403 (ANTHROPIC_API_KEY missing) is separate from trigger-path fix.

### [CONSIDER] File GH Issue — Tool Outcome Coverage Audit
- **Effort:** XS (issue filing only)
- **Evidence:** #841 + #844 both fixed email approval outcome routing same day
- **Note:** File with `code_health`, `agent_os`, `ai-ready` labels when opportunity arises.

---

## Deferred

### os_tool_executions.py god class split
- **Effort:** M
- **Reason:** Modified again (adb31f9, 2026-09-11). Needs 5+ days stability.

### SSRF redirect hop audit
- **Effort:** S
- **Reason:** Single-commit evidence. Lower priority than credential expiry.

### Skill freshness check / last_verified frontmatter
- **Effort:** M
- **Reason:** Low urgency, M effort, no automated verification path.

---

## Frozen

### ai_human_handoff
- Frozen per governance.json. Do not re-surface.

---

## Governance notes

- Run 122 total_runs: 122
- Active direction: Step 9E threshold fix (from mandate item 4 of run 121)
- Next winner candidate: Step 9J (limit=5) once Step 9E threshold fix lands
- AUTOPILOT_GH_TOKEN expiry: ~2026-10-02 — rotate soon
