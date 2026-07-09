# Idea 5: email_sequences.py God-Class Split

**Category**: code_health  
**Confidence**: MEDIUM  
**Effort**: L (~2 hours human execution)  
**Autonomous**: NO — requires human to invoke /god-class-splitter  
**Run 41 active_direction**: canonical entry, still pending_approval

## What

`backend/services/email_sequences.py` is 1143L (was 1255L before some trimming). Contains 3 independent concerns:
- **email_crud**: CRUD operations (create, read, update, delete sequences, enrollments)
- **email_enrollment**: enrollment logic (enroll lead, check conditions, pause/resume)
- **email_processor**: background processing (send queued emails, retry logic, rate limits)

GH #112/#113 (N+1 queries) become simpler post-split. Each concern can be reasoned about independently.

## Prerequisites (all met)

- `god-class-splitter SKILL.md` — created by nightly e848b87 (2026-05-26) ✓
- `post-split-test-repair SKILL.md` — created by nightly d481799 (2026-05-30) ✓
- GH #181 billing fix — MOOT (2-plan repricing superseded old AMOUNT_TO_PLAN concerns) ✓
- No active GH #181 blocker ✓

## Why not winner this run

- L effort (2h) vs Idea 1 (5 min S effort)
- No new urgency signal — file is stable at 1143L, no new bugs from it
- Moratorium still active — L-effort features require careful timing
- Pre-commit blockage is more urgent (blocks every developer right now)
- Run 41 active_direction already captures this — no new framing

## When to promote

Promote to winner when:
1. Pre-commit unblocked (Idea 1 done)
2. Plan-name guard added (Idea 2 done)
3. AI-to-Human Handoff shipped (Idea 3 done)
4. Sprint session clears backlog → moratorium exits
5. email_sequences.py grows past 1200L again or new bugs surface from it

## Notes

First production use of god-class-splitter SKILL.md. Cross-reference: run 41 winning-concept.md for full split plan. Run 35 superseded (same item, older framing).
