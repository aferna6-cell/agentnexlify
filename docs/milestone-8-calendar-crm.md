# Milestone 8 — Calendar + CRM Business Actions

**Status:** Implementation in progress on `cursor/milestone8-calendar-crm-a2c9`  
**Date:** 2026-08-30  
**Prerequisite:** M7 on main (#707). Migration 198 still unapplied (RAG persist).

## Architecture (locked)

See `planning/decisions/2026-08-30-m8-calendar-crm-architecture.md` and Phase 0
audit `audits/audit-m8-calendar-crm-phase0-2026-08-30.md`.

| Concern | Decision |
|---------|----------|
| Calendar provider | Google via `CalendarPort` → data plane (`google_calendar.py` / `booking.py`) |
| CRM SoT | `leads` (`client_id`, `status`) via `CrmPort` |
| Entity resolution | `agents/_resolve.ts` (exact / unique / multiple / none) |
| Mutations | Action Executor only — no department → provider calls |
| Flags | `CALENDAR_ACTIONS_ENABLED=0`, `CRM_ACTIONS_ENABLED=0` (default OFF) |

## Tools

| Tool | Risk | Notes |
|------|------|-------|
| `get_calendar_availability` | 0 | Never invents slots; provider errors honest |
| `create_calendar_event` | 1 → 2 | L2 when attendees / `send_invitations` |
| `reschedule_calendar_event` | 2 | Approval required |
| `cancel_calendar_event` | 2 | Explicit `event_id` only |
| `get_customer` | 0 | Tenant-scoped |
| `search_customers` | 0 | Never picks among multiple |
| `update_customer` | 1 | Field-level; preserves unspecified |
| `create_customer` | 1 | Duplicate-aware (email then phone) |
| `update_lead_stage` | 1 | Canonical / tenant stages only |
| `add_customer_note` | 1 | Reused; not gated by CRM flag |

## Guarantees (honest)

- **Idempotency:** claim-gated execute + search-before-create fingerprint /
  `idempotency_key`. Without Google idempotency tokens this is **best-effort**,
  not provider-native exactly-once.
- **Verification:** calendar GET after write; CRM field read-back. Status
  `verification_failed` is separate from `succeeded`.
- **Availability:** never fabricated. Empty or provider error is returned as-is.
- **Ambiguity:** multiple name matches → clarification / `kind: multiple`.

## Rollout

```
CALENDAR_ACTIONS_ENABLED=0
CRM_ACTIONS_ENABLED=0
```

Do not enable in production without explicit owner approval + controlled smoke.

## Eval

```bash
python3 agent-service/evals/datasets/calendar-crm/build_calendar_crm_eval_v1.py
cd agent-service && npm run eval:calendar-crm:gate
```

Also rerun M6 `npm run eval:actions:gate` and M7 RAG validation/holdout.

## Live smoke (owner-gated)

Blocked until explicit authorization:

1. Staging tenant + test calendar
2. Internal create → verify → cancel
3. Invite create parks for approval → one event after approve
4. CRM update on staging lead → read-back + audit row

## Out of scope

SMS, computer use, browser automation, general multi-step planner, ten CRM
vendors, RL/active learning.

## Status honesty

**Offline Action Executor + policy + evals + flag-gated department resolvers:** ready for review.

**Not yet production-complete Milestone 8:**

- Live Google Calendar / appointments data-plane persistence after Collecting ports
- Controlled live Calendar + CRM smoke (owner authorization required)
- Natural-language booking still requires explicit ISO start/end (by design — no invented times)
- Flags remain default OFF

Rollback: keep `CALENDAR_ACTIONS_ENABLED=0` and `CRM_ACTIONS_ENABLED=0`.
