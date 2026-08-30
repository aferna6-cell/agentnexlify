# Audit — Milestone 8 Phase 0: Calendar + CRM infrastructure

**Date:** 2026-08-30  
**Branch:** `cursor/milestone8-calendar-crm-a2c9`  
**Prerequisite:** M7 code merged via #707; migration 198 **not yet applied** (RAG persist optional for M8).

---

## War-room answers (required)

### 1. Which Calendar integrations exist?

| Provider | Capabilities | Path | Production? |
|----------|--------------|------|-------------|
| **Google Calendar** | OAuth, create/update/delete, freebusy | `backend/services/google_calendar.py`, `routers/integrations.py` | **Yes** |
| **Microsoft 365** | OAuth + create only | `backend/services/m365_calendar.py` | Partial |
| Calendly | Stub | `_archive/backend/services/calendar.py` | Dead |
| iCal export | Busy blocks only | `routers/appointments.py` | Shipped |

### 2. Which CRM/customer capabilities already exist?

| Capability | Evidence |
|------------|----------|
| Canonical customer store | **`leads`** table (`client_id`, `status`, `areas_of_interest`) — **no separate customers table** |
| Pipeline | `pipeline_stages` + `leads.status` (`new`→…→`closed`/`lost`) |
| Notes / activity | `client_notes`, `activity_log`, Action tool `add_customer_note` |
| Dashboard CRM | Clients, Leads, Pipeline, Calendar pages |
| External | HubSpot OAuth upsert; Zapier `new_lead` export |
| Entity resolution | `agent-service/.../agents/_resolve.ts` (exact / unique / multiple / none) |

### 3. Production vs prototype?

**Production:** Google OAuth + freebusy + booking slots; `appointments` + EXCLUDE double-book; dashboard/widget book/reschedule/cancel; leads/clients/pipeline APIs; HubSpot+Zapier; Action Executor (`get_business_profile`, `add_customer_note`, `send_email`); OS deliverable `calendar.event.create` / `crm.contact_upsert`.

**Prototype / orphaned:** `booking_gcal.py` pending_sync / `gcal_event_id` (mismatched schema; not wired); `appointment_sync` dispatcher unregistered; Calendly stub; agent-service booking agent = SMS drafts only.

**Missing for M8 Agent OS tools:** `get_calendar_availability`, `create_calendar_event`, `reschedule_*`, `cancel_*`, `get_customer`, `search_customers`, `update_customer`, `update_lead_stage`, `create_customer` in Action Executor registry.

### 4. Which credential system to reuse?

`integrations` table + `integration_key_vault` Fernet (`access_token_enc` / `refresh_token_enc`, migration 148). Providers: `google_calendar`, `m365_calendar`, HubSpot. **Do not invent a parallel OAuth store.**

### 5. Which tables are canonical?

| Domain | Canonical |
|--------|-----------|
| Appointments | `appointments` (+ `business_hours`, `google_event_id`) |
| Customers | `leads` (`client_id`, `status`) |
| Notes | Prefer unify toward Action path → `leads.notes` verify today; dashboard also uses `client_notes` |
| Agent mutations audit | `os_tool_executions` |
| Activity timeline | `activity_log` |

### 6. Which integrations support independent verification?

| Integration | Fetch-after-write? |
|-------------|-------------------|
| Gmail send | Fingerprint / adopt (M6) |
| `add_customer_note` | Port + data-plane read-back |
| Google Calendar create | **No** — trusts create response id |
| HubSpot upsert (deliverable) | Hard-fail on push; no Action Executor verify loop |
| Local appointment row | Booker sometimes checks DB row exists |

**M8 must add provider GET verification for calendar mutations.**

---

## Agent OS Action Executor gaps

- Registry tools today: L0 profile, L1 notes, L2 email only.
- `ToolPorts` has only `customerNotes`.
- Department `runAction` does not mint L2 idempotency keys (hole for any new L2).
- SharedContext appointments/leads are thin (no freebusy, no lead email/phone in context — by design for send).
- Booking agent does not mutate calendar.

---

## Explicit non-goals confirmed by audit

- Do not rebuild Google OAuth.
- Do not add Salesforce/Jobber/ServiceTitan/GHL native connectors in M8.
- Do not put live customer state into RAG.
- Do not call calendar providers from department skills.
- Do not revive orphaned `booking_gcal` pending_sync without a schema redesign — prefer `google_calendar.py` + `booking.py`.
