# Idea 04 — Split email_sequences.py (God Class)

**Category:** Code Health  
**Effort:** M (2-3 hours with god-class-splitter skill)  
**Confidence:** MEDIUM  
**Prior recommendation:** Run 41 (2026-05-30) — pending_approval since then  
**Moratorium interaction:** Adds pending_approval. Currently at max.

---

## The Gap

`backend/routers/email_sequences.py` is 1143 lines with 3 clean concerns:
- **email_crud** — CRUD operations on sequences and steps
- **email_enrollment** — contact enrollment logic
- **email_processor** — background send/process loop

God class confirmed by `docs/dev-knowledge/` architecture notes. `wc -l backend/routers/email_sequences.py` → 1143.

---

## Prerequisites (All Met)

- `god-class-splitter` SKILL.md exists (e848b87, 2026-05-26)
- `post-split-test-repair` SKILL.md exists (d481799, 2026-05-30)
- GH #181 billing fix is MOOT (2-plan repricing cleared old blocker)
- No circular dependencies in email_sequences.py (pre-verified run 41)

---

## What to Build

Split into:
- `backend/routers/email_crud.py` (~280 lines) — CRUD endpoints
- `backend/services/email_enrollment.py` (~400 lines) — enrollment service
- `backend/services/email_processor.py` (~300 lines) — background worker
- `backend/routers/email_sequences.py` → thin router, imports from above

Update imports in `main.py` (lines 746-813). Run `post-split-test-repair` after.

---

## Debate Considerations

WEAKENED → parking lot. Valid, prerequisites met, god-class-splitter skill makes this tractable.

But: moratorium is active (true_pending ~6). Pre-commit was blocked since run 65 (now resolved by mandate action, but still within current run). Split is M-effort, non-urgent, no active breakage.

Correct sequence: SMS Dashboard first (direct customer value, S-effort), then email_sequences split in a later run.

Run 71 candidate if moratorium remains active and one pending item resolves.
