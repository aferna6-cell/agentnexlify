# Improvement Backlog — Run 2026-09-11-pm (Run 120)

## Active (recommended, pending approval)

### Step 9E: Credential expiry early-warning + GH issue filing
- **Category:** workflow_efficiency / operational
- **Effort:** XS
- **File:** `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block
- **Status:** 1st carry-forward. Autonomous-executable at run 122 (3rd consecutive carry).
- **Urgency:** HIGH — AUTOPILOT_GH_TOKEN expires 2026-10-02 (21 days)

---

## Parking Lot (validated, waiting for window)

### Step 9G: Replace gh CLI with mcp__github__actions_run_trigger
- **Category:** operational
- **Effort:** XS
- **Why parked:** MCP tool availability in nightly sessions unverified. Weakened by uncertain root cause (ANTHROPIC_API_KEY in GH Actions #403).
- **Revisit:** Run 121. Verify mcp__github__actions_run_trigger availability via ToolSearch first.

### governance.json `verified_date` field (Idea 5)
- **Category:** workflow_efficiency
- **Effort:** XS
- **Why parked:** Low urgency vs credential expiry. Step 9L stale flag fix included in this run's governance.json update.
- **Revisit:** Run 122 if mandate check still shows stale flags accumulating.

---

## Deferred (not stable, revisit later)

### os_tool_executions.py god class split (Idea 4)
- **Category:** code_health
- **Effort:** L
- **Why deferred:** 783L (threshold 600L) — 4th consecutive flag. BUT commit adb31f9 (2026-09-11, today) modified the file. Stability window broken. Require 5+ days with no changes.
- **Revisit:** Run ~125 (check `git log --oneline -1 backend/services/os_tool_executions.py` — if last commit >5d ago, re-evaluate).

---

## Killed (do not re-propose without new evidence)

### Step 9D stalled issues auto-nudge
- **Reason:** Mechanism proven ineffective (GH #413: 5 automated comments, zero human action). Root cause of stall is AUTOPILOT_GH_TOKEN expiry — token fix (Idea 1) addresses root cause directly.
- **Frozen:** Yes. Re-open only if: (1) Step 9E implemented + token rotated, (2) loop running again, (3) issues still stalled due to different root cause.

---

## Frozen Ideas (do not re-propose)

- **ai_human_handoff:** frozen by governance. High complexity, not aligned with current phase. See `frozen_ideas` in governance.json.
