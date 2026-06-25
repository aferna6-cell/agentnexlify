# Idea 02 — Extend Nightly Scope to Cover cp + Text Replacement

**Category:** workflow_efficiency
**Confidence:** MEDIUM
**Autonomous-executable:** possibly YES (meta)

## Proposal
Extend nightly-commit-review SKILL.md autonomous scope to cover:
- Shell `cp` commands between known file pairs
- sed/Python text replacements in JSX/JS files when winning-concept specifies them

## Why it could work
- Makes the delivery chain truly autonomous for a broader class of fixes
- Step 9B (from run 66) could be delivered first, then broader scope follows
- Lower human intervention required going forward

## Fatal flaw
This IS the meta-fix layer run 65 mandate explicitly forbids.

Run 65 winning-concept.md line 108-112:
> "Do NOT add yet another layer of meta-fixes — go direct (interactive execution path)"

Adding "extend nightly scope to cover cp + sed" is exactly the pattern that failed:
- Run 65 added AUTONOMOUS-EXECUTABLE label → nightly didn't pick it up (scope mismatch)
- Run 66 added Step 9B to nightly SKILL.md → nightly didn't pick it up (existing-SKILL.md not in scope)
- Run 67 adding "extend scope for cp/sed" → same risk, same chain, same delay

The fix required is the fix. Not a fix to the fix.

## Verdict: REJECTED
Idea 01 delivers the same outcome in 1 interactive session vs. potentially 3+ more
failed nightly cycles. Meta-fix rejected per mandate.
