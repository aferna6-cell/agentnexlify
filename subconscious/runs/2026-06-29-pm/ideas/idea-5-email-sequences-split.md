# Idea 5 — email_sequences.py God-Class Split (30+ Days Pending)

## Category
Code Health

## Evidence
- Run 41 winner (30+ days ago): split email_sequences.py god class
- File reported at 700+ lines (exceeds 600-line threshold per user-rules.md Rule 9)
- god-class-splitter skill exists + post-split-test-repair skill exists
- No new code in email_sequences.py recently (no conflict risk)
- Nightly commit review: no recent changes to this file

## Problem
backend/services/email_sequences.py has accumulated concerns: sequence orchestration, template rendering, Resend API calls, scheduling logic, unsubscribe handling. All in one file. Hard to test individual concerns. Adding new sequence types requires touching the whole file.

## Recommendation
Split into 4 modules:
- email_sequences/orchestrator.py — sequence lifecycle, state machine
- email_sequences/renderer.py — template + variable substitution
- email_sequences/sender.py — Resend API wrapper
- email_sequences/scheduler.py — timing logic, cron expression parsing

Post-split: run post-split-test-repair skill to ensure all tests pass.

## Effort
M — 4 new files, move code, update imports, run tests

## Risk
MEDIUM — refactor of active service; needs full test pass. No schema changes.

## Status
HUMAN-REQUIRED — multi-file refactor, needs human review per user-rules.md Rule 1
