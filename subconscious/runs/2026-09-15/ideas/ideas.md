# Ideas — Run 2026-09-15 (Run 121)

Generated from evidence gathered 2026-09-15. All ideas evidence-backed, atomic, not frozen/rejected.

---

### Idea 1: Step 9E — Add days_remaining ≤10 threshold + GH issue filing (2nd carry-forward from run 119)

**Evidence:** nightly-2026-09-15 Step 9E: "AUTOPILOT_GH_TOKEN: 73 days — under 76-day threshold, 0 approaching expiry." Token expires 2026-10-02 = 17 days. Current logic fires at `days_since_rotation >= 76` (3 days from now) but only logs — no GH issue filed. Under proposed `days_remaining <= 10` threshold, alert would have fired 7 days ago at day 66. 3 consecutive nightlies logged credential warning with zero human action. GH #399 open for token rotation, untouched.

**Action:** Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block: change `days_since_rotation >= 76` to `days_remaining = threshold_days - days_since_rotation; if days_remaining <= 10`. Add GH issue filing for new violations; dedup by searching `label:credential-rotation` — comment on existing GH #399 rather than create duplicate. Also handle `unknown` last_rotated state by filing `needs-human-input` labeled issue.

**Impact:** AUTOPILOT_GH_TOKEN rotation tracked with actionable GH issue + email notification. Prevents silent loop death from token expiry 2026-10-02. Brain PAT same fix. SUPABASE_ACCESS_TOKEN unknown state finally escalated.

**Category:** workflow_efficiency / operational

---

### Idea 2: Fix Step 9G — Replace gh CLI with mcp__github__actions_run_trigger

**Evidence:** nightly-2026-09-15 Step 9G: "gh CLI not available in this environment. Cannot trigger workflow run." KB 20 days stale (last: 2026-08-26). Step 9G fires but cannot execute because `gh workflow run` requires gh CLI which is absent in CCR cloud sessions. `mcp__github__actions_run_trigger` is listed as an available deferred tool in this session's MCP registry and presumably available in nightly sessions (same GitHub MCP config).

**Action:** Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9G: replace `gh workflow run kb-autopopulate.yml` with `mcp__github__actions_run_trigger(owner='aferna6-cell', repo='agentnexlify', workflow_id='kb-autopopulate.yml', ref='main')`. Update result-check logic to handle MCP response shape instead of gh exit code.

**Impact:** KB self-healing resumes. Step 9G transitions from "always no-op" to "triggers workflow + logs failure URL for human." KB 20d stale → auto-triggered on next nightly. Compounds permanently.

**Category:** operational

---

### Idea 3: Step 9L dedup fix — search by systemic label before filing duplicate summary issue

**Evidence:** nightly-2026-09-15 Step 9L filed GH #871 as a systemic summary covering "20 unique router violations." Step 9L dedup logic searches for existing issues by `path:function` pair — per-function granularity. GH #871 is a systemic issue, not per-function. Next nightly: Step 9L will scan same 20 functions, find no per-function issue matching, and either file 20 new issues or another systemic summary. Dedup gap is real.

**Action:** Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9L: before filing any issue, first check for open systemic summary issue (search `label:billing AND label:ai-ready AND is:open in:title "AI metering"`). If found: add comment with current count. If not found: file systemic summary (not per-function issues). Prevents GH issue spam from daily recurrence of same violation class.

**Impact:** Step 9L runs cleanly every nightly without filing duplicate GH issues. Comment-on-existing keeps #871 as the canonical tracking issue. Reduces GH issue noise.

**Category:** workflow_efficiency

---

### Idea 4: Step 9E auto-close credential GH issues when rotation confirmed

**Evidence:** GH #399 (AUTOPILOT_GH_TOKEN rotation) has been open for 73+ days. When human rotates credential and updates credential-rotation-schedule.md (resets `last_rotated` to today), the GH issue remains open unless manually closed. Step 9E currently has no auto-close logic. Over time this accumulates stale "done" issues. SUPABASE_ACCESS_TOKEN has its own open issue (GH #800 for brain connector staleness, tagged with credential context).

**Action:** In Step 9E, after checking credentials: for any `credential-rotation`-labeled open issue whose credential now has `days_since_rotation < 7` (recently rotated), post a success comment and close the issue. Dedup: only close if last_rotated date in schedule changed since last nightly check.

**Impact:** GH issues auto-close when human acts. Reduces stale issue noise. Makes credential health immediately visible in open issue count.

**Category:** workflow_efficiency

---

### Idea 5: Nightly Step 9E extension — unknown last_rotated creates separate actionable GH issue

**Evidence:** SUPABASE_ACCESS_TOKEN `last_rotated: unknown` in ops/credential-rotation-schedule.md for 120+ runs. Every nightly Step 9E logs "1 unknown state" but files NO GH issue for unknown state. Human has never filled in the date. The log line disappears in nightly reports. A dedicated GH issue with `needs-human-input + ops` labels would create an email notification and a trackable action item. GH #800 tracks brain connector staleness (related) but not SUPABASE_ACCESS_TOKEN rotation date specifically.

**Action:** In Step 9E, add unknown-state handling: if `last_rotated == unknown`, search for open issue labeled `credential-rotation + needs-human-input` for that credential. If none found: file issue asking human to verify rotation date from Supabase dashboard. Dedup: don't re-file if open issue exists. Add to nightly log: "Step 9E: 1 unknown state — GH issue filed/found."

**Impact:** Human gets actionable GH issue (email) for SUPABASE_ACCESS_TOKEN date. Closes a monitoring blind spot that has persisted 120+ runs.

**Category:** operational
