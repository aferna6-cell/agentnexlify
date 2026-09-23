# Improvement Backlog — Run 127 (2026-09-23)

## Winner (This Run)
- **Step 9E: Add 10-Day P0 Credential Expiry Escalation Tier** — Autonomous-executable since run 122. Task-prompt recommend-only constraint is the blocker. Implementation: ~15 lines in `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block. See `winning-concept.md` for exact sketch.

---

## Parking Lot (Priority Order)

### 1. Step 9M — AI Metering Violation Trend Tracking
- **Evidence:** Step 9L reports 45 violations (unchanged across multiple runs). No trending. New features landing silently could push count up without detection.
- **Action:** Add Step 9M block to SKILL.md after Step 9L: read last Step 9L count from nightly log, compute delta, log trend. Escalate to GH #827 comment if delta > 0.
- **Effort:** S (~20 lines bash + awk, same SKILL.md channel)
- **Status:** WEAKENED this run (PRs #792-#799 retroactive — may be trending down). Post-Step-9E item.
- **Next check:** Run 128 — re-evaluate if Step 9E implemented.

### 2. os_tool_executions.py God-Class Split GH Issue
- **Evidence:** os_tool_executions.py at 783L, 6+ consecutive run mentions (115→127). Rule 9: factor god classes >600L. Agent OS shipping new tool executions each sprint — blast radius grows.
- **Action:** File GH issue: "refactor(agent_os): split os_tool_executions.py (783L) into os_tool_dispatch.py + os_tool_state.py + os_tool_executor.py". Labels: refactor + agent-os + ai-ready.
- **Effort:** XS (GH issue only, no code)
- **Status:** Governance mandated GH issue at runs 122/123 bonus actions — verify if filed. If not, bonus action for run 128.

### 3. Step 9N — Credential Rotation Reminder Comment Automation
- **Evidence:** `ops/credential-rotation-schedule.md` has blank `last_rotated` fields (unknown) for multiple credentials including SUPABASE_ACCESS_TOKEN. Step 9E can't fire for credentials without valid `last_rotated` dates.
- **Action:** Add Step 9N to SKILL.md: for each credential with last_rotated=unknown or >90 days, post dedup-guarded weekly reminder on tracking issue with exact dashboard path to find rotation date.
- **Effort:** S
- **Status:** Prerequisite is Step 9E (need days_remaining first). Run 129+ candidate.

### 4. GH #892 — CI Safety Tests Escaping to Network
- **Evidence:** GH #892 P1 filed 2026-09-22. CI tests making real network calls. Filed under P1.
- **Status:** KILLED from debate (already tracked, insufficient file-level evidence for specific recommendation). Issue-to-pr-loop will handle once AUTOPILOT_GH_TOKEN rotated (GH #893).

---

## Mandate Items for Run 128

1. **Verify Step 9E P0 tier implemented:** grep `.claude/skills/nightly-commit-review/SKILL.md` for `days_remaining`, `P0`, `<= 10`. Confirmed or still absent?
2. **Did Step 9E P0 fire for AUTOPILOT_GH_TOKEN?** Check nightly log for "Step 9E P0 ALERT" line. P0 GH issue filed or still only GH #893?
3. **AUTOPILOT_GH_TOKEN rotated before 2026-10-02?** 8 days remain. If rotated: update `ops/credential-rotation-schedule.md` with new `last_rotated` date. If not: escalate.
4. **Step 9G firing correctly?** KB still 27+ days stale (ANTHROPIC_API_KEY blocker, GH #403). Did Step 9G trigger run? Check `knowledge-base/log.md`.
5. **GH #892 CI fix:** still P1 open? Any PR from issue-to-pr-loop?
6. **os_tool_executions.py GH issue:** confirm filed (bonus action from runs 122/123) or file in run 128.

---

## Governance Notes

- Step 9G: CONFIRMED IMPLEMENTED by nightly-2026-09-23 (run 126 winner delivered)
- Step 9E: 7th carry-forward. Autonomous-executable mandate still binding (run 122). Task-prompt recommend-only is the sole blocker. Implement when constraint lifted.
- KB staleness: 27+ days. Root cause: ANTHROPIC_API_KEY missing from GH Actions (#403). Step 9G trigger now works but workflow itself blocked.
- Repo idle: 4+ days (zero production code commits).
