# Spec — Phase 3a: Ops Automation Surfacing

**Status:** Approved · 2026-04-21
**Owner:** Aidan
**Phase:** 3a of onboarding friction reduction (audit-onboarding-2026-04-21.md)
**Priority:** P1 — gates the "AI employee for small trades" demo claim
**Target ship:** V1 in 3-5 weeks

---

## 1. Overview + Motivation

The onboarding audit (2026-04-21) found one damning pattern: backend capability far exceeds frontend exposure. Finding #2 states it plainly: "Major features exist server-side with zero UI." The appointment booker code is live in `backend/services/appointment_booker.py` and has never been called from a real HTTP route. The missed-call text-back fires via `backend/routers/twilio_webhooks.py:78` but writes nothing to the database and surfaces no event in the dashboard. Tenants who signed up for the "AI employee" pitch have no evidence it is doing anything.

This PRD covers Phase 3a: wiring those two ghost automations to the dashboard and widget so they are visible, controllable, and demoable. It is not a new feature build — it is an integration pass on existing code that makes the platform's existing claim true. The automation product claim is "your AI employee handles missed calls and books appointments." After Phase 3a, that claim will be demonstrably true in a 5-minute sales demo for any Growth+ tenant with Twilio + Google Calendar wired.

The audit named this class of work "Backend-ready / frontend-missing" and scored it 10x leverage (audit §3, cross-cutting patterns row 1). Two hours of onboarding friction collapse to near-zero for the automation features once tenants can see events firing and flip toggles. The activation metric is binary: one automation fires in the first 24 hours after signup. That is the north star for this phase.

---

## 2. Goals

**Primary**
- G1: Missed-call text-back fires and writes a `missed_call_texts` row with full state. Dashboard shows last 5 events. Activity feed shows full history.
- G2: Appointment booker exposed via HTTP router and widget chat tool. GCal slot availability drives the picker. Confirmed bookings write to `appointments` table with GCal event ID.
- G3: Dollar attribution counter visible on dashboard top card within 7 days of any automation firing.
- G4: Both automations fire live in a 5-minute sales demo without pre-seeding data.

**Secondary**
- G5: Per-automation enable/disable via `automation_config` JSONB on `widget_configs`. Tenant controls mode (hold/silent_undo/always_ask) without a support ticket.
- G6: Pending-automation queue (`pending_automations` table) backs retry logic for Twilio down and GCal OAuth expiry. No silent loss.
- G7: Activity feed p95 <200ms on first page load.

---

## 3. Non-Goals

The following are explicitly deferred. Do not scope-creep into them.

- Auto-follow-up SMS/email sequences — V2 (after ≥3 testers confirm $ counter moves)
- Document/quote drafter PDF/DOCX export — separate PRD (needs Stripe invoice + tax logic)
- Auto-review-reply — marketing-automation PRD
- Stale-lead reactivation — marketing PRD
- Post-appointment survey — marketing PRD
- Auto-rebook on cancellation — V3+
- Voice autodialer — deferred (TCPA compliance scope)
- Invoice generation — separate PRD
- Phone or walk-in auto-booking — V2 (widget/chat source only in V1)
- Native calendar (no GCal) — not in V1
- Per-tenant Twilio number provisioning — existing env var pattern stands for V1
- Free tier automation — permanently gated; plan check on every trigger

---

## 4. User Stories

**US-1 — Tenant (missed call):**
As a plumber, when I miss a call while on a job, I want an automatic text to fire to the caller so I do not lose the lead. I want to see in my dashboard that it fired, who called, and whether they replied.

**US-2 — Tenant (appointment booking):**
As a power-washing business owner, when a website visitor asks to book a job, I want the chat widget to offer real available times from my Google Calendar and confirm the booking without me touching my phone.

**US-3 — Customer (widget slot picker):**
As a homeowner chatting with an HVAC company's widget, I want to see a list of available appointment times I can click — not free-text a date and wait for a callback.

**US-4 — Tenant (dashboard):**
As a business owner reviewing my week, I want to see at a glance how much revenue my AI employee recovered this month and how many hours it saved — not just a generic activity log.

**US-5 — Developer (integration):**
As the engineer implementing this, I want a single `activity_feed_service.record_event(client_id, type, metadata)` helper that every automation calls so the feed is consistent and the attribution math lives in one place.

---

