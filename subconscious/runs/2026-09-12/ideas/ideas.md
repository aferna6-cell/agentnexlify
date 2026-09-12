# Ideas — Run 121 (2026-09-12)

## Evidence Summary

- **Step 9G broken in cloud CCR**: `gh workflow run kb-autopopulate.yml` requires gh CLI which is unavailable in cloud-hosted CCR sessions. KB 17d stale (last run 2026-08-26, threshold 7d). Step 9G fires but silently fails every nightly.
- **Step 9E escalation implemented**: run 119/120 winner (early warning + GH issue filing) IS in SKILL.md (days_remaining, <= 10, add_issue_comment — 9 grep hits). AUTOPILOT_GH_TOKEN at ~70d (threshold 76d), fires in ~6 days. No governance.json active_directions entry yet for this enhancement.
- **os_tool_executions.py active**: 2 fixes landed in 3 days (Gmail termination 0605d0f + email approval surface adb31f9), currently 436L. Rule 9 god-class threshold: 600L.
- **SUPABASE_ACCESS_TOKEN date unknown**: credential-rotation-schedule.md shows "unknown" for last_rotated. Human has not set it. No GH issue filed.
- **Run 120 mandate item 6**: explicitly requests "Step 9G MCP fix (Idea 2 from this run): evaluate for run 121 implementation."

---

### Idea 1: Fix Step 9G — Replace gh CLI with `mcp__github__actions_run_trigger`
**Evidence:** KB is 17d stale (threshold 7d). `gh workflow run` requires gh CLI unavailable in cloud CCR sessions. Step 9G fires but silently fails. Run 120 mandate item 6 explicitly requests this evaluation. `mcp__github__actions_run_trigger` IS available (confirmed in MCP tool list).
**Action:** Edit Step 9G block in `.claude/skills/nightly-commit-review/SKILL.md`. Replace `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify` with `mcp__github__actions_run_trigger(owner="aferna6-cell", repo="agentnexlify", workflow_id="kb-autopopulate.yml")`. Replace `gh run list` status check with `mcp__github__actions_list(owner, repo, workflow_id)` to read latest run result.
**Impact:** KB autopopulate workflow gets triggered correctly in cloud environment. KB staleness drops from 17d+ to <7d within one nightly cycle. Step 9G becomes functional.
**Category:** operational
**Effort:** XS (single block edit in SKILL.md)

---

### Idea 2: Add governance.json active_directions entry for Step 9E escalation (run 119 winner)
**Evidence:** Run 119 winner "Step 9E Credential Expiry Escalation — Earlier Warning + GH Issue Filing" was implemented in SKILL.md (verified run 121 mandate item 1 — 9 grep hits). No governance.json entry exists for this enhancement (separate from the original Step 9E add from run 84). Governance.json accuracy is critical for preventing re-proposal of already-done work.
**Action:** Add active_directions entry `{"title": "Step 9E credential expiry escalation — early warning + GH issue filing (run 119 winner)", "status": "implemented", "date": "2026-09-08", "implemented_date": "2026-09-10", ...}` to governance.json.
**Impact:** Governance hygiene. Prevents future runs from re-proposing run 119/120 winner. Establishes accurate state for Step 9E carry-forward count tracking.
**Category:** operational (governance)
**Effort:** XS (single JSON entry)

---

### Idea 3: Step 9M — os_tool_executions.py god-class early warning
**Evidence:** os_tool_executions.py at 436L after 2 modifications in 3 days (commits 0605d0f + adb31f9). Rule 9 threshold: 600L (split required before adding new concern). Current growth rate ~25L/commit suggests ~7 more commits before crossing threshold. File is Agent OS router — critical path for all tool executions.
**Action:** Add Step 9M to nightly SKILL.md: `wc -l backend/routers/os_tool_executions.py` — if ≥500L, file GH issue "os_tool_executions.py approaching god-class threshold (Rule 9)". Add architectural note on split strategy.
**Impact:** Early warning before 600L threshold. Gives 2-3 nightly cycles of notice before emergency refactor required. Prevents future architectural debt from accumulating silently.
**Category:** code_health
**Effort:** XS (single block addition to SKILL.md)

---

### Idea 4: SUPABASE_ACCESS_TOKEN rotation GH issue — file now, don't wait for Step 9E to fire
**Evidence:** credential-rotation-schedule.md shows SUPABASE_ACCESS_TOKEN last_rotated = "unknown". Step 9E will NOT fire for this credential until it has a last_rotated date. Run 120 mandate item 5 asks about this. SUPABASE_ACCESS_TOKEN is required by the KB autopopulate workflow — if expired, KB goes dark permanently.
**Action:** File GH issue directly from this subconscious run (or mandate Step 9E to file issue for unknown-date credentials regardless of rotation age). Include: "SUPABASE_ACCESS_TOKEN rotation date unknown. Check Supabase dashboard → Access Tokens → find token named AUTOPILOT or similar. Record date in ops/credential-rotation-schedule.md. Token may already be expired."
**Impact:** Surfaces a credential with completely unknown expiry. Prevents silent KB autopopulate failure if token expires undetected.
**Category:** operational
**Effort:** XS (SKILL.md edit to handle unknown-date credentials in Step 9E)

---

### Idea 5: Step 9N — nightly credential expiry countdown log (all credentials each run)
**Evidence:** Current Step 9E only fires when days_remaining <= 10 (≥66d threshold). For the remaining 65 days there is no visibility into credential health. AUTOPILOT_GH_TOKEN is at ~70d and will expire 2026-10-02 — the first time Step 9E would flag it is at 76d (6 days from now). No daily countdown visible in nightly log.
**Action:** Add to Step 9E: always log all credentials' days_since_rotation and days_remaining regardless of threshold. Format: `Step 9E: {name} — {days_since}d since rotation, {days_remaining}d until threshold, expires {expiry}`.
**Impact:** Operators can see credential health trend in every nightly log, not just when threshold fires. Zero overhead; improves observability.
**Category:** operational
**Effort:** XS (single line addition to Step 9E log output)
