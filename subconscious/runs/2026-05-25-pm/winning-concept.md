# Winning Concept — 2026-05-25-pm (Run 33)

## Recommendation

Create `.claude/skills/god-class-splitter/SKILL.md` — a 12-step execution checklist for splitting god-class files, distinct from the existing diagnosis-only tools (`improve-architecture`, `tech-debt`).

---

## Why This, Why Now

**Skill discovery 2026-05-25 delivered external validation today.** Three god-class split occurrences landed this week (3555645, 2174732, 4afb3cf/5f2cd2b follow-ups) — the most in any 7-day window. Skill discovery explicitly mapped how `god-class-splitter` fills a gap not covered by `improve-architecture` (diagnosis), `tech-debt` (ranking), or `dead-code-sweep` (removal): it is the execution arm.

**Every split this week required follow-up commits.** Local_seo split (3555645) needed `d8a89f3` to finish extraction. PR #180 (5-file split, 2174732) needed `5f2cd2b` (21 stale @patch targets) and `4afb3cf` (1 stale import). These follow-ups are predictable and preventable — Step 10 of the proposed checklist ("verify no stale importers: `grep -rn "backend.services.old_module" .` returns nothing") catches them before commit.

**54 files remain.** `plans/god-class-refactor_plan.md` lists 29 backend + 25 frontend files still exceeding 600 lines. This workflow will recur weekly for months. Every saved 20-40 min compounds.

**Nightly review can create this autonomously.** Skill file creation is LOW-risk additive — the same mechanism that autonomously implemented moratorium-sprint SKILL.md (7985fbb, 2026-05-19) and the Moratorium Escalation Protocol (2ce31b2, 2026-05-20). No human approval needed for the file creation itself.

---

## Implementation Sketch

**Total estimated time: ~20 min (or autonomous via nightly review)**

### Step 1: Create skill directory

```bash
mkdir -p .claude/skills/god-class-splitter
```

### Step 2: Write SKILL.md

File path: `.claude/skills/god-class-splitter/SKILL.md`

Required content:

**Frontmatter:**
```yaml
---
name: god-class-splitter
description: Execute a god-class file split: identify concerns, extract modules, update all importers, write smoke tests. Execution arm for improve-architecture findings. Prevents post-split test-repair commits.
version: 1.0.0
origin: claude
user-invocable: true
effort: high
triggers:
- split X
- factor out X
- X is too big
- refactor god class in X
- god-class-splitter
---
```

**12-step checklist body:**

1. Read `plans/god-class-refactor_plan.md` — check if target file is queued with a suggested split axis
2. `wc -l <target>` — confirm exceeds 600-line threshold (Rule 9). If not, abort.
3. Read the full file — identify 2-3 independent concerns. Name each concern explicitly.
4. Propose module names (`<concern>_service.py`, `<concern>_fetch.py`, etc.). If ambiguous, wait for approval.
5. Extract each concern to its new module — move only symbols that belong to that concern.
6. Grep all importers: `grep -rn "from backend.services.old_module\|import old_module" .` — update every call site in the same pass. No stale references left behind.
7. Delete or thin the original file. No re-export shims. No `# removed` comments.
8. If the split produced new router files, register in `backend/main.py` (lines 746-813).
9. Run `python3 -m pytest <test_files> -x --tb=short -q` — confirm pass count unchanged.
10. Verify no stale importers: `grep -rn "backend.services.old_module" .` returns nothing. If results remain, fix before committing.
11. Write `tests/test_extracted_<module>.py` smoke test covering the new module's public surface (key endpoints + pure functions). Minimum 5 test functions.
12. Commit atomically: `refactor(<concern>): split <old_module> → <new_modules> (Rule 9)`. One PR, no half-splits.

**Post-split-test-repair sub-step (if tests fail after split):**
- Run `python3 -m pytest tests/ -x --tb=short -q 2>&1 | head -40` — capture first failure
- Identify old module path in failure (e.g. `backend.routers.old_router._function`)
- `grep -rn "old.module.path" tests/` — find all stale @patch decorators + imports
- Update each to new canonical path
- Re-run pytest — repeat until green
- Commit: `test: repoint stale patch targets after <split> refactor`

**Cross-refs:**
- `plans/god-class-refactor_plan.md` — 54 remaining files with split axes
- `improve-architecture/SKILL.md` — hands off top-ranked file to this skill
- CLAUDE.md Rule 9 — don't extend god classes, factor them out
- `tech-debt/SKILL.md` — ranking produces the input priority list

### Step 3: Update improve-architecture SKILL.md (bonus, ~5 min)

After the ranked output step in `.claude/skills/improve-architecture/SKILL.md`, add:

```
For files flagged CRITICAL (>1000 lines, >2 concerns):
→ Immediately invoke god-class-splitter for the top-ranked file
→ Note the split axis in plans/god-class-refactor_plan.md
This closes the audit→fix loop within a single session.
```

---

## What This Replaces

No previous active direction covered execution of god-class splits. Previous tools end at diagnosis or ranking. This is the first skill that executes the split workflow.

---

## Standing Actions (unchanged)

**GH #181 billing fix remains the most urgent HUMAN action (run 34 escalation):**
- Add `15000: "autopilot"` and `25000: "professional"` to `AMOUNT_TO_PLAN` in `backend/routers/billing.py:264`
- Remove `test_no_wrong_15000_mapping` + `test_no_wrong_25000_mapping` from `backend/tests/test_billing_amount_to_plan.py:38-44`
- Add `test_current_autopilot_pricing_150` and `test_current_professional_pricing_250`
- Update `test_all_four_current_tiers_present` to use `{9900, 15000, 25000, 89900}`
- S-effort ~15 min. Moratorium-safe. Closes GH #181.
- **RUN 34 GOVERNANCE SIGNAL**: If GH #181 still unimplemented by run 34, governance mandate fires (4-consecutive-run threshold). Winner must switch.

**/moratorium-sprint remains the standing highest-leverage sprint action:**
- Items A (check_project_invariants pre-commit, ~5 min) + B (widget sync guard, ~15 min) + D (CI eval workflow, ~20 min)
- SKILL.md ready (7985fbb). Moratorium day 20+. Pending 8→4→2 = moratorium exits.

---

## Confidence

**HIGH** — Four independent evidence sources: (1) skill-discovery-2026-05-25 proposed it with 3+ occurrence examples and explicit gap analysis vs existing tools; (2) PR #180 (2174732) + local_seo split (3555645) both required predictable follow-up commits that the skill checklist would prevent; (3) `plans/god-class-refactor_plan.md` lists 54 remaining files confirming long-tail recurrence; (4) nightly review precedent (7985fbb, 2ce31b2) demonstrates this type of skill file can be autonomously created.