## 5. Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Activation: automation fires in 24h after signup | ~0% (no visibility) | ≥60% of new Growth+ signups | `missed_call_texts` or `appointments` insert within 24h of tenant created_at |
| Demo: both automations live in 5-min demo | Impossible today | 100% demo success | Manual QA on demo tenant |
| Dollar counter visible in 7 days | No counter exists | ≥80% of testers see non-zero value | `activity_feed_events.dollars_this_month > 0` |
| Activity feed p95 | Unknown | <200ms | Sentry performance monitoring |
| Appointment booking race condition | Unknown | Zero 409s in first 30 days | Sentry error tracking on `/book` |

**Ship → V2 criteria (any 2 of 3):**
- ≥3 paid testers see $ counter move in first 30 days
- ≥10 appointment bookings total across testers without support tickets
- p95 activity feed <200ms, zero Sentry errors in `activity_feed_service`

---

## 6. Architecture

### 6.1 System Data Flow

```
Twilio missed-call webhook
  → twilio_webhooks.py:handle_missed_call (extended in-place)
  → activity_feed_service.record_event(client_id, "missed_call", metadata)
  → INSERT missed_call_texts
  → Twilio send SMS
  → leads upsert (existing logic)
  → pending_automations queue (on Twilio failure)

Widget chat → Claude tool call: propose_appointment_slots
  → appointment_service.get_available_slots(client_id, service, days=7)
    → google_calendar.get_free_busy(tenant_id)
    → filter against appointments table
    → return [{start, end, display}]
  → widget renders slot picker component

Widget slot click → POST /api/v1/widget/appointments/book
  → re-check availability (race-condition guard)
    → 409 + 3 alternates if taken
  → INSERT appointments (status='scheduled', source='chat')
  → appointment_service.create_gcal_event(tenant_id, appointment)
    → gcal_event_id written back to row
    → on OAuth failure: status='pending_sync', tenant notified
  → Twilio SMS confirmation to customer phone
  → iCal attachment via Resend
  → activity_feed_service.record_event(client_id, "appointment_booked", metadata)

Dashboard /activity page
  → GET /api/v1/automations/activity
  → materialized view activity_feed_events (refreshed on insert trigger)
  → totals: dollars_this_month, hours_this_week
  → p95 <200ms (index on client_id, occurred_at desc)
```

### 6.2 Database Schema

#### New Tables

**`missed_call_texts`** (migration 111)
```sql
CREATE TABLE missed_call_texts (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id             uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    call_sid              text NOT NULL,
    caller_phone          text NOT NULL,
    call_received_at      timestamptz NOT NULL,
    sms_sent_at           timestamptz,
    sms_body              text,
    delivery_status       text,                       -- queued|sent|delivered|failed
    twilio_message_sid    text,
    caller_replied_at     timestamptz,
    tenant_responded_at   timestamptz,
    converted_to_lead_id  uuid REFERENCES leads(id),
    converted_at          timestamptz,
    created_at            timestamptz NOT NULL DEFAULT now(),
    updated_at            timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_missed_call_texts_client_received
    ON missed_call_texts(client_id, call_received_at DESC);
```

**`appointments`** (migration 111 — note: existing `appointments` table at migration 092 tracks reminders only; this spec introduces a full booking table. Check schema before applying — if table exists, add missing columns via ALTER.)
```sql
CREATE TABLE IF NOT EXISTS appointments (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id         uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id           uuid REFERENCES leads(id),
    contact_name      text NOT NULL,
    contact_phone     text NOT NULL,
    contact_email     text,
    service_type      text NOT NULL,
    start_ts          timestamptz NOT NULL,
    end_ts            timestamptz NOT NULL,
    duration_minutes  int NOT NULL DEFAULT 60,
    notes             text,
    gcal_event_id     text,
    source            text NOT NULL CHECK (source IN ('chat', 'manual', 'phone')),
    status            text NOT NULL DEFAULT 'scheduled'
                      CHECK (status IN ('scheduled','confirmed','completed','cancelled','no_show','pending_sync')),
    avg_ticket_amount decimal(10,2),
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_appointments_client_start
    ON appointments(client_id, start_ts);
```

**`pending_automations`** (migration 111)
```sql
CREATE TABLE pending_automations (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    automation_type text NOT NULL,   -- missed_call_text|appointment_sync|sms_confirm
    payload_json    jsonb NOT NULL,
    scheduled_for   timestamptz NOT NULL DEFAULT now(),
    status          text NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','processing','done','failed')),
    retry_count     int NOT NULL DEFAULT 0,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_pending_automations_client_status
    ON pending_automations(client_id, status, scheduled_for);
```

#### Per-Automation Config — Reuse `automations` Table

