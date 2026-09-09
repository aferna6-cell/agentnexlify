# Ideas — Run 118 (2026-09-09)

## Context

Step 9L confirmed implemented via PR #804 (`ci(nightly): wire Step 9L AI metering sweep`).
Active direction resolved. Fresh ideation cycle.

---

### Idea 1: Split os_tool_executions.py god class

**Evidence:** `backend/services/os_tool_executions.py` at 783L, last commit `ae81e5f` (10d+ stable).
Run 116 governance mandate: "run 118 god class split candidate if Step 9L confirmed."
Step 9L IS confirmed (PR #804). CLAUDE.md Rule 9: "Don't extend god classes — factor them out."
**Action:** Split into 3 focused modules: `os_tool_dispatch.py` (routing/orchestration),
`os_tool_handlers.py` (per-tool execution), `os_tool_context.py` (context/state management).
~260L each vs. current 783L monolith.
**Impact:** Future OS workflow features get added to correctly-scoped 260L files instead of
bloated 783L file. Prevents bug-compounding. Enforces CLAUDE.md Rule 9.
**Category:** code_health

---

### Idea 2: Fix Step 9J token budget — order or cap earlier steps

**Evidence:** Memory entries for runs 115-117 consistently show "17/19 Dependabot PRs skipped
due to token budget." Step 9J runs AFTER Steps 9A-9K which may exhaust context budget before
reaching all PRs. 9 PRs merged this week shows Step 9J works, but only for the first ~2 checked.
**Action:** Add a `STEP_9J_MAX_PRS = 10` cap per run (up from implied ~2). Profile which earlier
step consumes the most token budget and add a note in SKILL.md to run Step 9J before
token-heavy steps in the session when Dependabot count is high.
**Impact:** Step 9J processes 10 PRs per nightly run instead of 2. 19-PR backlog clears in 2 days
instead of 10+ days. Security patches applied faster.
**Category:** workflow

---

### Idea 3: Step 9M — KB autopopulate via MCP trigger (replace broken gh CLI path)

**Evidence:** Step 9G uses `gh workflow run kb-autopopulate.yml` — confirmed broken in cloud
sessions (run 116: "gh CLI unavailable in cloud sessions"). KB stale 14 days (last compile
2026-08-26). `mcp__github__actions_run_trigger` IS available in nightly sessions per run 116
investigation. GH #403 open, ANTHROPIC_API_KEY still missing from GH Actions.
**Action:** Edit Step 9G in nightly SKILL.md to use `mcp__github__actions_run_trigger` as
fallback when `gh` CLI returns non-zero or is absent. Add diagnostic log for which path
succeeded/failed: "Step 9G: triggered via MCP (gh CLI unavailable)".
**Impact:** Step 9G resumes triggering KB autopopulate. KB compiles within 24h of next nightly
instead of staying dark indefinitely. Tenant AI quality improves.
**Category:** operational

---

### Idea 4: Step 9N — Auto-fix test __future__ annotations in nightly

**Evidence:** GH #823 filed yesterday (2026-09-08): 5 test files carry
`from __future__ import annotations` — violating CLAUDE.md Rule 5 (blanket ban in all files).
Nightly auto-fixed the same violation in 2 service files yesterday (`6219d4a`). Test files
have zero 422 risk but the pattern check blocks pre-commit for contributors.
**Action:** Add Step 9N to nightly SKILL.md: grep `backend/tests/` for
`from __future__ import annotations`, auto-remove the line, run `python -m py_compile` to verify,
commit. Same pattern as existing annotation auto-fix logic.
**Impact:** GH #823 closed within 24h. 5 test files cleaned. Pre-commit annotation check
no longer noise-fires on these files.
**Category:** code_health

---

### Idea 5: AI metering violation trend tracker — add Step 9L output to a metrics file

**Evidence:** Step 9L now runs nightly via PR #804 and logs violation counts.
`check_ai_metering.py` found 30+ violations before the billing sprint (#792-#799, #803).
No mechanism tracks whether violations are trending down over time. Without trend data,
it's impossible to know if the metering program is winning.
**Action:** Create `docs/dev-knowledge/ai-metering-trend.md` — append Step 9L violation count
each nightly run: `| 2026-09-09 | 30 | 4 filed | 0 dedup |`. Add 1 line to Step 9L SKILL.md
block to write this row after logging.
**Impact:** Trend is visible. Any regression (new unguarded AI endpoint) shows as uptick.
Proves program progress to human reviewer.
**Category:** operational
