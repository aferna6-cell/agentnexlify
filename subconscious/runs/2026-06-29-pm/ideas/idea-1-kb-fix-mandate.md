# Idea 1 — KB Autopopulate Fix: Mandate Nightly 2026-06-30

## Category
Code Health / Operational

## Evidence
- Run 71 winner (2026-06-29): fix kb-autopopulate.sh — add WebFetch to --allowedTools, correct false DISCOVER_PROMPT instruction
- AUTONOMOUS-EXECUTABLE label confirmed in run 71 winning-concept.md
- Step 9B confirmed in nightly SKILL.md (lines 65-67)
- CRITICAL TIMING: nightly 2026-06-29 ran BEFORE run 71 was committed (git order: 291819f nightly commit → f7195cd run 71 commit)
- Result: run 71 hasn't had a nightly implementation cycle yet
- 2026-06-30 nightly = FIRST implementation opportunity for run 71 fix
- kb-autopopulate.sh broken 53+ days; knowledge base stale

## Problem
Run 71 recommended a 2-line fix to scripts/daily/kb-autopopulate.sh. That fix has not yet been implemented because nightly ran before the recommendation was committed. Nightly 2026-06-30 is the first test of whether Step 9B picks it up.

## Critical gap in Step 9B scope
Step 9B (nightly SKILL.md lines 65-67) covers:
- New `.claude/skills/*/SKILL.md` creation
- Bash additions to `scripts/hooks/pre-commit`
- New GitHub workflow YMLs

It does NOT explicitly cover arbitrary bash script edits to `scripts/daily/kb-autopopulate.sh`. This creates a risk that Step 9B runs, doesn't match the kb fix, and the fix is silently skipped.

## Recommendation
Re-confirm run 71 winner as run 72 winner. Winning-concept.md for run 72 should:
1. Confirm: nightly 2026-06-30 is the first cycle to attempt the kb fix
2. Provide explicit fallback fix instructions for human if Step 9B scope doesn't match
3. Label AUTONOMOUS-EXECUTABLE-WITH-FALLBACK

## Effort
XS — this is documentation + mandate, not new code

## Risk
LOW — re-confirming a prior fix, providing human fallback path