**REVISION 2026-04-22 (plan v2 re-audit):** Original spec proposed adding `widget_configs.automation_config` JSONB. Re-audit found pre-existing `automations` table (migration 001) already provides this: `tenant_id` + `type` (CHECK includes `missed_call_textback`) + `is_enabled` + `config` JSONB + `runs_total`. Use that table instead.

Per-automation config lives in `automations.config` JSONB, one row per `(tenant_id, type)`:
- `missed_call_textback.config = {"mode": "hold", "hold_seconds": 60, "template_id": "default"}`
- `appointment_booker.config = {"mode": "hold", "hold_seconds": 60, "min_lead_hours": 2, "max_days_ahead": 14}`
- `auto_follow_up.config = {"mode": "hold", "hold_seconds": 60}`  *(V2 — not V1)*
- `document_drafter.config = {"mode": "always_ask", "quote_threshold_dollars": 5000}`  *(V2 — not V1)*

Seed one `automations` row per tenant for `missed_call_textback` at tenant creation (add to tenant-provisioning path, OR backfill via migration 111).

`avg_ticket_override` — separate column on `tenants` table (1-line ALTER in migration 111 or 113):
```sql
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS avg_ticket_override decimal(10,2);
```

#### Materialized View (migration 111)
```sql
CREATE MATERIALIZED VIEW activity_feed_events AS
    SELECT
        'missed_call'::text AS event_type,
        client_id,
        call_received_at AS occurred_at,
        caller_phone AS contact_identifier,
        sms_body AS summary,
        NULL::decimal AS dollar_value,
        id AS source_id,
        'missed_call_texts'::text AS source_table
    FROM missed_call_texts
    UNION ALL
    SELECT
        'appointment_booked'::text,
        client_id,
        created_at,
        contact_phone,
        service_type || ' — ' || to_char(start_ts AT TIME ZONE 'UTC', 'Mon DD HH12:MI AM'),
        avg_ticket_amount,
        id,
        'appointments'
    FROM appointments
    WHERE status NOT IN ('cancelled');

CREATE UNIQUE INDEX idx_activity_feed_events_pk
    ON activity_feed_events(event_type, source_id);

CREATE INDEX idx_activity_feed_events_client_occurred
    ON activity_feed_events(client_id, occurred_at DESC);
```

Trigger refreshes the view on insert to either source table:
```sql
CREATE OR REPLACE FUNCTION refresh_activity_feed_events()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY activity_feed_events;
    RETURN NULL;
END;
$$;

CREATE TRIGGER trg_refresh_on_missed_call
    AFTER INSERT ON missed_call_texts
    FOR EACH STATEMENT EXECUTE FUNCTION refresh_activity_feed_events();

CREATE TRIGGER trg_refresh_on_appointment
    AFTER INSERT OR UPDATE ON appointments
    FOR EACH STATEMENT EXECUTE FUNCTION refresh_activity_feed_events();
```

#### New Config Files
- `config/vertical_defaults.yaml` — avg ticket per vertical: `plumbing: 325, hvac: 450, cleaning: 150, power_washing: 400, landscaping: 275, electrical: 350, default: 200`
- `config/hours_saved_formula.yaml` — constants in minutes: `missed_call_text_back: 3, appointment_book: 12, auto_follow_up: 5, auto_quote: 20`

### 6.3 API Surface

#### Automations Activity Feed
```
GET /api/v1/automations/activity
    ?client_id=<uuid>
    &since=<ISO8601>           # optional, default 30 days back
    &type=all|missed_call|appointment
    &limit=<int>               # default 20, max 100

Auth: Bearer JWT (tenant must own client_id)

Response:
{
    "events": [
        {
            "event_type": "missed_call",
            "occurred_at": "2026-04-21T14:32:00Z",
            "contact_identifier": "+1234**7890",   // masked last 4 visible
            "summary": "Missed call — text-back sent",
            "dollar_value": null,
            "source_id": "<uuid>"
        }
    ],
    "totals": {
        "dollars_this_month": 325.00,
        "hours_this_week": 0.6,
        "missed_calls_this_month": 4,
        "appointments_this_month": 1
    }
}
```

#### Widget Appointment Availability (public, api_key gated)
```
GET /api/v1/widget/appointments/available
    ?api_key=<tenant_api_key>
    &service=<service_type>
    &days=7                    # default 7, max 14

Response:
{
    "slots": [
        {"start": "2026-04-22T09:00:00Z", "end": "2026-04-22T10:00:00Z", "display": "Tue Apr 22, 9:00 AM"},
        ...
    ],
    "timezone": "America/New_York"
}
```

