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

# God-Class Splitter

Execution arm for god-class splits. Picks up where `improve-architecture` (diagnosis) and `tech-debt` (ranking) leave off. Prevents the stale-importer and stale-@patch follow-up commits that have appeared after every split this week.

## When to invoke

- File exceeds 600 lines (CLAUDE.md Rule 9)
- `improve-architecture` or `tech-debt` flags a file as CRITICAL or HIGH
- User says "split X", "factor out X", "X is too big", "refactor god class in X"

## 12-Step Checklist

**Step 1.** Read `plans/god-class-refactor_plan.md` — check if the target file is queued with a suggested split axis. Use that axis if present; propose one if absent.

**Step 2.** `wc -l <target>` — confirm it exceeds 600 lines. If under threshold, abort and say why.

**Step 3.** Read the full file — identify 2-3 independent concerns. Name each concern explicitly before proceeding.

**Step 4.** Propose module names (`<concern>_service.py`, `<concern>_fetch.py`, etc.). If the naming is ambiguous, wait for approval before extracting.

**Step 5.** Extract each concern to its new module — move only symbols that belong to that concern. No copy-paste residue in the original.

**Step 6.** Grep all importers:
```bash
grep -rn "from backend.services.old_module\|import old_module" .
```
Update every call site in the same pass. No exceptions. No stale references left behind.

**Step 7.** Delete or thin the original file. No re-export shims (`from new_module import *`). No `# removed` comments.

**Step 8.** If the split produced new router files, register them in `backend/main.py` (lines 746-813).

**Step 9.** Run tests:
```bash
python3 -m pytest <relevant_test_files> -x --tb=short -q
```
Confirm pass count is unchanged from pre-split baseline.

**Step 10.** Verify no stale importers remain:
```bash
grep -rn "backend.services.old_module" .
```
If results appear, fix them before committing. This step is mandatory — it is the step that prevents every follow-up commit from PR #180 and the local_seo split.

**Step 11.** Write `tests/test_extracted_<module>.py` smoke tests covering the new module's public surface. Minimum 5 test functions covering key endpoints and pure functions.

**Step 12.** Commit atomically:
```
refactor(<concern>): split <old_module> → <new_modules> (Rule 9)
```
One PR, no half-splits. The old module must be gone or explicitly deprecated with a plan for the remaining call sites (Rule 8 — no half migrations).

---

## Post-Split Test-Repair Sub-Step

If tests fail after the split:

1. Run:
   ```bash
   python3 -m pytest tests/ -x --tb=short -q 2>&1 | head -40
   ```
2. Identify the old module path in the failure (e.g. `backend.routers.old_router._function`).
3. Find all stale `@patch` decorators and imports:
   ```bash
   grep -rn "old.module.path" tests/
   ```
4. Update each to the new canonical path.
5. Re-run pytest — repeat until green.
6. Commit separately:
   ```
   test: repoint stale patch targets after <split> refactor
   ```

---

## Cross-refs

- `plans/god-class-refactor_plan.md` — 54 remaining files (29 backend + 25 frontend) with split axes
- `.claude/skills/improve-architecture/SKILL.md` — hands off top-ranked CRITICAL file to this skill
- `.claude/skills/tech-debt/SKILL.md` — ranking produces input priority list
- `.claude/rules/user-rules.md` Rule 9 — don't extend god classes, factor them out
- `.claude/rules/user-rules.md` Rule 8 — no half migrations; all call sites must move
- `CLAUDE.md` Critical Invariants — `client_id` not `tenant_id`, no `__future__` annotations
