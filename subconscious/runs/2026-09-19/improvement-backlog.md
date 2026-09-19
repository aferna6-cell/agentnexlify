# Improvement Backlog — Run 2026-09-19 (Run 124)

## Active (recommended, not yet implemented)

### Step 9E: Add 10-Day P0 Credential Expiry Escalation Tier
- **Status:** autonomous-executable (mandate passed run 122), task prompt blocks. 5th carry-forward.
- **Urgency:** CRITICAL — P0 fires 2026-09-22 (3 days). Expiry 2026-10-02 (13 days).
- **File:** `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block
- **Action required:** Interactive session OR task prompt change to allow implementation
- **Evidence:** grep confirms P0 tier absent. GH #399 = 7+ comments, 0 responses.

---

## Parking Lot (approved direction, not yet time)

### Step 9G: Replace `gh` CLI with `mcp__github__actions_run_trigger` in SKILL.md
- **Status:** autonomous-executable (mandate passed run 124: run 121 winner + 3 carries)
- **Urgency:** HIGH — bash command fails silently on every nightly run. In-session workaround applied 2026-09-18 only.
- **File:** `.claude/skills/nightly-commit-review/SKILL.md` Step 9G block
- **Next action:** implement in interactive session or next subconscious run if task prompt allows

### Dependabot Major-Version PR Triage Issue
- **Status:** new idea, not yet debated to winner
- **Urgency:** MEDIUM — PRs #859–864 accumulating. No tracking issue. No coordination plan.
- **Action:** file GH issue to coordinate react 18→19 (frontend + demo-platform), vitest 4→5, mcp major-version upgrade order
- **Next action:** file as bonus action or dedicated future run

### Step 9M: AI Metering Trend Tracking
- **Status:** new idea, proposed run 124
- **Urgency:** LOW — 45 violations (rc=2), GH #827 open. No trend data showing progress.
- **Action:** add 7-day rolling count + delta to nightly Step 9L reporting
- **Next action:** future run if Step 9E/9G are closed

### os_tool_executions.py God Class Split (783L)
- **Status:** GH issue may have been filed in run 123 bonus action (mandate item) — needs verification
- **Urgency:** MEDIUM — 783L, 7th consecutive mention, Rule 9 violation
- **Action:** verify GH issue exists; if not, file it. Then split: action persistence, event dispatch, quota tracking, tool registry bridge
- **Next action:** verify issue in run 125 mandate check

---

## Frozen / Rejected

- `ai_human_handoff` — frozen (governance.json frozen_ideas list)

---

## Questions for run 125

1. Was Step 9E P0 tier implemented in an interactive session before 2026-09-22?
2. Did the P0 tier fire on 2026-09-22 (days_remaining = 10)? Was a P0 issue filed?
3. Was AUTOPILOT_GH_TOKEN rotated before 2026-10-02?
4. Was Step 9G SKILL.md fix applied (gh → mcp__github__actions_run_trigger)?
5. Was the os_tool_executions.py GH issue filed (run 123 bonus mandate item)?
