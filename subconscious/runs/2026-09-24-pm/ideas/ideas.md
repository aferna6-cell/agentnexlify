# Ideas — Run 2026-09-24-pm

## Evidence Digest
- **Repo quiet**: only nightly + subconscious commits in 3 days (0 feature code)
- **Step 9J Priority Queue** (run 128 winner): NOT in SKILL.md — sort:created-asc + perPage=5 absent (grep=0) — 1st carry-forward
- **Step 9E P0 tier**: CONFIRMED IMPLEMENTED by nightly-2026-09-24 (P0 comment + SKILL.md edit done)
- **Step 9G gh→MCP**: CONFIRMED IMPLEMENTED by nightly-2026-09-23
- **AUTOPILOT_GH_TOKEN**: expires 2026-10-02, **8 days**. P0 on GH #399. Loop stalled 82+ days. 40 ai-ready issues blocked.
- **Brain connector PAT**: expires 2026-10-02, 8 days. GH #394 tracked.
- **KB**: 29 days stale (last: 2026-08-26). Step 9G triggers kb-autopopulate.yml but ANTHROPIC_API_KEY missing from GH Actions (GH #403) causes silent failure.
- **GH #827**: 45 unguarded AI call sites — Step 9L detecting nightly, filing issues
- Frozen ideas: ai_human_handoff

---

### Idea 1: Step 9J Priority Queue Fix (run 128 carry-forward)
**Evidence:** Run 128 winner confirmed absent from SKILL.md (grep=0). nightly-2026-09-24 implemented Step 9E instead — Step 9J was not the focus. 7+ consecutive nightlies show 17/19 Dependabot PRs skipped because token budget depletes before processing all results. Oldest PRs (#885-#891) carry highest CVE-age risk. By default search returns newest-first; oldest (highest risk) are processed last or skipped.
**Action:** In SKILL.md Step 9J.1, add `sort: 'created', direction: 'asc', perPage: 5` to `search_pull_requests` call. Update log line to include "sort:created-asc" label.
**Impact:** Ensures the oldest (highest CVE risk) Dependabot PRs are processed first within the token budget window. ~5 PRs/run instead of random selection.
**Category:** workflow_efficiency

---

### Idea 2: Step 9G KB Failure Diagnostics
**Evidence:** KB 29 days stale. Step 9G triggers kb-autopopulate.yml via mcp__github__actions_run_trigger (confirmed working since nightly-2026-09-23). But workflow fails silently — ANTHROPIC_API_KEY missing in GH Actions. GH #403 open but no specific error message. Human doesn't know exactly which secret to add without inspecting GH Actions logs manually.
**Action:** Update Step 9G in SKILL.md to poll the last kb-autopopulate.yml run (via mcp__github__actions_list) 30s after triggering, check conclusion (success/failure), and post the specific failure reason on GH #403 if failed. Log: "Step 9G: kb-autopopulate triggered — status=FAILED (missing secret ANTHROPIC_API_KEY). Comment added to GH #403."
**Impact:** Converts silent kb-autopopulate failures into actionable GH comments with exact error cause. Reduces human diagnosis time from 10+ min to 0.
**Category:** operational

---

### Idea 3: Step 9M — AI Metering Trend Tracking
**Evidence:** GH #827 has 45 open violations detected by Step 9L. Step 9L files one issue per violation but doesn't track whether the count is improving or worsening. PRs #792-#799 retroactively metered 6 endpoints in 3 days (498-1726 new test lines each). New feature PRs continue to add unguarded calls. Without trend data, it's impossible to know if the class problem is being solved.
**Action:** Add Step 9M to SKILL.md: read count of open GH issues with label `billing + ai-ready` (proxy for pending AI metering violations), compare to last-run count stored in a state file (subconscious/state/ai_metering_trend.json), log delta. If count increased week-over-week: post comment on GH #827 with trend.
**Impact:** Early detection of regression — if new PRs add violations faster than issues are resolved, the trend alert fires before backlog grows unmanageable.
**Category:** code_health

---

### Idea 4: GH #403 Consolidated Diagnostic Comment
**Evidence:** GH #403 is 75+ days open. Three separate blockers: ANTHROPIC_API_KEY missing from GH Actions, KB 29d stale, Step 9G triggering but failing. Multiple nightly comments have been posted piecemeal. Human sees fragmented history, harder to action.
**Action:** Post a single consolidated comment on GH #403 summarizing all three root causes (ANTHROPIC_API_KEY in GH Actions, SUPABASE_ACCESS_TOKEN last_rotated unknown, KB current staleness=29d), exact steps to fix each, and the expected outcome (kb-autopopulate.yml runs clean, Step 9G reports success). This is a one-time targeted action.
**Impact:** Reduces diagnosis friction for human by ~15 min. Higher probability of human actioning GH #403 next session.
**Category:** operational

---

### Idea 5: Step 9E Expiry State File
**Evidence:** ops/credential-rotation-schedule.md shows AUTOPILOT_GH_TOKEN last_rotated=2026-07-04 (estimated). After rotation, the human must manually update this file. Step 9E reads this file daily. If human rotates the token but forgets to update the schedule, Step 9E will keep firing P0 alerts incorrectly.
**Action:** Add a rotation confirmation template to ops/credential-rotation-schedule.md under AUTOPILOT_GH_TOKEN with explicit git commit instruction + reminder that Step 9E depends on the date being accurate. Add to Step 9E a "STALE_DATE" warning if last_rotated matches an expiry date exactly (suggesting the date wasn't updated after rotation).
**Impact:** Prevents false P0 alerts after rotation. Closes the feedback loop between human rotation action and automated monitoring.
**Category:** operational
