---
name: post-split-test-repair
description: Repair stale @patch targets and imports after any module split or API cleanup migration. Invoke immediately after every god-class split or migration that relocates symbols.
version: 1.0.0
origin: agentnexlify
user-invocable: true
triggers:
  - after god-class split
  - after module extraction
  - after API cleanup migration
  - stale @patch error
  - ImportError after split
  - post-split-test-repair
---

# Post-Split Test Repair

Run this checklist after EVERY module split before committing. Takes ~15 min. Prevents CI-red repair commits.

## Recurrence evidence (100% rate)
- `5f2cd2b`: test-repair after local_seo.py split
- `4afb3cf`: import-repair after local_seo.py split (second repair same day)
- `bca2082`: test-mock-repair after API cleanup migration (.filter() chain fix)

Every god-class split or API migration in this codebase has generated a stale-patch repair commit. Without this checklist, a split PR will become split PR + CI-red + repair PR.

## Step 1 — Find test files importing split symbols
```bash
grep -rn "from backend.routers.<old_module> import\|from backend.services.<old_module> import" backend/tests/
```
Replace `<old_module>` with the file being split (e.g. `email_sequences`).

## Step 2 — Find all @patch decorators targeting old paths
```bash
grep -rn "@patch.*<old_module>" backend/tests/
```

## Step 3 — Determine new home of each symbol
Check the split output: which symbol moved to which new file?
- CRUD functions → `<name>_crud.py`
- Enrollment/trigger logic → `<name>_enrollment.py`
- Processing/execution logic → `<name>_processor.py`

## Step 4 — Update @patch paths
```python
# Before
@patch("backend.routers.email_sequences.send_email")
# After
@patch("backend.services.email_crud.send_email")
```

## Step 5 — Update import statements in test files
```python
# Before
from backend.routers.email_sequences import list_sequences
# After
from backend.services.email_crud import list_sequences
```

## Step 6 — Check __init__.py re-exports
If the old module re-exported symbols via `__init__.py`, ensure the new modules are also exported. Add to `backend/services/__init__.py` if needed.

## Step 7 — Run targeted test suite
```bash
python -m pytest backend/tests/ -k "<split_module_name>" -x --tb=short
```
Fix any remaining import errors before committing.

## Step 8 — Commit repair in the same PR as the split
Do NOT commit the split without the repair. One PR = split + repair. If repair is discovered post-commit, amend before push (not after push to main).

## Cross-refs
- `.claude/skills/god-class-splitter/SKILL.md` — invoke this skill at step 6.5 of every split
- `docs/dev-knowledge/bug-patterns.md` — stale @patch pattern entry
- `god-class-refactor_plan.md` — 54 files remaining; each will need this checklist
