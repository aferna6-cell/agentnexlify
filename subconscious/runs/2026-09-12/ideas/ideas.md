# Ideas — Run 121 (2026-09-12)

## Evidence Summary

- **Step 9G broken in cloud CCR**: `gh workflow run kb-autopopulate.yml` requires gh CLI which is unavailable in cloud-hosted CCR sessions. KB 17d stale (last run 2026-08-26, threshold 7d). Step 9G fires but its current trigger mechanism cannot execute in the cloud nightly environment.
- **Step 9E escalation is recommended, not implemented**: run 119/120 proposed earlier warning + GH issue filing, but current governance evidence records `step9e_status` as NOT YET IMPLEMENTED. AUTOPILOT_GH_TOKEN is approaching its warning threshold; the recorded 90-day due date is 2026-10-02.
- **os_tool_executions.py active**: 2 fixes landed in 3 days (Gmail termination 0605d0f + email approval surface adb31f9), currently 436L. Rule 9 god-class threshold: 600L.
- **SUPABASE_ACCESS_TOKEN date unknown**: credential-rotation-schedule.md shows "unknown" for last_rotated. Human has not set it. No new duplicate issue should be filed without identity-based dedup against existing ops trackers.
- **Run 120 mandate item 6**: explicitly requests "Step 9G MCP fix (Idea 2 from this run): evaluate for run 121 implementation."

---

### Idea 1: Fix Step 9G — evaluate replacing gh CLI with a verified GitHub Actions MCP trigger
**Evidence:** KB is 17d stale (threshold 7d). `gh workflow run` requires gh CLI unavailable in cloud CCR sessions, so the present Step 9G trigger path is not viable there. Run 120 mandate item 6 explicitly requests this evaluation. A GitHub Actions MCP trigger/list path is a candidate, but the exact actions and schemas have **not** been verified in the actual nightly CCR execution surface.
**Action:** First verify, inside the nightly CCR surface, that the required GitHub Actions MCP trigger and run-list capabilities exist and work end to end. Only after that proof, edit Step 9G in `.claude/skills/nightly-commit-review/SKILL.md` to replace the `gh workflow run` / `gh run list` path with the verified MCP actions and their actual schemas. Keep GH #403 separate: triggering the workflow does not repair a missing `ANTHROPIC_API_KEY` prerequisite.
**Impact:** If verification succeeds, Step 9G gains an execution mechanism that can operate in the cloud nightly environment. KB freshness improves only after the trigger path and the workflow's own prerequisites both succeed.
**Category:** operational
**Effort:** XS after capability verification

---

### Idea 2: Track Step 9E escalation as pending implementation, not implemented
**Evidence:** Run 119 winner "Step 9E Credential Expiry Escalation — Earlier Warning + GH Issue Filing" remains a recommendation. Current governance on `main` explicitly records `step9e_status` as NOT YET IMPLEMENTED. Marking it implemented would cause future runs to skip real work.
**Action:** Keep governance status for the run 119 Step 9E escalation as pending/recommended until `.claude/skills/nightly-commit-review/SKILL.md` actually contains the identity-deduplicated escalation behavior and that implementation is verified. Do not add an `implemented` active_directions entry prematurely.
**Impact:** Governance accuracy. Prevents a false-complete state and preserves the real Step 9E implementation lane.
**Category:** operational (governance)
**Effort:** XS

---

### Idea 3: Step 9M — os_tool_executions.py god-class early warning
**Evidence:** os_tool_executions.py at 436L after 2 modifications in 3 days (commits 0605d0f + adb31f9). Rule 9 threshold: 600L (split required before adding new concern). Current growth rate ~25L/commit suggests ~7 more commits before crossing threshold. File is Agent OS router — critical path for all tool executions.
**Action:** Add Step 9M to nightly SKILL.md: `wc -l backend/routers/os_tool_executions.py` — if ≥500L, file GH issue "os_tool_executions.py approaching god-class threshold (Rule 9)". Add architectural note on split strategy.
**Impact:** Early warning before 600L threshold. Gives 2-3 nightly cycles of notice before emergency refactor required. Prevents future architectural debt from accumulating silently.
**Category:** code_health
**Effort:** XS (single block addition to SKILL.md)

---

### Idea 4: SUPABASE_ACCESS_TOKEN unknown rotation date — route through identity-deduplicated Step 9E handling
**Evidence:** credential-rotation-schedule.md shows SUPABASE_ACCESS_TOKEN last_rotated = "unknown". Age-based Step 9E logic cannot calculate a warning date from an unknown rotation date. Existing ops/human-action trackers must be searched by credential identity before any new issue is created.
**Action:** Extend the pending Step 9E implementation contract so unknown-date credentials are surfaced for human verification, using credential-identity dedup to reuse an existing tracker when one already covers the credential. Record the verified rotation date before applying normal age thresholds.
**Impact:** Surfaces a credential with unknown expiry while avoiding duplicate ops issues.
**Category:** operational
**Effort:** XS after Step 9E implementation surface is available

---

### Idea 5: Step 9N — nightly credential countdown observability after Step 9E implementation
**Evidence:** The proposed Step 9E escalation is not yet implemented. The current system therefore does not provide the intended identity-deduplicated pre-threshold escalation contract. A daily countdown would be useful observability, but it should build on the corrected Step 9E implementation rather than assume that implementation already exists.
**Action:** After Step 9E is implemented, consider logging each known credential's days_since_rotation, warning-threshold distance, and recorded due date every nightly run. Unknown-date credentials should be reported as unknown, not assigned fabricated countdowns.
**Impact:** Improves credential-health visibility without conflating warning thresholds with expiry/due dates.
**Category:** operational
**Effort:** XS
