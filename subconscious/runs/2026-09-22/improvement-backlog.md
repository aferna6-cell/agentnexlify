# Improvement Backlog — Run 2026-09-22 (Run 125)

## Active (current winner)

### Step 9E: 10-Day P0 Credential Expiry Escalation Tier
- **Status:** Recommended (6th carry-forward). Autonomous-executable mandate passed at run 122. Task prompt prevents execution.
- **Action:** Edit Step 9E in `.claude/skills/nightly-commit-review/SKILL.md` to add P0 sub-step for days_remaining ≤ 10.
- **Urgency:** CRITICAL — P0 threshold fires today (2026-09-22). Token expires 2026-10-02.
- **Bonus action:** File P0 GH issue for AUTOPILOT_GH_TOKEN directly (title: "P0: AUTOPILOT_GH_TOKEN expires 2026-10-02 (10 days) — rotate now", labels: human-action-required, ops, P0).

---

## Parking Lot (deferred, not rejected)

### Step 9G: gh CLI → MCP Fix for KB Autopopulate
- **Carry-forward count:** 2 (runs 124–125)
- **Evidence:** `gh workflow run` bash command broken in CCR. KB 27 days stale (last: 2026-08-26). `mcp__github__actions_run_trigger` confirmed available.
- **Deferred:** Causally downstream of credential health. Token expiry kills MCP auth too. Run 126 candidate after credential rotation.
- **Action:** Replace bash `gh` line in Step 9G with `mcp__github__actions_run_trigger` call.

### os_tool_executions.py Split
- **Carry-forward count:** 6 (runs 119–125)
- **Evidence:** 783 lines (god-class threshold 600L). No recent commits touching it.
- **Deferred:** M effort, should follow feature-wave quiescence. Run 127+ candidate.
- **Action:** Read file, propose 2–3 module split, update all import call sites.

### Step 9M: AI Metering Violation Trend Tracker
- **Carry-forward count:** 0 (new this run)
- **Evidence:** GH #827 open, 45 violations. Step 9L counts but no delta tracking.
- **Deferred:** Low urgency vs credential expiry crisis.
- **Action:** After Step 9L count check, compute delta vs prior-day count, append trend line to GH #827 comment.

---

## Rejected / Frozen

### ai_human_handoff
- **Status:** FROZEN (rejected 3+ times, per governance.json)
- **Do not propose again.**

---

## Completed (recent, for context)

- **Step 9K** (stale subconscious PR audit): implemented, working
- **Step 9I** (issue filing for HIGH-risk bugs): implemented, working
- **Step 9J** (schema drift detection): implemented, working
- **Step 9L** (AI metering violation check): implemented, working — 45 violations detected in GH #827

---

## Open Questions

1. **Credential rotation workflow**: Once AUTOPILOT_GH_TOKEN is rotated, what is the process to update `ops/credential-rotation-schedule.md` and any secrets stores? Needs documentation.
2. **SUPABASE_ACCESS_TOKEN**: Listed in credential-rotation-schedule.md with unknown rotation date. Should be pinned to a known rotation date.
3. **Step 9G after rotation**: Will the fixed `mcp__github__actions_run_trigger` call need updated auth headers once the AUTOPILOT_GH_TOKEN is rotated? Or does it use a different token?
