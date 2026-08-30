# War room — M8 finalization path map (2026-08-30)

**Branch:** `cursor/milestone8-finalize-a2c9`  
**Base:** `main` @ #709 merged; migration 198 **APPLIED**.

## End-to-end map

```
Owner ask
  → orchestrate (agent-service)
  → department resolveAction (flag-gated)
  → executeAction (policy + audit row)
      L0/L1: Collecting ports (request-local), seeded from SharedContext
      L2: park pending_approval (no provider)
  → FastAPI persist_tool_executions
      notes → apply_customer_notes (REAL) ✅
      customers → apply_crm_mutations (REAL) ✅
      calendarEvents → apply_calendar_mutations (REAL L1) ✅
  → owner approve (L2)
      send_email → os_tools.run_tool + Gmail ✅
      calendar L2 → run_calendar_l2 + booking/google ✅
      other → engine Collecting + apply bundles
  → verification axis separate from status
```

## Production vs Collecting

| Surface | Pre-finalize | After finalize |
|---------|--------------|----------------|
| `add_customer_note` | Collecting → apply | unchanged ✅ |
| `send_email` | claim → Gmail | unchanged ✅ |
| Calendar L0 availability | empty InMemory (false free) | SharedContext busy / fail-closed ✅ |
| Calendar L1 create | Collecting only | Collecting + `apply_calendar_mutations` ✅ |
| Calendar L2 | engine Collecting | claim → `run_calendar_l2` ✅ |
| CRM L0/L1 | Collecting only | seed leads + `apply_crm_mutations` ✅ |

## Decisions (locked)

1. L1 CRM + internal calendar: notes-style apply + read-back.
2. L2 calendar: email-style claim → provider → verify.
3. Idempotency: best-effort (not Google exactly-once).
4. Flags default OFF until staging proof.
5. Dual stacks: do not merge `os_actions/calendar.py` into Action Executor.

## Remaining (owner-gated)

- Live staging Calendar + CRM smoke (Google OAuth / test tenant)
- RAG / Gmail controlled enablement per `docs/feature-rollout-matrix-m8.md`
