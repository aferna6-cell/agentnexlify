# Ideas — Run 118 (2026-09-10)

## Evidence Inputs

- Step 9L confirmed in SKILL.md (grep=2, lines 457+471) — governance mandate condition met
- `check_ai_metering.py` finds 30 violations across 16 router + 14 service files
- PR #834 shipped `check_backend_future_annotations.py` CI guard with allowlist-baseline pattern
- `os_tool_executions.py`: 783L, ~10d stable (last commit: f72a274, schema docs only)
- Step 9J still skipping 17/19 Dependabot PRs due to token budget exhaustion (4+ nights)
- `meter-ai-endpoint` skill added 2026-09-08 (b20ece0) — reactive tooling for metering
- `__future__ annotations` cleanup active (PRs #836, #837, #838) — 3 test files remain
- customer-gaps.md: AI-to-human handoff = Critical for all industries (Open)
- KB log.md: last compile 2026-08-26, 15d stale (Step 9G cloud trigger still failing)

---

### Idea 1: os_tool_executions.py God Class Split
**Evidence:** 783L file (Rule 9 threshold: 600L), 10d stable since f72a274 (schema docs only). Governance run_116_mandate + run_117_mandate both explicitly name this as "run 118 winner if Step 9L confirmed." Step 9L IS confirmed (grep=2). File handles three distinct concerns: OS tool execution store, executor orchestration, and approval flow handler.
**Action:** Split into `os_tool_executions_store.py` (DB read/write), `os_tool_executor.py` (execution logic), `os_tool_approval.py` (approval flow). Update imports across callers. No API changes — internal refactor only.
**Impact:** Reduces blast radius of future bugs. Each module is reviewable in isolation. Prevents the file from reaching 1000L by next quarter. Unblocks Rule 9 compliance.
**Category:** code_health

---

### Idea 2: CI Gate for New Unmetered AI Calls (check_ai_metering.py allowlist)
**Evidence:** PR #834 (2026-09-10) shipped `check_backend_future_annotations.py` — an allowlist-based CI guard that starts with 3 known violations and fails on new ones. Identical pattern applies to `check_ai_metering.py`. This idea was KILLED in run 117 ("no allowlist mechanism exists"), but PR #834 proves the allowlist-CI pattern is viable and buildable in one commit. `check_ai_metering.py` already exists with 325 test lines. 30 violations become the allowlist baseline. GitHub Actions CI workflow blocks new violations at PR time.
**Action:** Add 30 known violations to `KNOWN_VIOLATIONS` set in `check_ai_metering.py`. Add `.github/workflows/backend-ai-metering.yml` (mirrors `backend-future-annotations.yml`). CI fails if any function NOT in allowlist calls Claude. 
**Impact:** Catches new unmetered AI calls at PR time (before merge) vs. Step 9L's overnight detection. Defense-in-depth with Step 9L. Permanently closes the new-violation pipeline.
**Category:** code_health

---

### Idea 3: Step 9J Token Budget Fix — Reorder to Position 2 in Nightly
**Evidence:** 17/19 Dependabot PRs skipped 4+ consecutive nights (runs 113-117). Each prior step (9C through 9K) consumes token budget via multiple GitHub API calls + model reasoning. Reordering Step 9J immediately after commit review (before Steps 9C-9K) gives it fresh budget. S effort — SKILL.md reorder only, no logic change.
**Action:** In `.claude/skills/nightly-commit-review/SKILL.md`, move Step 9J block from position ~8 to position 2 (after "2. Review commits and apply LOW-risk fixes"). Add comment: "Moved early to run before token-intensive Steps 9C-9K exhaust budget."
**Impact:** Step 9J goes from ~10% effective (2/19 PRs) to ~95% (19/19). Security patches merge within 24h of CI passing vs. 2-3 week wait. CVE window closes.
**Category:** workflow

---

### Idea 4: Step 9G Cloud Trigger Fix — mcp__github__actions_run_trigger
**Evidence:** KB last compile 2026-08-26 (15d stale). Step 9G fires correctly (nightly confirms trigger attempt) but `gh workflow run` fails silently in cloud sessions (no `gh` CLI in cloud containers). GH #403 has had 7+ comments but ANTHROPIC_API_KEY also missing, creating double-failure. The trigger side can be fixed independently: replace `gh workflow run` with `mcp__github__actions_run_trigger`. S effort, compound fix.
**Action:** Edit Step 9G block in `.claude/skills/nightly-commit-review/SKILL.md`: replace `bash gh workflow run kb-autopopulate.yml --repo aferna6-cell/agentnexlify` with `mcp__github__actions_run_trigger(owner="aferna6-cell", repo="agentnexlify", workflow_id="kb-autopopulate.yml")`. Add error handling: if trigger returns non-200, post diagnostic comment on GH #403 with exact error.
**Impact:** KB autopopulate trigger becomes observable in cloud sessions. Trigger failures surface as specific errors rather than silent skips. Compounds permanently: every nightly can attempt the trigger.
**Category:** operational

---

### Idea 5: AI-to-Human Handoff (Customer Gap)
**Evidence:** customer-gaps.md lists "AI-to-human handoff" as Critical impact for ALL industries. Listed first in "Open Gaps — Cross-Industry (High Priority)." However: no implementation sketches exist, no GH issues filed, no specific evidence of customers churning because of this gap, and M effort with architectural implications (handoff channel, notification system, agent state transfer).
**Action:** File GH issue with architecture brief: trigger words that indicate AI hit its limit, notification to business owner (email/SMS), conversation transcript handoff, resume path for human to take over widget session.
**Impact:** Unlocks complex query handling for all verticals. Reduces lost leads from conversations the AI can't complete.
**Category:** customer_value
