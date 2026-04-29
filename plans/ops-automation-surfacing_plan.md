# Ops Automation Surfacing — Implementation Plan (v2)

**Source spec:** `specs/ops-automation-surfacing_spec.md` (approved 2026-04-21)
**Plan revision:** v2 — re-audited 2026-04-22 after discovering pre-existing infrastructure
**Estimated phases:** 5
**Target ship:** V1 in 2-4 weeks (reduced from spec's 3-5 — plan reuses ~50% of existing code)
**Reversibility:** `OPS_AUTOMATION_V1_ENABLED=false` global killswitch + per-row `automations.is_enabled`

---

## Spec Delta Report (READ FIRST)

Plan v1 assumed greenfield build. Re-audit of codebase found substantial pre-existing infrastructure the spec did not survey. Recommend user update spec before Phase 3 to resolve.

| Spec §6.2 / §7 claim | Actual state | Plan treatment |
|---|---|---|
| Create `missed_call_texts` table | Genuine new | Migration 111 — keep |
| Create `appointments` table (or ALTER if exists) | **Exists** (migration 005): tenant_id, customer_name, customer_email, start/end_time, status, notes, lead_id. GiST EXCLUDE constraint prevents double-booking for `status='confirmed'`. | ALTER to add `gcal_event_id`, `service_type`, `avg_ticket_amount`, expand status CHECK for `'scheduled'`/`'pending_sync'` |
| Create `pending_automations` table | Genuine new | Migration 112 — keep |
| Add `widget_configs.automation_config` JSONB | **Redundant** — existing `automations` table (migration 001) already has `tenant_id`/`type`/`is_enabled`/`config` JSONB/`runs_total`. `type` CHECK already includes `'missed_call_textback'`. | **Use `automations.config` JSONB instead.** Drop spec §6.2's ALTER `widget_configs` proposal. |
| Create `backend/services/activity_feed_service.py` | Partially exists — `backend/services/activity.py::log_activity()` writes to `activity_log` table (migration 004). Not a full feed service. | Extend `activity.py` with `get_activity_events` + `get_activity_totals`. No new file. |
| Create `backend/services/appointment_service.py` | **Exists** — `backend/services/booking.py` has `create_appointment`, `generate_available_slots`, `cancel_appointment`, `list_appointments`, `update_appointment`, `get_business_hours`, `upsert_business_hours`, `create_recurring_series`. | Extend `booking.py` with `create_gcal_event`, `handle_gcal_failure`. |
| Create `backend/routers/automations.py` | **Exists** (6.7K) — has Twilio signature verify + `list_automations` + `toggle` + `update_config`. Uses `tenant_id`. Register at `main.py:749` already done. | Add `GET /automations/{tenant_id}/activity` endpoint to existing router. No new router file. |
| Create `backend/routers/widget_appointments.py` | **Exists as `backend/routers/appointments.py`** (22.4K) — has `POST /` (book, api_key, 10/min), `GET /slots` (availability, api_key, 60/min), `GET /availability` (business hours), iCal feed, service-types CRUD, no-show-stats. | Extend `appointments.py` with GCal + signed-JWT option. No new router file. |
| Create `backend/services/attribution_service.py` | Genuine new | Keep |
| Signed JWT on booking | `appointments.py:176` uses `api_key` in body + rate limiter `@limiter.limit("10/minute")`. Not JWT. | Add signed-JWT alt-auth path; keep api_key for legacy widgets. |
| Widget slot picker | Genuine new | Keep (byte-identical widget JS sync required) |
| `propose_appointment_slots` Claude tool | Genuine new | Keep |

**Spec update needed:** §6.2 must drop `widget_configs.automation_config` ALTER, reference existing `automations` table instead. §7 must reframe most "new files" as "extend existing." Flag for user approval before Phase 3 starts.

---

## Tracer-bullet principle (unchanged)

Smallest user-visible win = **missed-call text-back fires, writes `missed_call_texts` + `activity_log` row, dashboard surfaces it**. No widget changes. No GCal. Backend code fires at `backend/routers/twilio_webhooks.py:80` today but doesn't persist.

---

## Phase 1 — Tracer Bullet: Missed-Call Event Surfacing (REVISED) — **DONE 2026-04-22**

**Status:** SHIPPED. Verified 2026-04-29 audit:
- Migration `111_missed_call_texts.sql` applied
- `backend/routers/twilio_webhooks.py::handle_missed_call` wired (replay window, automation lookup, masked insert, runs_total increment)
- `backend/routers/automations.py:134` `GET /{tenant_id}/activity` live
- `backend/services/activity.py` `_mask_phone`, `log_activity`, `get_activity_events`, `get_activity_totals`
- `frontend/src/pages/Dashboard/AutomationActivityCard.jsx` + `ActivityFeed.jsx` mounted in `Dashboard/index.jsx:414,462`
- `frontend/src/utils/api/automations.js::getActivity()` matches API shape
- Tests green: `pytest test_twilio_webhooks.py test_activity.py` → 26 passed

Browser smoke + simulated webhook POST not yet run — defer to Phase 2 verification. Next phase = Phase 2.

**Goal:** Twilio missed-call webhook writes `missed_call_texts` row + `activity_log` event + dashboard card shows last 5 events. No totals, no `/activity` page, no widget.

**DB (migration 111):** `missed_call_texts` only + RLS + `idx_missed_call_texts_tenant_received` (use `tenant_id` column — consistency with `appointments` + `activity_log`; `client_id` would break schema-discipline pattern for this subtree).

**Backend:**
- Extend `backend/services/activity.py` — add `get_activity_events(tenant_id, since, type_filter, limit)` + `get_activity_totals(tenant_id, since)` functions. Reads from `activity_log`. No new service file.
- New: `backend/tests/test_activity.py` — extend for new functions (PII masking, type filter)
- Modify: `backend/routers/twilio_webhooks.py:handle_missed_call` (line 80)
  - Read `automations` row for tenant + type=`'missed_call_textback'`. Skip if `is_enabled=false` or not found.
  - 5-min replay window check on `CallStatus` timestamp
  - On Twilio send success: INSERT `missed_call_texts` + call `log_activity(tenant_id, 'missed_call_textback', desc, metadata={sms_sid, call_sid, ...})` + UPDATE `automations.runs_total += 1`
  - On Twilio fail: stash to `pending_automations` (deferred to migration 112 → Phase 4) OR log warning only for Phase 1
- Modify: `backend/tests/test_twilio_webhooks.py` — characterization tests FIRST per TDD rule, then extension: writes row / personalized for known lead / disabled skips / Free-tenant skips / replay-window rejects

**API:**
- Add to existing `backend/routers/automations.py`: `GET /api/v1/automations/{tenant_id}/activity?limit=5`. Auth: `_get_current_tenant` (matches existing router pattern). Returns events only, no totals (Phase 2 adds totals).

**Frontend:**
- Extend `frontend/src/pages/Dashboard/` — top card, last 5 events, masked phone (last 4), dark theme
- New: `frontend/src/utils/api/automations.js` — `getActivity({tenantId, limit})` only

**Gate:**
1. Simulated Twilio webhook POST (test form) → row in `missed_call_texts` + row in `activity_log` within 1s
2. `GET /api/v1/automations/{tenant_id}/activity?limit=5` returns event with masked phone `+1234****7890`
3. Dashboard top card renders event
4. `pytest backend/tests/test_activity.py backend/tests/test_twilio_webhooks.py` green
5. `automations.runs_total` increments from 0 to 1
6. Verified: `pytest + curl /activity + preview screenshot — PASS`

**Rollback:** revert migration 111. `automations` row flip `is_enabled=false` for instant tenant-level disable.

**Files touched (6):** migrations/111_missed_call_texts.sql, activity.py (extend), test_activity.py (extend), automations.py (add 1 endpoint), twilio_webhooks.py (extend handle_missed_call), test_twilio_webhooks.py (extend), Dashboard card (extend), automations.js (new — 1 fn)

---

## Phase 2 — Dollar/Hours Attribution + Activity Page (REVISED)

**Goal:** Dashboard top card shows `$X recovered this month · Y hrs saved this week`. `/activity` full-page feed with filter chips.

**Backend:**
- New: `config/vertical_defaults.yaml` + `config/hours_saved_formula.yaml`
- New: `backend/services/attribution_service.py` — `get_avg_ticket`, `compute_dollars_this_month`, `compute_hours_this_week`. YAML loaded via `functools.lru_cache`. Checks `tenants.avg_ticket_override` (add column if not present — 1-line ALTER in mig 111 addendum OR separate mig 113). Falls back to vertical default → `default: 200`.
- New: `backend/tests/test_attribution_service.py` — write FIRST per TDD
- Extend: `backend/services/activity.py::get_activity_totals` to call attribution_service

**API:**
- Extend: `GET /api/v1/automations/{tenant_id}/activity` → add `totals` object + `type`/`since`/`limit` query params per spec §6.3

**Frontend:**
- New: `frontend/src/pages/ActivityPage.jsx` — full-width stream, filter chips (All / Missed Call / Appointment), event detail drawer (unmasked phone behind JWT wall)
- Modify: `frontend/src/App.jsx` — add `/activity` route
- Modify: `frontend/src/components/Sidebar.jsx` — Activity link, Growth+ only (check `plan` claim)
- Extend: Dashboard top card — totals headline + "View all →"

**Gate:**
1. Tenant w/ 1 missed call → `$X` non-zero (e.g. plumbing default $325)
2. `/activity` renders, filter "Missed Call" narrows
3. Detail drawer shows full unmasked phone behind auth
4. Sidebar link hidden for Free tier
5. Verified: `pytest test_attribution + npm run build + manual /activity render`

**Files (~9):** 2 YAMLs, attribution_service.py + test, ActivityPage.jsx, App.jsx edit, Sidebar.jsx edit, Dashboard extend, activity.py extend + test extend, API client extend

---

## Phase 3 — Appointment Booker GCal Integration (REVISED)

**Goal:** Widget chat proposes slots from GCal → click → `appointments` row w/ `gcal_event_id` → dashboard shows event. Reuses existing booking infrastructure.

**DB (migration 112):**
- ALTER `appointments`: ADD `gcal_event_id TEXT`, `service_type TEXT`, `avg_ticket_amount DECIMAL(10,2)`, `source TEXT CHECK (source IN ('chat','manual','phone'))` DEFAULT 'manual'
- ALTER `appointments` status CHECK: add `'scheduled'`, `'pending_sync'` to existing set
- CREATE `pending_automations` (genuine new) + RLS + index
- RLS policies for new columns (should inherit but verify)

**Backend:**
- Extend: `backend/services/booking.py` — add `create_gcal_event(tenant_id, appointment) -> str | None`, `handle_gcal_failure(tenant_id, appointment_id) -> None`. Reuse existing `google_calendar.py` service if present; else add.
- Extend: `backend/routers/appointments.py::book_appointment` (line 176) — after `create_appointment` success, call `create_gcal_event`, write `gcal_event_id` back. On GCal failure: set `status='pending_sync'`, enqueue in `pending_automations`, tenant toast.
- Add: signed-JWT alt-auth on `book_appointment` (5-min expiry, `jti` tracked). Keep api_key path for legacy widgets.
- Modify: `backend/routers/widget_chat.py` — add `propose_appointment_slots` tool. **Characterization tests FIRST** (per TDD + Rule 10: never change tests to match intent).
- Extend tests: `backend/tests/test_booking.py` — GCal success/failure paths; `backend/tests/test_widget_appointments.py` — if doesn't exist, create

**Widget (byte-identical sync required):**
- Modify `widget/agentnexlify-widget.js` — slot picker component (renders after `propose_appointment_slots` tool fires), click → existing `POST /api/v1/appointments/{tenant_id}` with api_key
- Modify `frontend/public/widget/agentnexlify-widget.js` — **identical** copy. Verify via `diff` in gate.

**Frontend:**
- Extend: `ActivityPage.jsx` — render `appointment_booked` event type
- Extend: Dashboard card — render appointment events

**Gate:**
1. Widget chat → `propose_appointment_slots` → picker renders 4+ slots from real GCal free-busy
2. Slot click → `appointments` row with `gcal_event_id` populated + `activity_log` event
3. Dashboard shows "Appointment booked: <service> <date>"
4. `diff widget/agentnexlify-widget.js frontend/public/widget/agentnexlify-widget.js` empty
5. Playwright E2E: `chat → picker → click → confirmation → GCal event` green
6. Existing GiST EXCLUDE catches concurrent booking → 409 (already in place, verify test)
7. Verified: `pytest + playwright + widget diff + curl /appointments/book`

**Rollback:** migration 112 revert (additive — safe). Git revert widget JS on both paths.

**Files (~10):** migrations/112, booking.py extend + test, appointments.py extend + test, widget_chat.py extend + char tests, widget JS ×2 paths, ActivityPage extend, Dashboard extend

---

## Phase 4 — Edge Cases + Hardening (REVISED)

**Goal:** All 10 spec §8 failure modes covered. PII masking enforced. Plan gate blocks Free tier.

**Backend:**
- `pending_automations` retry worker — exponential 30s/2min/10min, 3 attempts. New bg task in `backend/services/automation_engine.py` (existing) OR new `backend/services/retry_worker.py`
- `appointments.py::book_appointment` — on GiST exclusion 409, **add 3 next-available alternates** to response (spec §6.3). Small extension of existing exception handler at line 198-199.
- `twilio_webhooks.py::handle_missed_call` — plan gate (`tenants.plan IN growth+`), spam blocklist check against `automations.config.spam_blocklist`
- `booking.py::handle_gcal_failure` — status='pending_sync', enqueue retry, dashboard toast
- PII masking helper in `activity.py` — enforce `+1234****7890` on all list responses; unmasked only in detail drawer behind JWT
- `GET /api/v1/automations/{tenant_id}/pending` — stuck items (retry_count≥3, age>1hr)
- 60-second hold UI — dashboard cancel writes `pending_automations.status='cancelled'`

**Tests (from spec §10):**
- `test_race_condition_returns_409_with_alternates` — concurrent booking
- `test_gcal_expired_fallback_pending_sync`
- `test_missed_call_twilio_failure_queues_pending`
- `test_replay_window_rejects_old_timestamp`
- `test_missed_call_free_tenant_skips`
- `test_phone_masked_in_events_list` / `test_phone_unmasked_in_detail`

**Security (spec §9):**
- Twilio HMAC-SHA1 already verified at `twilio_webhooks.py:32` — add 5-min replay window check
- Signed JWT 5-min expiry added Phase 3 — verify rate limit 5/hr/session (sliding window, jti key)
- Cost cap $50/mo Anthropic+Twilio soft cap, admin console alert

**Gate:**
1. All 10 spec §8 rows covered by passing tests
2. Concurrent booking test → 1 row inserted, other gets 409 + 3 alternates
3. Free tenant webhook → no SMS, no rows, dashboard upgrade banner
4. GCal expired mid-book → customer confirmation still sent, tenant sees "reconnect" toast
5. **`/ultrareview`** clean on full diff (auth + payments + tenant isolation per `rules/ultrareview.md`)
6. Verified: `pytest backend/tests/ -v + /ultrareview report PASS`

**Files (~6):** retry worker, appointments.py 409 extend, twilio_webhooks plan gate, booking.py GCal failure, 60s hold UI, PII masking helper

---

## Phase 5 — Metrics + GA Rollout + Flag Removal (UNCHANGED)

**Goal:** Flag off by default, measurable activation metric, 3 paid testers green, ship to all Growth+.

**Backend:**
- Sentry perf monitor `activity.get_activity_events` — alert p95 >200ms
- Activation metric SQL: `missed_call_texts` OR `appointments` insert within 24h of `tenants.created_at`
- Admin dashboard: Anthropic+Twilio spend per tenant
- Remove `OPS_AUTOMATION_V1_ENABLED` flag after 7 days zero-incident

**Frontend:**
- Dashboard banner for new Growth+ signups: "Your AI employee is now active" → `/activity`
- Free tier banner: "Automations paused — upgrade to Growth to activate"

**Rollout (spec §11):**
- Week 1: Internal tenant (Aidan) end-to-end verify
- Week 2-3: MTOptions (power-washing, 704 msgs, confirmed active per `memory/project_active_testers.md`) + 2 new verticals (HVAC, cleaning)
- Week 4: all Growth+, watch activation ≥60% daily

**Gate (V1 → V2 — any 2 of 3):**
1. ≥3 paid testers see `$` counter move in 30d
2. ≥10 appointment bookings total, zero support tickets
3. p95 activity feed <200ms, zero Sentry errors

**Files (~4):** Sentry config, activation metric SQL, dashboard banners, flag removal

---

## Cross-Phase Concerns (REVISED)

| Concern | Enforcement |
|---|---|
| `tenant_id` not `client_id` on ALL new columns | `appointments` + `automations` + `activity_log` all use `tenant_id` — schema-discipline.md confirms. Do NOT introduce `client_id` here. (`leads` + `conversations` keep `client_id` — different subtree.) |
| Reuse `automations.config` JSONB | Per-automation enable/config — existing pattern. Do NOT add `widget_configs.automation_config`. |
| Reuse `activity_log` as feed source | `log_activity()` fires on every automation — Dashboard reads from there. |
| Reuse `booking.create_appointment` | EXCLUDE constraint prevents double-booking. Do NOT add SELECT FOR UPDATE. |
| Widget JS byte-identical (Phase 3+) | `widget-test` skill diff check every PR |
| No `from __future__ import annotations` in FastAPI | pre-commit hook |
| Migration numbering | 111 (Phase 1 — `missed_call_texts`), 112 (Phase 3 — `appointments` ALTER + `pending_automations`) |
| Plan names | `growth`/`professional`/`autopilot`/`enterprise` — never `foundation`/`operations` |
| RLS | Every new table; verify inherits on ALTER |
| `/ultrareview` | Phase 3 + Phase 4 diffs (auth + payments + tenant isolation) |
| Self-verification | Every phase-gate completion: `Verified: <cmd> — PASS` |

---

## Phase Dependencies

```
Phase 1 (missed-call surfacing) → independent, uses only existing activity_log
    ↓
Phase 2 (attribution + /activity page) → depends on Phase 1
    ↓
Phase 3 (GCal booking) → independent of Phase 2, requires mig 112 + widget sync
    ↓
Phase 4 (edge cases) → depends on Phase 3
    ↓
Phase 5 (GA) → all prior
```

---

## Next Step

**Before execution:** user confirms spec delta report above. Two decisions needed:
1. Spec §6.2 — drop `widget_configs.automation_config` ALTER in favor of existing `automations.config`? (Recommended: yes)
2. Spec §7 — reframe "new files" as "extend existing"? (Recommended: yes)

**After confirmation:** execute Phase 1. Recommended:

```
# Option A — direct Sonnet executor with plan
Agent(subagent_type=sonnet-executor, prompt=<Phase 1 scope + cross-phase constraints + this plan file>)

# Option B — compound-engineering for Phase 1
/compound specs/ops-automation-surfacing_spec.md --phase=1

# Option C — manual Opus-advisor brief → Sonnet executor
see .claude/rules/advisor-consult.md
```

---

## Open Items (non-blocking)

1. `automations` table row for `missed_call_textback` must exist per tenant — verify seeder logic (may need mig 111 to INSERT default row per tenant)
2. GCal OAuth flow state — does `google_calendar.py` exist? Need to verify before Phase 3 start
3. Spec §14 monitor questions (Twilio cost, materialized view REFRESH latency, 60s hold configurability)

Plan v2 locked pending spec-delta confirmation.
