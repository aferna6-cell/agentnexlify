# Idea 5: email_sequences.py God-Class Split

**Run:** 73 | **Date:** 2026-06-30 | **Origin:** Run 41 pending_approval

## One-line
Split `backend/services/email_sequences.py` into `email_template_service.py` + `email_delivery_service.py` + `email_scheduler.py` to kill the god class.

## Background
- Run 41 recommendation (pending_approval). Code health.
- `backend/services/email_sequences.py`: estimated 600+ lines covering template management, delivery, scheduling, and unsubscribe logic — 4 concerns in 1 file.
- User rule 9: "Don't extend god classes — factor them out." At >600 lines and adding new responsibility, stop and split.

## Evidence
- `docs/dev-knowledge/bug-patterns.md`: CAN-SPAM unsubscribe swallowed silently — buried in email_sequences.py, hard to test in isolation. Factoring would expose the bug surface.
- Moratorium note from run 41: deferred due to active_directions queue. Now at 4-6 pending — still over moratorium threshold.
- No regressions from email code reported in last 30 days. No urgency signal.

## What it involves
1. Read `backend/services/email_sequences.py` in full.
2. Identify 3 concern boundaries.
3. New files: `email_template_service.py`, `email_delivery_service.py`, `email_scheduler.py`.
4. Update all importers of `email_sequences.py`.
5. Regression tests for each split concern.

## Effort
- M (Medium) — 4–6 hours. Refactor + call-site migration + tests.
- Risk: HIGH blast radius. Call sites in `backend/routers/`, `backend/services/automation/`, potentially `managed_agents_registry.py`.

## Why this loses
- M-effort refactor with HIGH blast radius.
- Moratorium still active (true_pending 4-6 after KB fix corrections).
- No customer-facing value — pure code health.
- Rule 8 (no half migrations): must complete in one PR. Any partial split creates ambiguity.
- CAN-SPAM bug is a separate fix — doesn't require the split to fix it.

## Recommendation
Parking lot. Re-evaluate when moratorium lifts (pending queue < 2). Do not re-recommend while SMS Dashboard is pending.
