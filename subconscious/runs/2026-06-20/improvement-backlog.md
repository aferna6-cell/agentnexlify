# Improvement Backlog — Run 63 (2026-06-20)

Last updated: 2026-06-20

## Priority Queue

### P0 — Revenue / Active Breakage (implement immediately on human approval)

| ID | Title | Effort | Status | Notes |
|----|-------|--------|--------|-------|
| GH #308 | Fix webhook idempotency early-write (stripe_webhooks.py + idempotency.py) | S (20 min) | **RUN 63 WINNER** — pending_approval | 5 consecutive cycles. Moratorium override. |
| GH #292/#293 | Wire chatbot/agent_os into sms_rate_limiter + api_key_auth + billing_reconciliation | S (20 min) | pending_approval | Day 4. Moratorium override. Bonus A for run 63. |

### P1 — Structural Risk (triage required before fix)

| ID | Title | Effort | Status | Notes |
|----|-------|--------|--------|-------|
| GH #263 | 24 pending migrations — query Supabase schema_migrations vs migrations/ | M | Parked | ROI 2.3. Triage first — may be stale tracker. |

### P2 — Operational (fix when P0/P1 clear)

| ID | Title | Effort | Status | Notes |
|----|-------|--------|--------|-------|
| KB stale | Fix kb-autopopulate.sh (agent-browser CLI missing) | S | Parked | 46 days stale. ROI 1.8. Replace with curl/WebFetch fallback. |

### P3 — AUTONOMOUS-EXECUTABLE (sequence-blocked)

| ID | Title | Effort | Status | Notes |
|----|-------|--------|--------|-------|
| check_7 | Add plan-name guard to check_project_invariants.py | XS (~15 lines) | Sequence-blocked | AUTONOMOUS-EXECUTABLE. Must wait for GH #292/#293 fix. Bonus B. |

### Parked — God Classes (address during next improve-architecture pass)

| File | Lines | Notes |
|------|-------|-------|
| `frontend/src/pages/Home.jsx` | ~1006 | Split on next architecture session |
| `backend/services/email_sequences.py` | ~1143 | Split on next architecture session |

---

## Implemented This Run

None — run 63 is recommendation-only. Human approves before execution.

---

## Running P0 Counter

GH #308: flagged runs 59, 60, 61, 62, 63 → **5 consecutive cycles unimplemented**
GH #292/#293: flagged runs 61, 62, 63 → **3 consecutive cycles unimplemented (as winner in run 62)**

---

## Mandate Chain

- Run 59: GH #308 wins (first flag)
- Run 60: GH #308 wins (2nd)
- Run 61: GH #308 wins (3rd, mandate set for run 62)
- Run 62: GH #292/#293 wins (run 62 mandate fires — GH #308 unimplemented 4 cycles)
- Run 63: GH #308 wins (run 63 mandate fires — GH #292/#293 unimplemented)
- **Run 64**: GH #292/#293 wins if GH #308 still unimplemented (run 64 mandate fires)

---

## Frozen Ideas

None currently frozen.
