# Idea 5: Factor email_sequences.py God Class (P-EMAIL)

**Category:** Code Health (architecture)  
**Effort:** M (compound-engineering, multi-file refactor, 2–4h)  
**Autonomous:** NO — M-effort requires human approval + compound-engineering pipeline  
**Source:** Parking lot P-EMAIL (runs 41+, moratorium was blocking)  

---

## Evidence

- `email_sequences.py` is **1143+ lines** (measured at run 70)  
- God class: handles sequence CRUD, scheduling, template rendering, send-queue management, analytics — all in one file  
- Rule 9 (CLAUDE.md): "Don't extend god classes — factor them out" — any new email feature hits this wall  
- P-EMAIL note: "moratorium blocks M-effort items until pending ≤ 2"  
- After run 81 governance corrections: pending = 1 (only run 79 brain connector, pending_human)  
- max_pending_approvals = 2 → **moratorium is now LIFTED for M-effort items**  

## Why Now Eligible

Moratorium was blocking M-effort. After corrections:
- Run 80 Step 9C: implemented ✓
- Run 77 healthz-alert.sh: implemented ✓
- Run 79 brain connector: pending_human (1)
- 1 pending ≤ 2 max → moratorium LIFTED

## Proposed Split

| New file | Responsibility |
|----------|----------------|
| `email_sequences_crud.py` | Create/read/update/delete sequences |
| `email_sequences_scheduler.py` | Schedule + trigger sends |
| `email_sequences_renderer.py` | Template rendering + personalization |
| `email_sequences_analytics.py` | Open/click tracking, completion metrics |
| `email_sequences.py` | Thin orchestrator (imports + re-exports for backward compat) |

## Invariants to Preserve

- Existing `from backend.services.email_sequences import ...` imports continue working  
- No schema changes (email_sequences table unchanged)  
- All existing tests pass without modification  

## Risk

Medium — touches email service, potential regressions. Requires compound-engineering pipeline (brainstorm → plan → execute → review → vertical-check). Not autonomous.

## When to Execute

Run 82+ when: (a) SMS Dashboard delivered by issue-to-pr-loop, (b) brain connector fixed (GH #394), (c) human has bandwidth for M-effort review.

## Parking Lot Status

Keep. Moratorium no longer blocks. Flag as "eligible" in backlog after this run's governance corrections.
