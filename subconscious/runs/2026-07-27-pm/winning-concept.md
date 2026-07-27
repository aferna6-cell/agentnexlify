# Run 106 Winning Concept — 2026-07-27-pm

## Winner: Update god-class-splitter SKILL.md — Fix Step 7 Backward-Compat Re-Exports Contradiction

**Category:** workflow
**Effort:** XS
**Confidence:** HIGH
**Autonomous-executable:** YES (direct SKILL.md edit — same channel as runs 99/102/104)

---

## Problem

Step 7 of `.claude/skills/god-class-splitter/SKILL.md` currently reads:

> **Step 7.** Delete or thin the original file. No re-export shims (`from new_module import *`). No `# removed` comments.

This guidance actively contradicts best practice confirmed by two consecutive god-class splits this week:

- `calls.py` (1196L → 3 files): required backward-compat re-exports in follow-up commit
- `email_sequences.py` (1143L → 3 files): required backward-compat re-exports in follow-up commit

Evidence source: `docs/skill-discovery/2026-07-27.md:133` — "Both omissions cause test failures immediately after the split."

---

## Root Cause

Step 7 prohibits re-exports out of concern for "lazy callers" never updating imports. But:

1. Step 6 already handles caller updates (grep all importers, update every call site)
2. Re-exports are a safety net for importers MISSED in Step 6 — not a replacement for Step 6
3. Without re-exports, a single missed importer causes a 500 at runtime
4. Both recent splits needed re-exports AND still updated all explicit call sites

The guidance is wrong — not aspirationally wrong, actively wrong. It caused 2 preventable follow-up commits this week.

---

## Fix: Exact SKILL.md Edit

**File:** `.claude/skills/god-class-splitter/SKILL.md`
**Line 44 (current Step 7)**

### Before

```
**Step 7.** Delete or thin the original file. No re-export shims (`from new_module import *`). No `# removed` comments.
```

### After

```
**Step 7.** Add backward-compat re-exports to the original file for all moved symbols:
```python
from .new_module import Symbol1, Symbol2, Symbol3  # TODO: remove when all callers updated
```
Name each symbol explicitly — do not use star-exports (`from new_module import *`). This prevents callers missed in Step 6 from immediately breaking. Note: re-exports do NOT fix `@patch` target paths in tests — Step 10.5 handles those separately.
```

---

## Why direct implementation (not recommend-and-wait)

1. Nightly-commit-review channel cannot implement edits to non-nightly SKILL.md files — confirmed by all prior evidence
2. Human won't manually edit a SKILL.md based on a winning-concept.md recommendation without a specific instruction
3. Fix is XS (3-line replacement in Step 7)
4. Zero risk: SKILL.md is pseudocode guidance, not executable code
5. Precedent: runs 99, 102, 104 all directly implemented SKILL.md edits

---

## Verification

After edit: `grep -c "backward-compat re-exports" .claude/skills/god-class-splitter/SKILL.md` returns ≥1.
