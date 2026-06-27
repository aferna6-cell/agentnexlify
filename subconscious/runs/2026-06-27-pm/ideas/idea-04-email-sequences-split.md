# Idea 04: Email Sequences Split (run 41 pending direction)

**Category:** code_health
**Effort:** M (2 hours — god-class-splitter SKILL.md ready)
**ROI:** 2.3 (GH #112/#113 N+1 fix easier post-split, 1255L file)
**Age:** run 41 direction, ~6 weeks pending
**Autonomous:** No — human required (god-class-splitter invocation)

## Evidence

- governance.json `active_directions` includes run 41 "Extract Email Sequences Module" as pending_approval
- `parking_lot`: "Extract _process_pending_sends() from email_sequences.py (GH #113, 2026-05-02, ROI 1.8)"
- `parking_lot`: "Fix email_sequences N+1 queries (GH #112, ROI 2.3)"
- god-class-splitter SKILL.md exists (created by run 35 winner, 2026-05-26-pm)
- email_sequences.py confirmed 1255L with 3 clean concerns: enrollment management, scheduler, send loop

## What

Split `backend/services/email_sequences.py` (1255L) into 3 modules:
- `email_sequences_enrollment.py` — enrollment create/cancel/pause
- `email_sequences_scheduler.py` — scheduler loop, process_sequences
- `email_sequences_send.py` — _process_pending_sends, delivery logic

After split: GH #112 N+1 fix targets only `email_sequences_send.py` (clean concern boundary).
GH #113 extract helper becomes trivial (already in separate file).

## Risk

- M effort — not XS or S
- Moratorium blocks M-effort items (true_pending ~6 > max_pending_approvals:2)
- `@patch` targets in tests change post-split — need post-split-test-repair skill (parking_lot)
- god-class-splitter SKILL.md ready but first-use was run 35 — tool validated in practice

## Debate Position

**WEAK for run 70.** Moratorium blocks M-effort. No new forcing function (same situation as runs 66-69 where it was weakened). Infrastructure (god-class-splitter) is ready but execution requires human and moratorium lift.

**Verdict:** WEAKENED → parking lot. Remains run 41 active direction. Promote to winner post-moratorium exit.
