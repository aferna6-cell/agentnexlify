# Improvement Backlog — Run 119 (2026-09-11)

## Active (pending human approval)

### [RUN-119] Step 9E credential escalation: auto-file GH issue when within 10 days of rotation threshold
- Status: pending_approval
- Evidence: AUTOPILOT_GH_TOKEN at 69d (threshold 76d, expires ~2026-09-18)
- Action: Edit .claude/skills/nightly-commit-review/SKILL.md Step 9E block
- Effort: S (SKILL.md edit ~20 lines)
- Risk: LOW

---

## Parking Lot (next to consider)

### Step 9G MCP Fix: Replace gh CLI with mcp__github__actions_run_trigger
- Evidence: 4+ consecutive broken nights, KB 16 days stale
- Prerequisite: Verify kb-autopopulate.yml has `workflow_dispatch:` trigger
- Effort: S (SKILL.md edit ~5 lines)
- Run when: mandate check confirms workflow_dispatch available

### Step 9M: os_tool_executions.py god class split — add monitoring step
- Evidence: 783 lines, 4 consecutive runs noting this, 12d+ stable
- Action: Add Step 9M to SKILL.md to monitor line count + auto-file GH issue when >600L + >14d stable
- Effort: S (SKILL.md ~15 lines)
- Run when: if not already filed as GH issue

### Step 9D enhancement: Nudge stalled ai-ready issues after 14 days
- Evidence: #728 (10d), #669 (22d), #660 (27d) — all stalled with no PR
- Action: Add nudge-comment logic to Step 9D
- Effort: S (SKILL.md ~15 lines)
- Security urgency: #669 and #660 are security patches

### Governance.json verified_implemented status field
- Evidence: Step 9L stale flag caused 3 wasted carry-forward runs
- Action: Add schema note + fix Step 9L flag in governance.json
- Effort: XS (JSON edit)
- Can be done as bonus action with any other commit

---

## Implemented (confirmed live)

- Step 9B: healthz monitor → runs/SKILL.md (confirmed 2026-09-11 nightly)
- Step 9C: brain connector staleness → SKILL.md (commenting on #800 live)
- Step 9D: issue-to-PR loop health → SKILL.md (reporting stalled issues)
- Step 9E: credential rotation status check → SKILL.md (detecting expiry, logging warnings)
- Step 9F: KB autopopulate staleness → SKILL.md (detecting + commenting on #403)
- Step 9G: KB autopopulate self-healing → BROKEN (gh CLI unavailable in CCR)
- Step 9I: demo-role security sweep → SKILL.md (checking block_demo_role coverage)
- Step 9J: Dependabot auto-merge → SKILL.md (0 PRs today → PASS)
- Step 9K: stale subconscious draft PR audit → SKILL.md (checking for stale PRs)
- Step 9L: AI usage guard coverage sweep → SKILL.md (lines 457/471, confirmed run 118)

---

## Frozen

- ai_human_handoff: frozen run 21 — 3+ proposals without implementation
- widget_drift_topic_retired: retired run 70 — human-only task
- step_9j_cursor_approach: moot (0 open Dependabot PRs). Monitor. Re-propose if PR count rises.
