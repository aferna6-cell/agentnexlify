# War room — Milestone 8 Calendar + CRM architecture

**Date:** 2026-08-30  
**Status:** Accepted for implementation (Phase 0 audited)  
**Chief of Staff:** consolidated from Integration / Calendar / CRM / Safety / Eval / Agent OS briefs.

**Gate:** M7 code is on `main` (#707). Migration 198 remains unapplied (RAG chunk persist). M8 does not block on 198 for Calendar/CRM tools; RAG regression still runs offline.

---

## Phase 0 verdict

Usable infrastructure exists. M8 extends the **Action Executor + ports + data plane** pattern; it does **not** invent parallel connector stacks.

Canonical sources:
- Calendar SoT: local `appointments` + `business_hours`; Google Calendar is the production external mirror.
- CRM SoT: `leads` (`client_id`, `status`); HubSpot optional outbound; Zapier stays.

---

## Decisions (locked)

### 1. Canonical calendar provider / interface

**Decision:** Google Calendar is the M8 production external provider.  
Agent OS tools talk only to **ports** (`CalendarPort`), which call `backend/services/google_calendar.py` and `booking.py`.  
M365 remains OAuth+create for existing OS deliverable path; **M8 does not expand M365 freebusy/update/delete** unless a follow-on proves need.  
Calendly archive stays dead.

### 2. Timezone normalization

**Decision:** Availability computed in `business_hours.timezone` (default `America/New_York`).  
All stored appointment/event times are UTC.  
Tool I/O accepts explicit `timezone` (IANA); if omitted, use business timezone.  
Approval UI must show local wall-clock **and** timezone.  
Never invent availability when freebusy is unverifiable (preserve C5 fail-closed).

### 3. Event idempotency strategy

**Decision:**  
- L1 internal-only create: `idempotency_key` on `os_tool_executions` + unique natural key search (tenant + start/end + title + customer) before insert.  
- L2 create with external invite: required idempotency key (same as email L2) + provider fingerprint where available; search-before-create on Google when practical; store `google_event_id` on success.  
- Document honestly: without Google idempotency tokens, guarantee is **best-effort dedupe + claim-gated execute**, not perfect provider-native idempotency.

### 4. External attendee approval semantics

**Decision:**  
- Internal-only event (no attendees / no invitations): **L1**.  
- Any external attendee or invitation send: **L2**, explicit approval, approval card shows datetime, timezone, title, attendees, invitation flag.  
- Prompt-injection / “owner already approved” in notes or RAG **cannot** bypass policy.

### 5. Canonical CRM / customer source of truth

**Decision:** `leads` is the customer record. No new `customers` table.  
Use `client_id` and `status` (never `tenant_id` / `lead_stage` on leads).

### 6. Duplicate-customer resolution

**Decision:**  
- Name resolution: `_resolve.ts` only (migrate `add_customer_note` local matcher onto it).  
- Multiple matches → clarify; never first-row.  
- Create: check email (unique constraint) then phone before insert.  
- Dashboard merge/duplicates APIs remain human tools.

### 7. CRM pipeline validation

**Decision:** `update_lead_stage` accepts only statuses in the tenant’s `pipeline_stages` (or the canonical closed set if stages empty). Free-text stages rejected.

### 8. Internal vs external CRM abstraction

**Decision:** M8 tools mutate **internal** `leads` first. HubSpot sync is out of band / existing deliverable path — not required for Action Executor v1. No new CRM vendors.

### 9. Verification strategy

**Decision:**  
- Calendar mutate: after write, **GET event** (or DB row + GCal get when synced); compare start/end/title/attendees; `execution succeeded` ≠ `verification failed` as separate axes.  
- CRM mutate: read-back field(s) like `add_customer_note`.  
- Availability: never fabricate; empty/error is honest.

### 10. Rollout flags

**Decision:**  
```
CALENDAR_ACTIONS_ENABLED=0   # default OFF
CRM_ACTIONS_ENABLED=0        # default OFF
```
Mirror `SEND_EMAIL_ENABLED` / `RAG_ENABLED` fail-closed pattern.  
Read-only L0 tools still require the flag on (or a separate `*_READ_ENABLED` if we split later — v1: one flag each covering the tool family).

---

## Specialist briefs (compressed)

### Integration Architecture
Reuse `integrations` + vault; wrap Google via ports; ignore orphaned `booking_gcal` pending_sync.

### Calendar Agent
Tools: `get_calendar_availability` (L0), `create_calendar_event` (L1/L2), `reschedule_calendar_event` (L2 if customer-facing), `cancel_calendar_event` (L2 if customer-facing).

### CRM Agent
Tools: `get_customer` / `search_customers` (L0), `update_customer` / `create_customer` / `update_lead_stage` (L1), reuse `add_customer_note`.

### Safety / Reliability
Tenant scope on every call; cross-tenant IDs fail closed; L2 claim-before-execute; dual approval / retry tests mandatory.

### Evaluation
New `evals/datasets/calendar-crm/` validation set (~200–350); hard negatives; M6/M7 regression gates required.

### Agent OS Integration Reviewer
Departments propose via resolvers only; RAG for business knowledge; CRM/Calendar for operational state; no direct provider calls from skills.

---

## Open items (owner-gated, not blockers for offline build)

1. Apply migration 198 when ready (M7 persist).  
2. Controlled live Calendar smoke on staging calendar + explicit approval.  
3. Controlled CRM smoke on staging lead.  
4. Whether to split read vs mutate flags later.

---

## Build order

1. Flags + ports skeletons  
2. L0 availability + L0 get/search customer  
3. L1 CRM mutations + verify  
4. L1/L2 calendar create + verify + idempotency  
5. Reschedule/cancel  
6. Eval dataset + safety cases  
7. M6/M7 regression  
8. Live smoke (owner authorization)
