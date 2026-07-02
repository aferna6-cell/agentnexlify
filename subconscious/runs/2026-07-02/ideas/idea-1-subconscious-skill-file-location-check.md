# Idea 1: Add File-Location Verification to Subconscious Evidence Phase

**Category:** agent_performance / workflow  
**Effort:** XS  
**AUTONOMOUS-EXECUTABLE:** YES (SKILL.md edit — same class as runs 40/43 precedent)

## Evidence

Runs 75 and 76 wasted two full debate cycles tracking Zapier plan_status enforcement (GH #107) as unimplemented. The fix was already shipped on 2026-06-13 in `backend/routers/zapier.py:121-128`. The subconscious failed to detect this because it searched for `backend/services/zapier_auth.py` (a file that does not exist) and concluded `zapier_file_found: false` → assumed unimplemented.

Root cause: governance.json notes specified a file path that was wrong. The subconscious's Phase 2 evidence gathering trusted the path literally without greping for the function/symbol first.

This is not a one-off. Any time governance notes contain a file path assumption, the same failure mode can recur.

## Action

Add one step to Phase 2 (Gather Evidence) of `.claude/skills/subconscious/SKILL.md`:

> When reviewing active_directions items for implementation status:  
> 1. If a note specifies a file path, verify the file EXISTS before concluding it is the correct implementation target.  
> 2. If the file does not exist, grep for the key function/symbol (`grep -r "symbol_name" backend/ --include="*.py" -l`) to locate the actual implementation.  
> 3. Only mark as "unimplemented" if grep returns zero results — not if the expected file path is absent.

Patch target: `.claude/skills/subconscious/SKILL.md` Phase 2 section (after the existing evidence-gathering bash commands, before the 200-word summary instruction).

## Expected Impact

- Prevents 2-run wasted cycles (the B-001 incident cost 2 debate rounds)
- Makes implementation status checks accurate regardless of refactoring-induced path changes
- Zero human approval needed — nightly can apply the SKILL.md edit tonight
- Compounds: every future run benefits

## Why Now

Fresh evidence. Two concrete wasted runs. Zero prior proposals.