#### Widget Appointment Booking (signed JWT, rate-limited)
```
POST /api/v1/widget/appointments/book
    Authorization: Bearer <signed_widget_jwt>   // 5-min expiry, signed by api_key secret
    Content-Type: application/json

Body:
{
    "client_id": "<uuid>",
    "slot_start": "2026-04-22T09:00:00Z",
    "slot_end": "2026-04-22T10:00:00Z",
    "contact_name": "Jane Smith",
    "contact_phone": "+15551234567",
    "contact_email": "jane@example.com",
    "service_type": "power washing - driveway",
    "notes": "Two-car driveway, about 600 sq ft"
}

Response 200:
{
    "appointment_id": "<uuid>",
    "gcal_event_id": "<string>",
    "confirmation_message": "Booked for Tue Apr 22 at 9:00 AM. You'll receive a confirmation text.",
    "status": "scheduled"
}

Response 409 (race condition):
{
    "error": "slot_taken",
    "message": "That time was just booked. Here are 3 alternatives:",
    "alternatives": [
        {"start": "...", "end": "...", "display": "..."},
        ...
    ]
}
```

Rate limit: 5 bookings per hour per widget session.

#### Chat Tool: `propose_appointment_slots`
Invoked from `widget_chat.py` tool dispatch. Calls the availability endpoint with the tenant's api_key and returns formatted slot options for the widget to render as a clickable list.

Input schema:
```json
{
    "service_type": "string",
    "days_ahead": "integer (default 7)"
}
```

Output: formatted text + structured `slots` array passed as widget card data.

### 6.4 UI Layout

#### Dashboard Top Card

```
┌────────────────────────────────────────────────────────────┐
│  AI Employee Activity                                       │
│                                                             │
│  $325 recovered this month   ·   0.6 hrs saved this week   │
│                                                             │
│  ● Missed call from ****7890 — text-back sent   14 min ago │
│  ● Appointment booked: Power washing Tue Apr 22 9AM  2h ago│
│  ● Missed call from ****2341 — text-back sent   Yesterday  │
│                                           [View all →]     │
└────────────────────────────────────────────────────────────┘
```

