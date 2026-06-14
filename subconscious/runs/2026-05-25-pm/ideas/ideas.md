# Ideas — Run 2026-05-25-pm (Run 33)

Evidence base: skill-discovery-2026-05-25, git log since 2026-05-22, nightly-commit-review-2026-05-25, morning-digest-2026-05-25, direct billing.py inspection.

---

### Idea 1: Create `god-class-splitter` Skill

**Evidence:** Skill discovery 2026-05-25 proposed it with 3+ occurrences in 7 days. PR #180 (2174732, 2026-05-23) split 5 god-class files but required follow-up `5f2cd2b` (21 stale patch targets repaired) and `4afb3cf` (1-line stale import fix). Local_seo split (3555645) required follow-up auto-commit `d8a89f3`. `plans/god-class-refactor_plan.md` lists 29 backend + 25 frontend files still exceeding 600 lines — this workflow recurs weekly. Skill discovery explicitly distinguished this from existing tools: `improve-architecture` = diagnosis only, `tech-debt` = ranking/planning, `dead-code-sweep` = removal.

**Action:** Create `.claude/skills/god-class-splitter/SKILL.md` with 12-step checklist: (1) read god-class-refactor_plan.md for split axis, (2) wc -l confirm >600 threshold, (3) identify 2-3 independent concerns, (4) propose module names, (5) extract each concern, (6) grep + update all importers, (7) delete/thin original, (8) register new routers in main.py, (9) run pytest, (10) verify no stale importers, (11) write smoke tests, (12) commit atomically.

**Impact:** 20-40 min saved per split. Prevents follow-up test-repair commits (current: every split generates 1-2 follow-up commits). 54 remaining files = 18-36 hours of future split work made more reliable. Execution-layer skill nightly review can autonomously create (precedent: moratorium-sprint SKILL.md 7985fbb, Moratorium Escalation Protocol 2ce31b2).

**Category:** workflow

---

### Idea 2: Fix GH #181 — Add 15000→autopilot + 25000→professional to AMOUNT_TO_PLAN

**Evidence:** Direct inspection billing.py:263-281 confirms only `9900: "growth"` and `89900: "enterprise"` under "current pricing" — `15000` and `25000` absent. `test_no_wrong_15000_mapping` (line 38) and `test_no_wrong_25000_mapping` (line 42) actively assert these keys should NOT exist. Nightly review 2026-05-25 carry-forward. Morning digest 2026-05-25 calls it #1 priority. Three consecutive billing commits (c72b535, 1eaaeec, 1553bf7) failed to add or worsened the situation. Subconscious runs 31 and 32 both recommended the fix — not yet implemented.

**Action:** Add `15000: "autopilot"` and `25000: "professional"` to `AMOUNT_TO_PLAN` in `backend/routers/billing.py:264`. Replace `test_no_wrong_15000_mapping` + `test_no_wrong_25000_mapping` with positive `test_current_autopilot_pricing_150` and `test_current_professional_pricing_250`. Update `test_all_four_current_tiers_present` to use `{9900, 15000, 25000, 89900}`.

**Impact:** Fixes billing plan resolution for autopilot ($150/mo) and professional ($250/mo) Stripe webhook events. Removes CI trap blocking correct fix. Closes GH #181. S-effort ~15 min. Moratorium-safe (fixes existing GH issue, no net new pending item).

**Category:** code_health

---

### Idea 3: Create `billing-constant-guard` Skill

**Evidence:** Skill discovery 2026-05-25 documented "triple-fix pattern" — c72b535 + 1eaaeec + 1553bf7 + 3 subconscious runs on same dict entries. The "check for inverted tests" step was skipped twice (both billing commits). CLAUDE.md has authoritative plan price table but is not consulted during billing fixes. Skill discovery estimated 30-45 min wasted per occurrence. Root cause: no checklist that includes cross-referencing CLAUDE.md + checking for inverted assertions.

**Action:** Create `.claude/skills/billing-constant-guard/SKILL.md` with 10-step checklist: (1) read billing.py constants, (2) cross-reference CLAUDE.md plan prices, (3) identify missing/wrong entries, (4) fix the dict, (5) grep tests for AMOUNT_TO_PLAN references, (6) check for inverted assertions, (7) update inverted/stale tests, (8) add parametric contract tests if none exist, (9) verify CI wiring, (10) commit. Triggers: "billing mapping wrong", "AMOUNT_TO_PLAN", "plan prices changed".

**Impact:** Prevents 4th iteration of billing bug class. Root cause fix — encodes the "check for inverted tests" step skipped twice. Future billing fixes won't require 3 attempts.

**Category:** code_health / workflow

---

### Idea 4: Create `post-split-test-repair` Skill

**Evidence:** `5f2cd2b` (2026-05-22) repaired 21 stale `@patch` targets after local_seo split. `4afb3cf` (2026-05-22) fixed 1 stale import — same class, same day. Both commits happened within hours of the god-class split. Skill discovery 2026-05-25 proposed it as standalone skill (15-20 min save per split). Pattern: old module path in @patch strings and imports → needs updating to new module path.

**Action:** Create `.claude/skills/post-split-test-repair/SKILL.md` with 8-step checklist: (1) run pytest, (2) identify old module path in failure, (3) grep all test files for old path, (4) determine new canonical path, (5) update @patch decorators, (6) update imports, (7) re-run pytest, (8) commit. Trigger: "tests broke after split", "stale patch targets", "ModuleNotFoundError after refactor".

**Impact:** 15-20 min saved per split. Eliminates predictable follow-up commit after every god-class split. Could be sub-step of god-class-splitter or standalone — standalone recommended since repairs can be needed days after the split.

**Category:** workflow

---

### Idea 5: Update `improve-architecture` Skill — Add Execution Handoff Step

**Evidence:** Skill discovery 2026-05-25 identified gap: `improve-architecture` ends at "output a ranked fix list" with no handoff to execution. PR #180 audit output → actual split execution required a separate session. Skill discovery proposed: "For CRITICAL god classes (>1000 lines, >2 concerns): immediately invoke god-class-splitter." Currently diagnosis and execution are two separate sessions = context reload + task-switch friction.

**Action:** Add 3-5 lines to `.claude/skills/improve-architecture/SKILL.md` after ranked output step: "For files flagged CRITICAL: immediately invoke god-class-splitter for the top-ranked file. Note split axis in plans/god-class-refactor_plan.md." Additive change to existing skill, no breaking changes.

**Impact:** Closes audit→fix loop. Every architecture review automatically triggers execution for top item. Removes the two-session friction that currently leaves audit findings as "planned but not acted on." S-effort, additive, reversible.

**Category:** workflow
