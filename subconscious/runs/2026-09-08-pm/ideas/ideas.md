# Ideas — Run 118 (2026-09-08-pm)

## Evidence Summary (200 words)

3-day git window (Sep 5–8): 15 commits, 13 dependency bumps, 1 `__future__` service fix (nightly-09-08), 1 nightly ops log. Step 9L wired via PR #804 (commit `88dac49`). New `meter-ai-endpoint` skill shipped as PR #824. 3 duplicate PRs for same skill (#821, #824, #825) flagged by morning digest. P0 bug #801 (approve_send_once execution leak, 3d unresolved). Issue #823 filed: 5 test files still carry `from __future__ import annotations` — existing CI only checks `backend/routers/`, not `backend/services/` or `backend/tests/`.

7-day bug fix signals: `fix(os-workflows)` annotations patches (2 runs), `fix(billing)` graph AI metering, multiple `fix(security/billing)` metering retrofits. Pattern: annotations ban and AI metering both require repeated cleanup.

Governance condition met: Step 9L confirmed (2 grep hits in SKILL.md), os_tool_executions.py 783L stable 10d+ (last commit `fdcbb97`, not in 7-day window).

Key gaps: `from __future__` CI only covers `backend/routers/` — pattern spreading to services + tests. React 19 PRs #586/#591/#593 stale 43d, no hold explanation. Step 9J processes 2/19 Dependabot PRs (17 skipped).

---

### Idea 1: os_tool_executions.py God Class Split
**Evidence:** File 783L, last commit `fdcbb97` 10d+ ago. Rule 9: >600 lines → split before adding. Governance condition for run 118 explicitly set: "run 118 winner if Step 9L confirmed AND file still stable." Both conditions confirmed. M8 development paused on this file; safe window.
**Action:** File GH issue recommending split into 3 focused modules: `os_execution_engine.py` (core execution loop), `os_tool_dispatcher.py` (tool routing + catalog adapter), `os_result_formatter.py` (output/result normalization). Provide module boundary sketch in GH issue body.
**Impact:** Next M8 sprint won't add code to a 783L file. Reduces merge conflicts, test locality, and future blast radius when M8 expands.
**Category:** code_health

---

### Idea 2: Extend `from __future__` CI Check to All backend/*.py
**Evidence:** Existing CI checks (`pr-check.yml:121`, `health-check.yml:58`, `post-edit-check.sh:16`) all scope to `backend/routers/` only. Issues #805 (service files) and #823 (5 test files) filed in 2 consecutive days — pattern spreading through services/ and tests/ undetected by CI. This single gap caused 2 nightly repair sessions in 7 days.
**Action:** Change `backend/routers/` to `backend/` in the `from __future__` grep in both `pr-check.yml` (line ~121) and `health-check.yml` (line ~58). One-line change per file.
**Impact:** Eliminates recurring nightly cleanup of annotations pattern. CI catches any future introduction in services/, tests/, or routers/. Permanent fix for a pattern that has triggered 3 cleanup cycles.
**Category:** code_health

---

### Idea 3: Move Step 9J to Position 2 in Nightly Sequence (Token Budget Fix)
**Evidence:** Step 9J finds 19 Dependabot PRs but skips 17/19 due to token budget (confirmed across runs 115–117). Security patches age 40+ days. Earlier steps in nightly (Steps 9A–9I, 9K, 9L) consume token budget before Step 9J processes all PRs.
**Action:** Reorder Steps in nightly-commit-review SKILL.md — move Step 9J before Steps 9I/9K/9L (position 2 or 3 in nightly sequence after initial commit review). Earlier position = more remaining token budget for Dependabot enumeration.
**Impact:** Step 9J processes all 19 Dependabot PRs instead of 2. Security patches merge within 24h of CI passing.
**Category:** workflow_efficiency

---

### Idea 4: Document React 19 Hold Decision
**Evidence:** PRs #586 (frontend), #591 (demo-platform), #593 (demo-platform react-dom) all stale 43 days. Morning digest shows no explanation. Dependabot keeps proposing React 19. No ADR or architecture-decisions.md entry explains the hold.
**Action:** Add entry to `docs/dev-knowledge/architecture-decisions.md` explaining React 19 hold: breaking changes (Actions API, hydration, StrictMode double-mount), acceptance criteria for upgrade (test coverage ≥80%, breaking change inventory). Close PRs with "on hold — see ADR."
**Impact:** Eliminates mystery stale PRs, stops Dependabot churn, documents intentional decision for future sessions.
**Category:** workflow_efficiency

---

### Idea 5: Consolidate Duplicate meter-ai-endpoint PRs
**Evidence:** PRs #821, #824, #825 all implement/recommend the same meter-ai-endpoint skill. Morning digest priority 2: "3 dupes on meter-ai-endpoint skill — consolidation needed." #824 is the non-draft PR (content: docs/skill). Subconscious ran twice on this concept creating duplicates.
**Action:** Close #821 and #825 with comment "superseded by #824." Review and merge #824 if content is correct.
**Impact:** Reduces open PR count by 2. Cleaner review queue. Prevents reviewer confusion.
**Category:** operational
