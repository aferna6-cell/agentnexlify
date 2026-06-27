# Idea 04 — Pre-Commit Auto-Sync: Check 13 Executes the Fix

**Category:** Code Health  
**Evidence anchor:** `check_project_invariants.py` widget drift check always knows what to sync

## What
Amend `check_project_invariants.py` invariant #4 (widget byte-sync) to execute the fix when drift is detected, rather than just reporting it. Add `--fix` flag:

```python
if args.fix and drifted:
    for src, dst in mirror_pairs:
        if not filecmp.cmp(src, dst):
            shutil.copy2(src, dst)
            print(f"  FIXED: synced {dst} <- {src}")
```

Pre-commit hook (Check 13) passes `--fix` automatically, or nightly passes `--fix` as part of its invariant scan.

## Why
The subconscious loop has spent 5 runs recommending the same 1-line fix. Root cause: the check knows the problem but cannot execute the remedy. A `--fix` mode makes the checker self-healing. Invariant checks that can auto-fix are strictly more useful than ones that only report.

## Risk
- Modifying `check_project_invariants.py` (2+ files: the script + pre-commit hook)
- Auto-fixes in pre-commit hooks can be surprising; some dev workflows reject this pattern
- `landing-page-v2/` is FORBIDDEN territory — an auto-cp to legacy paths needs explicit approval
- Scope creep: other invariants would want `--fix` too (out of scope for this run)

## Verdict signal
Addresses root cause. High leverage long-term. But requires code change in check script (wider blast radius than a SKILL.md amendment).