Dark theme (#0b0e13 background, #00BFFF accents). Phone numbers masked to last 4. Status badges: green dot = sent/booked, yellow = pending, red = failed.

#### /activity Page (new route)

Full-width filterable event stream. Left column: event type filter chips (All / Missed Call / Appointment). Right: event cards with timestamp, masked contact, summary, status badge. Click event card: detail drawer with full (unmasked) contact info behind auth wall, SMS body, GCal event link.

Headline bar at top: same dollar/hours totals as dashboard card.

#### Widget Slot Picker (new widget component)

When `propose_appointment_slots` tool fires, widget renders:

```
┌─────────────────────────────────┐
│ Available times for your area:  │
│                                 │
│ [ Tue Apr 22 — 9:00 AM  ]       │
│ [ Tue Apr 22 — 2:00 PM  ]       │
│ [ Wed Apr 23 — 10:00 AM ]       │
│ [ Thu Apr 24 — 9:00 AM  ]       │
│                                 │
│ Select a time to confirm →      │
└─────────────────────────────────┘
```

Click fires `POST /api/v1/widget/appointments/book`. On success: confirmation card. On 409: toast with 3 alternates.

#### 60-Second Hold UI

For `mode: "hold"` automations, dashboard shows a toast: "{Automation} pending — fires in 60s. [Cancel]". Cancel writes `status='cancelled'` to `pending_automations` before execution. After 60s elapses, automation fires and toast resolves to the event card.

---

## 7. Technical Implementation — File by File

**REVISION 2026-04-22 (plan v2 re-audit):** Re-audit found most files in this section already exist. §7 reframed to "extend existing" wherever applicable. Genuine new files tagged `(NEW)`.

### Files to Extend (existing)

**`backend/services/activity.py`** *(exists — 991B, has `log_activity()` writing to `activity_log` table)*
Add read-side functions:
```python
def get_activity_totals(tenant_id: str, since: datetime) -> dict
def get_activity_events(tenant_id: str, since: datetime, type_filter: str, limit: int) -> list[dict]
```
Reads from `activity_feed_events` materialized view (migration 111). Computes `dollars_this_month` via `attribution_service` (NEW). Computes `hours_this_week` from `config/hours_saved_formula.yaml`.

**`backend/services/booking.py`** *(exists — 22.5K, has `create_appointment`, `generate_available_slots`, `cancel_appointment`, `list_appointments`, `update_appointment`, `get_business_hours`, `upsert_business_hours`, `create_recurring_series`)*
Add GCal integration:
```python
async def create_gcal_event(tenant_id: str, appointment: dict) -> str | None
async def handle_gcal_failure(tenant_id: str, appointment_id: str) -> None
```
`create_gcal_event`: calls existing `google_calendar.py` (confirmed present, 11.4K). On success writes `gcal_event_id` back to `appointments` row.
`handle_gcal_failure`: sets `status='pending_sync'`, enqueues `pending_automations` row, emits tenant dashboard toast.

**`backend/routers/automations.py`** *(exists — 6.7K, has Twilio signature verify + `list_automations` + `toggle` + `update_config`, registered at `main.py:749`)*
Add endpoints:
```python
GET  /api/v1/automations/{tenant_id}/activity   # unified feed with totals, type/since/limit query params
GET  /api/v1/automations/{tenant_id}/pending    # stuck items older than 1h
```
Use existing `_get_current_tenant` auth pattern. Config read/write already live via existing `update_config`.

**`backend/routers/appointments.py`** *(exists — 22.4K, has `POST /` book w/ api_key + 10/min, `GET /slots`, `GET /availability`, iCal feed, service-types CRUD, no-show-stats)*
Extend:
- `book_appointment` (line 176): call `booking.create_gcal_event` after insert success, write `gcal_event_id` back. On GCal fail → `status='pending_sync'` + `pending_automations` enqueue.
- Add signed-JWT alt-auth path (5-min expiry, `jti` tracked, rate 5/hr/session). Keep api_key path for legacy widgets.
- On GiST EXCLUDE 409 at line 198-199: return 3 next-available alternates in response body.

### Files to Create (genuine new)

**`backend/services/attribution_service.py` (NEW)**
Dollar + hours math. Stateless.
```python
def get_avg_ticket(tenant_id: str, vertical: str | None) -> float
def compute_dollars_this_month(tenant_id: str, events: list[dict]) -> float
def compute_hours_this_week(events: list[dict]) -> float
```
Loads `config/vertical_defaults.yaml` on import via `functools.lru_cache`. Checks `tenants.avg_ticket_override` first (ALTER added in mig 111 per §6.2); falls back to vertical default; falls back to `default: 200`.

**`backend/services/retry_worker.py` (NEW — Phase 4)** *(OR add to existing `backend/services/automation_engine.py` if better fit)*
Background task draining `pending_automations` with exponential backoff 30s/2min/10min, max 3 attempts. Emits Sentry breadcrumb on each retry.

**`config/vertical_defaults.yaml`**
```yaml
verticals:
  plumbing: 325
  hvac: 450
  cleaning: 150
  power_washing: 400
  landscaping: 275
  electrical: 350
  default: 200
```

**`config/hours_saved_formula.yaml`**
```yaml
minutes_saved:
  missed_call_text_back: 3
  appointment_book: 12
  auto_follow_up: 5
  auto_quote: 20
```

**`migrations/111_ops_automation_v1.sql`**
All DDL above: `missed_call_texts`, `appointments` (or ALTER if exists), `pending_automations`, `widget_configs` columns, materialized view + triggers, indexes.

**`frontend/src/pages/ActivityPage.jsx`** (new page)
Full activity feed. Dark theme. Filter chips. Event detail drawer. Wires to `GET /api/v1/automations/activity`.

**`frontend/src/utils/api/automations.js`** (new API client module)
```js
export const getActivity = (params) => ...
export const getAutomationConfig = (clientId) => ...
export const updateAutomationConfig = (clientId, config) => ...
export const getPendingAutomations = (clientId) => ...
```

**`backend/tests/test_activity_feed_service.py`**
80% coverage target. Key cases: record_event writes row, totals compute correctly, masking applied, vertical default fallback, avg_ticket_override wins.

**`backend/tests/test_appointment_service.py`**
80% coverage. Key cases: slot availability excludes booked times, race condition returns 409, GCal failure sets pending_sync, backfill on reconnect.

**`backend/tests/test_widget_appointments_router.py`**
100% coverage for auth paths. Key cases: unsigned request rejected, expired JWT rejected, rate limit enforced, 409 returns alternates.

### Files to Modify

**`backend/routers/twilio_webhooks.py`** — extend `handle_missed_call` (line 78):
1. Read `automation_config` from `widget_configs` for the matched tenant. If `missed_call_text_back.enabled == false`, skip.
2. After existing quiet-hours check, add call duration check: if `CallDuration` param >10 or call_status not in (`no-answer`, `busy`, `failed`), skip (existing status check at line 108 covers this partially; add duration guard).
3. Check `leads.caller_phone` match for personalization: `"Hi {first_name}, sorry we missed you. {tenant_name} here."` vs default.
4. On Twilio send success: call `activity_feed_service.record_event(client_id, "missed_call", {...})` + INSERT into `missed_call_texts`.
5. On Twilio send failure: INSERT into `pending_automations` with `automation_type='missed_call_text'` and exponential retry schedule.
6. Existing `log_activity()` call (line 157) stays; add `missed_call_texts` insert before it.
7. Replay window: add check that `call_received_at` is within 5 minutes of now to prevent forged replays.

**`backend/services/appointment_booker.py`** — extend `AppointmentBooker.run()`:
Current code talks to a Managed Agent and returns a UUID stub. After this PRD:
1. Before Managed Agent call: try `appointment_service.get_available_slots()`. If no slots, return `needs_human` immediately (fast path, no API spend).
2. After successful booking: call `appointment_service.create_gcal_event()` and write `gcal_event_id` to the `appointments` row.
3. Call `activity_feed_service.record_event()` on success.
4. The Managed Agent path remains for complex multi-turn flows; the direct GCal path is the primary V1 path from widget chat.

**`backend/routers/widget_chat.py`** — add `propose_appointment_slots` to chat tool dispatch:
1. Register the tool in the tools list passed to Claude (existing pattern: search for `tools=` in widget_chat.py).
2. Handle `tool_use` block with name `propose_appointment_slots`: call `appointment_service.get_available_slots(client_id, service, days)`.
3. Return structured slot data alongside text for widget to render as clickable list.
4. Write characterization tests on existing `widget_chat.py` before touching (per TDD-workflow rule).

**`frontend/src/pages/Dashboard/` components** — add top card:
Extend dashboard to render the automation activity card above or alongside the existing onboarding checklist. Wire to `GET /api/v1/automations/activity?limit=5`. Show last 5 events + dollar/hours headline. "View all" link → `/activity`.

**`frontend/src/App.jsx`** — add route `/activity` → `ActivityPage`.
**`frontend/src/components/Sidebar.jsx`** — add "Activity" link (icon: lightning bolt), visible to Growth+ tenants only.
**`backend/main.py`** — register `automations` router and `widget_appointments` router.

---

## 8. Edge Cases + Failure Modes

| Scenario | Behavior |
|----------|----------|
| Twilio down on missed call | INSERT into `pending_automations` with `automation_type='missed_call_text'`. Retry 3× with exponential backoff (30s, 2min, 10min). Surface stuck items (retry_count ≥ 3, status='pending') in `/automations/pending` after 1 hour. |
| GCal OAuth expired mid-booking | Book locally (INSERT appointments with `status='pending_sync'`). Do NOT block customer confirmation. Queue GCal sync in `pending_automations`. Send tenant dashboard toast: "Calendar sync failed — reconnect Google Calendar to sync." Backfill on OAuth reconnect. |
| Claude timeout on slot proposal | Rule-based fallback: next 5 free 60-minute windows in next 7 days during business hours (09:00–17:00 tenant timezone). No API spend on fallback path. |
| Booking race condition | Re-check slot availability inside a transaction before INSERT. If taken: return 409 with 3 next-available alternates. Widget shows toast with alternatives. |
| Tenant on Free plan | `automation_config` check first. `missed_call_text_back.enabled` defaults to `true` but plan gate in `handle_missed_call` blocks execution. Dashboard shows "Automations paused — upgrade to Growth to activate." |
| Tenant downgrades Growth→Free mid-cycle | Cancel all `pending_automations` rows for that client_id (set `status='failed'`). Pause new triggers (plan gate). Dashboard banner: "Plan changed, automations paused. Upgrade to resume." Existing `missed_call_texts` and `appointments` data preserved. |
| Spam caller | Check against a simple blocklist: `automations.config.spam_blocklist` (array of E.164 numbers) on the `(tenant_id, type='missed_call_textback')` row. If caller in blocklist, skip silently. |
| Caller already has open lead | Existing lead upsert logic at twilio_webhooks.py:174 stays. If lead exists, use `lead.name` for personalization. `converted_to_lead_id` set on `missed_call_texts` row. |
| iCal email fails | Log warning, do not fail the booking. Booking is confirmed regardless. Retry iCal via `pending_automations`. |
| `pending_automations` stuck > 1 hour | `GET /api/v1/automations/pending` returns them. Admin can manually retry or dismiss. V2: cron job retries automatically. |
| Materialized view refresh slow | `REFRESH MATERIALIZED VIEW CONCURRENTLY` — non-blocking. If refresh takes >1s (large dataset), log warning. Dashboard falls back to direct table queries with a 5s timeout. |

---

## 9. Security + Compliance

**Widget GET endpoints (`/available`):** `api_key` query param. Rate limit 60/min per api_key. CORS gated to tenant's `allowed_domains`.

**Widget POST endpoint (`/book`):** signed JWT (5-minute expiry, signed with api_key secret). Rate limit 5 bookings per hour per session (sliding window, keyed by JWT `jti`). Any request with expired or missing JWT returns 401.

**Twilio webhooks:** HMAC-SHA1 verify already exists (`_verify_twilio_signature` at twilio_webhooks.py:32). Add 5-minute replay window check: reject if `call_received_at` > 5 minutes ago (prevents forged/replayed requests).

**PII handling:** Phone numbers masked to last 4 digits in all API responses to the frontend (`+1234****7890` → show as `****7890`). Full number visible only in the detail drawer, gated on the same JWT that authenticated the dashboard session. Never log full phone numbers. `missed_call_texts.caller_phone` is stored full server-side (needed for Twilio sends) but never echoed in list endpoints.

**Plan gate:** Every automation trigger checks `tenant.plan IN ('growth', 'professional', 'autopilot', 'enterprise')` before executing. Free tier: blocked at trigger point, not after SMS send.

**Cost caps:** Soft cap $50/month Anthropic + Twilio spend per tenant. Admin console alert when exceeded. No hard cap V1.

**Tenant isolation:** Every query scoped by `client_id`. `activity_feed_service.get_activity_events` always filters `WHERE client_id = $1`. No cross-tenant data in any response.

**RLS:** `missed_call_texts`, `appointments`, `pending_automations` all need RLS policies: `service_role` bypass + `auth.uid()` owner check via `tenants` join. Add in migration 111.

---

## 10. Testing Strategy

### Backend (80% minimum coverage on new services; 100% on auth paths)

**`backend/tests/test_activity_feed_service.py`**
- `test_record_event_inserts_row` — verifies materialized view row after insert
- `test_totals_dollar_uses_vertical_default` — plumbing tenant, no override, expects $325 × bookings
- `test_totals_dollar_uses_avg_ticket_override` — override set to $500, uses $500
- `test_totals_hours_from_formula` — missed call event → 3 min saved
- `test_phone_masked_in_events_list` — asserts last 4 visible, rest stars
- `test_phone_unmasked_in_detail` — detail endpoint returns full number with auth

**`backend/tests/test_appointment_service.py`**
- `test_get_available_slots_excludes_booked` — mocked GCal free-busy, existing appointment in slot, expect slot absent
- `test_get_available_slots_gcal_expired_fallback` — OAuth error, expect rule-based 5 slots returned
- `test_book_appointment_inserts_row` — valid slot, expect `appointments` row with `status='scheduled'`
- `test_book_appointment_calls_gcal` — expect `create_gcal_event` called with correct params
- `test_book_appointment_gcal_failure_pending_sync` — GCal raises, expect `status='pending_sync'` + `pending_automations` insert
- `test_race_condition_returns_409` — concurrent booking of same slot, expect 409 with alternates
- `test_sms_confirmation_sent` — mock Twilio, verify `send_sms` called on booking success

**`backend/tests/test_widget_appointments_router.py`**
- `test_unsigned_book_request_returns_401`
- `test_expired_jwt_book_returns_401`
- `test_rate_limit_exceeded_returns_429`
- `test_valid_book_returns_200_with_appointment_id`
- `test_taken_slot_returns_409_with_alternates`
- `test_available_endpoint_api_key_required`
- `test_available_endpoint_returns_slots`

**`backend/tests/test_twilio_webhooks_extended.py`** (characterization tests first, then extension tests)
- `test_missed_call_writes_missed_call_texts_row`
- `test_missed_call_personalized_for_known_lead`
- `test_missed_call_automation_disabled_skips`
- `test_missed_call_free_tenant_skips`
- `test_missed_call_twilio_failure_queues_pending`
- `test_replay_window_rejects_old_timestamp`

### E2E (Playwright)
- `chat → slot picker render → slot click → confirmation card → GCal event created`
- `missed call webhook → missed_call_texts row → dashboard top card shows event`

### Pre-edit characterization tests
Before touching `widget_chat.py` for tool addition, write characterization tests covering existing tool dispatch paths. Run and confirm green before any changes.

---

## 11. Rollout Plan

**Feature flag:** Global killswitch via env var `OPS_AUTOMATION_V1_ENABLED=false` for instant revert. Per-tenant enable via `automations.is_enabled` column (migration 001, existing).

**Per-automation disable:** `automations.is_enabled` per `(tenant_id, type)` row. Existing `PATCH /automations/{tenant_id}/toggle` endpoint already wired. Config JSONB via existing `PATCH /automations/{tenant_id}/config`. Settings page UI deferred to Phase 3b — V1 ships with API-only toggle.

**Rollout sequence:**
1. Week 1: Internal test tenant (Aidan's own). Verify both automations fire end-to-end. Fix anything.
2. Week 2-3: 3 paid testers — MTOptions (power-washing, 704 msgs, verified active per memory/project_active_testers.md) + 2 new verticals (target: HVAC, cleaning). Monitor Sentry.
3. Week 4-5: All Growth+ tier tenants. Watch activation metric daily (target ≥60% fire in 24h).
4. Free tier: disabled permanently via plan gate. Banner on dashboard.

**Comms:** No email blast V1. Dashboard banner for new Growth+ signups: "Your AI employee is now active — see what it's doing." Link → `/activity`.

---

## 12. Timeline Estimate

| Week | Work | Owner |
|------|------|-------|
| 1 | Migration 111, `activity_feed_service`, `attribution_service`, `vertical_defaults.yaml`, `hours_saved_formula.yaml`. Tests for both services. | Backend-dev |
| 1-2 | Extend `twilio_webhooks.py:handle_missed_call`. `pending_automations` retry logic. Tests. | Backend-dev |
| 2 | `appointment_service.py`. Extend `appointment_booker.py`. `widget_appointments.py` router. Tests (including 100% auth paths). | Backend-dev |
| 2-3 | `widget_chat.py` tool addition (characterization tests first). `automations.py` router. Register both routers in `main.py`. | Backend-dev |
| 3 | `ActivityPage.jsx`. Dashboard top card. Sidebar link. `automations.js` API client. Widget slot picker component. | Frontend-dev |
| 3-4 | E2E Playwright tests. Internal tenant smoke test. Fix issues. | QA |
| 4 | Roll to 3 paid testers. Monitor. | — |
| 5 | Roll to all Growth+. | — |

**Total V1: 3-5 weeks.** Backend heavy in weeks 1-3. Frontend in parallel from week 3. No blocking dependencies — `activity_feed_service` can ship independently of `appointment_service`.

---

## 13. V2 Scope (deferred — document only, do not detail)

- **Auto-follow-up sequences** — SMS + email triggered by lead qualification score (hot/warm/cold). Trigger: `lead_qualification.py` score write. Sequence config in `automation_config`. Not in V1.
- **Document drafter quotes** — PDF + DOCX output. Triggered by high-confidence service quote from widget chat. No invoices V1. Separate PRD after V1 ships.

---

## 14. Open Questions

None blocking implementation. All decisions locked above.

Monitoring questions to answer after rollout (not blockers):
1. What is the realistic Twilio SMS cost per missed-call event at scale? (Soft cap is $50/tenant/mo — validate this is right before Growth tier launch.)
2. Does `REFRESH MATERIALIZED VIEW CONCURRENTLY` block at the table sizes we expect in week 4? If yes, switch to direct query with caching layer.
3. Should the 60-second hold window be configurable per tenant or fixed? V1 ships fixed at 60s. Re-evaluate after tester feedback.

---

## Constraints Summary

- `client_id` not `tenant_id` on `missed_call_texts`, `appointments`, `pending_automations` (schema-discipline rule — production bug risk)
- `status` not `lead_stage` on all status fields
- No `from __future__ import annotations` in any FastAPI file
- Widget JS byte-identical in `widget/` and `frontend/public/widget/` after any slot picker addition
- Migration numbering: next is 111 (110 is `tenant_api_keys.sql`, verified 2026-04-21)
- Plan names for gate checks: `growth`, `professional`, `autopilot`, `enterprise` — never `foundation` or `operations`
- Activity feed p95 <200ms — enforced by materialized view + composite index, verified by Sentry performance monitoring before Growth+ rollout
