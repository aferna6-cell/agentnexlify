# Existing Infrastructure Reference — 2026-04-21

Produced from migration survey (113 files). Load-bearing input for PRD respawns. Corrects grill-me Q9-Q16 decisions that invented tables already present.

## Methodology
Read migrations 005, 011, 014, 017, 019, 020, 021, 022, 024, 040, 044, 066, 070, 073, 087, 092, 102 in full. Grep'd remaining 113 for ops/marketing/review/sequence/opt-in keywords. Cross-referenced against both PRD drafts written 2026-04-21.

---

## Rule: EXTEND, do not RECREATE

Both draft PRDs invented tables already present. Every proposed table below maps to existing infrastructure. **PRDs must ALTER existing, not CREATE new, unless explicitly novel.**

---

## Section 1 — Ops-automation existing infra

### Missed-call-text-back (ALREADY WIRED)
**Migration 040 `textback_settings.sql`:**
- `tenants.textback_enabled BOOLEAN default false`
- `tenants.textback_message TEXT` — tenant's custom SMS template
- `tenants.textback_quiet_start TEXT` — e.g. "22:00"
- `tenants.textback_quiet_end TEXT` — e.g. "07:00"

**PRD impact:** grill-me Q15 decision ("JSONB `automation_config` on widget_configs for all automations") needs correction — missed-call config lives on `tenants`, not `widget_configs`. Keep the JSONB column for NEW automations but don't duplicate textback settings.

### Calls (canonical voice event log)
**Migration 044 `calls.sql`:**
```
calls (
  id uuid, tenant_id uuid (NOT client_id), lead_id uuid FK,
  caller_phone text, called_number text, direction text,
  duration_seconds int, status text CHECK in (
    'ringing','in-progress','completed','no-answer','busy','failed'
  ),
  recording_url, transcript jsonb, summary text,
  sentiment text CHECK in ('positive','neutral','negative'),
  action_taken text, twilio_call_sid text, created_at
)
```
Index: `(tenant_id, created_at DESC)`.

**PRD impact:** My Q9 decision proposed `missed_call_texts` standalone. Corrected: `missed_call_texts` should FK to `calls.id`, NOT duplicate caller_phone/timestamps. One call → potentially many SMS attempts (retry scenarios).

Corrected schema:
```
missed_call_texts (
  id uuid, tenant_id uuid,
  call_id uuid FK REFERENCES calls(id),
  sms_sent_at tz, sms_body text, delivery_status text,
  twilio_message_sid text,
  caller_replied_at tz, tenant_responded_at tz,
  converted_to_lead_id uuid FK, converted_at tz,
  created_at, updated_at
)
```

### Appointments (existing with EXCLUDE constraint)
**Migrations 005 + 017 + 024 + 066 + 092.** Full schema:
```
appointments (
  id uuid, tenant_id uuid (NOT client_id — documented exception),
  lead_id uuid FK,
  customer_name text (NOT contact_name),
  customer_email text,
  customer_phone text,
  start_time tz (NOT start_ts),
  end_time tz (NOT end_ts),
  status text CHECK in ('confirmed','cancelled','completed','no_show') — NO 'scheduled',
  notes text,
  recurrence_rule text, recurrence_parent_id uuid, recurrence_end_date date,
  updated_at tz,
  reminder_24h_sent_at tz, reminder_1h_sent_at tz,
  review_request_sent_at tz,   -- from migration 020
  -- EXCLUDE USING gist prevents double-booking where status='confirmed'
)
```

**PRD impact:**
- Q10 decision ("new appointments table") CORRECTED: ALTER existing. Add `gcal_event_id`, `source`, `avg_ticket_amount`, `service_type_id FK` to `service_types`.
- Q22 decision ("409 + 3 alternates for race condition") SIMPLIFIED: EXCLUDE constraint already rejects double-booking at DB level. Catch unique violation → return 409 + alternates. No manual re-check needed.
- Column naming: `start_time/end_time` (not `_ts`), `customer_*` (not `contact_*`).
- Tenant column: `tenant_id` (not `client_id`) — schema-discipline documented exception.

### Business hours + service types + waitlist
**Migration 005:** `business_hours` table with JSONB hours config per tenant, `slot_duration_minutes`, `buffer_minutes`, `max_advance_days`.

**Migration 066:** `waitlist_entries` — when slots booked, visitors join. Auto-notify on cancellation.

**Migration ? (066 ref):** `service_types` table exists.

**PRD impact:** Appointment booker availability query = `business_hours` + `appointments` + respect `waitlist_entries`. Free feature: "all slots booked, join waitlist" already supported.

### Automation framework (MASSIVE existing infra)
Three parallel automation systems already exist:

**1. `automation_sequences` (005 — older):**
- `automation_sequences`, `automation_steps`, `automation_executions`, `automation_logs`
- Trigger events: `new_lead`, `lead_stage_change`, `no_response_24h`

**2. `email_sequences` (073 — newer, dedicated):**
- `email_sequences` (trigger_type: `lead_captured`, `tag_added`, `manual`)
- `email_sequence_steps` (supports `email_type: 'email' | 'sms'`)
- `email_sequence_enrollments` (tracks lead progress)
- `email_sequence_sends` (individual send records, `scheduled_for`, `status: pending|sent|failed|skipped`)

**3. `automation_rules` (087 — event-driven):**
- Trigger types: `lead_captured`, `tag_added`, `tag_removed`, `form_submitted`, `appointment_created`, `appointment_completed`, `pipeline_stage_changed`, `lead_score_threshold`, `email_opened`, `email_clicked`, `scheduled_daily`, `scheduled_weekly`, `website_visit`, `smart_list_matched`
- `automation_rule_executions` = execution log with `status`, `actions_run JSONB`, `execution_time_ms`, `error_message`

**4. `pipeline_automations` (070):** stage-based trigger → action JSONB.

**PRD impact:** GRILL-ME DECISION CORRECTION — my proposed `activity_feed_service` + materialized `activity_feed_events` view is REINVENTION. Correct approach:
- Activity feed = SQL UNION across `calls` + `appointments` + `missed_call_texts` + `automation_rule_executions` + `email_sequence_sends` + `reviews` + future self-maintenance events
- Each event type projects into unified response shape at query time
- No new table needed; index boost on existing tables if perf fails

**Auto-follow-up sequences (V2) already 90% built:** `email_sequences` table with SMS support. V2 work = wire lead qualification score to enrollment trigger, plus UI to manage. Not building sequences from scratch.

### Compliance (existing)
**Migration 021 `lead_unsubscribe.sql`:**
- `leads.unsubscribed BOOLEAN`
- `leads.unsubscribed_at TIMESTAMPTZ`
- Index for filtering

**Migration 069 `lead_email_bounced.sql`:** bounce tracking on leads.

**PRD impact:** Marketing PRD proposed `marketing_opt_ins` table with UNIQUE(email, phone). CORRECTED: use existing `leads.unsubscribed` for opt-out. TCPA opt-in for SMS marketing is the delta — add `leads.sms_marketing_opted_in BOOLEAN`, `leads.sms_opted_in_at TIMESTAMPTZ`, `leads.sms_opt_in_source TEXT` via ALTER. Don't invent a separate opt-in table.

---

## Section 2 — Marketing-automation existing infra

### Reviews (CORE TABLE EXISTS)
**Migration 019 `reviews.sql`:**
```
reviews (
  id uuid, tenant_id uuid,
  platform text default 'google' ('google','yelp','facebook'),
  author_name text, rating int (1-5), review_text text, review_date tz,
  ai_draft_response text,      -- AI-generated reply draft
  owner_response text,         -- Tenant-approved final
  responded boolean default false,
  external_review_id text,     -- platform dedup
  created_at, updated_at
)
```

**PRD impact:** Marketing PRD proposed NEW `review_replies` table. CORRECTED: existing `reviews` table has both `ai_draft_response` and `owner_response` columns. Approval flow = tenant edits `ai_draft_response` → promotes to `owner_response` → sets `responded=true`. NO new table.

### Review request config (EXISTS)
**Migration 020 `review_request_config.sql`:**
- `tenants.review_request_config JSONB default '{"enabled": false, "delay_hours": 24, "method": "email"}'`
- `appointments.review_request_sent_at TIMESTAMPTZ`

**Migration 011:** `tenants.google_review_link TEXT` — shortlink to Google review page.

**PRD impact:** Marketing PRD proposed NEW `review_requests` table to track sends per appointment. CORRECTED: existing `appointments.review_request_sent_at` is the dedup signal. Per-request detail (channel, delivery status) = ALTER appointments or minimal new table `review_request_sends` linked to appointment_id. Much smaller scope than proposed.

### Email infrastructure (EXISTS)
- Migration 014: `email_templates` (tenant-scoped, categorizable, shareable)
- Migration 022: `email_events` (opens/clicks via tracking pixel + redirect, `execution_id` for sequences, `campaign_tag` for blasts)
- Migration 069: email bounce tracking on leads
- Existing service: `backend/services/email_sender.py` per audit

### Marketing plan gating (EXISTS)
**Migration 102 `marketing_addon.sql`:**
- `tenants.marketing_addon_active BOOLEAN`
- `tenants.marketing_addon_stripe_sub_id TEXT`
- `tenants.marketing_addon_started_at TIMESTAMPTZ`
- `tenants.marketing_addon_grandfathered BOOLEAN`
- $49.99/mo add-on separate from primary plan
- Grandfather pass applied one-time for existing paid tenants

**PRD impact:** Marketing PRD's plan-tier gating (Growth+/Professional+) is WRONG model. Real model = `marketing_addon_active=true` check. Plan tiers handle ops-auto features. Marketing features gate on add-on subscription. Must reflect in PRD: feature checks `tenants.marketing_addon_active`, not plan name.

### Social + SEO (EXISTS)
- Migration 050: `social_media_marketing`
- Migration 045: `local_seo`
- Migration 055: `campaign_sending_started_at`
- Migration 088: `campaign_analytics_aggregates`

**PRD impact:** Auto-post job photos (V2) and local SEO automation may already have scaffolding. Haven't read fully — flag for PRD to reference.

---

## Section 3 — What's GENUINELY NEW (what PRDs should propose)

### Ops-automation v1 NEW work
1. `missed_call_texts` — one row per SMS response, FK to `calls`
2. ALTER `appointments` ADD COLUMN `gcal_event_id`, `source`, `avg_ticket_amount`, `service_type_id FK`
3. `widget_configs.automation_config JSONB` — NEW automations' config (NOT textback — that's on tenants). Covers appt_booker settings, auto-follow-up, doc_drafter.
4. `widget_configs.avg_ticket_override DECIMAL` — per-tenant dollar attribution override
5. `config/vertical_defaults.yaml` + `config/hours_saved_formula.yaml` — new config files
6. `backend/services/activity_feed_service.py` — query-time UNION across existing tables
7. `backend/services/appointment_service.py` — wraps existing appointments table ops + GCal sync
8. `backend/services/attribution_service.py` — dollar/hour counter from existing data
9. Widget chat tool `propose_appointment_slots` — new Claude tool
10. `/api/v1/automations/activity`, `/api/v1/widget/appointments/available|book` — new endpoints
11. Missed-call → SMS send handler extension in `twilio_webhooks.py` (existing file)
12. ALTER `leads` ADD COLUMN `sms_marketing_opted_in`, `sms_opted_in_at`, `sms_opt_in_source` — for V2 follow-up TCPA

### Marketing-automation v1 NEW work
1. Use existing `reviews` table — no new review_replies
2. Use existing `tenants.review_request_config` + `appointments.review_request_sent_at`
3. Optional minimal `review_request_sends` table ONLY if per-send channel/delivery tracking needed beyond the boolean sent_at
4. Use `leads.unsubscribed` + new `sms_marketing_opted_in` columns (shared with ops-auto)
5. Gate all marketing features on `tenants.marketing_addon_active=true`, NOT plan tier
6. Backend services: `backend/services/review_request_scheduler.py` (extends existing automation_engine ref from migration 024 comment), `backend/services/review_reply_drafter.py`
7. Google Business Profile OAuth integration — may need new `tenant_integrations` table (see onboarding PRD scope) or extend existing integration storage
8. `/api/v1/marketing/reviews/pending-reply` — query `reviews WHERE responded=false AND ai_draft_response IS NOT NULL`
9. Bad-experience detection service (sentiment on chat + appointment.status='no_show') — new logic, uses existing data

### Onboarding-v2 NEW work
(Out of scope for this turn — will produce when 3b PRD fires)

### Self-maintenance NEW work
(Out of scope — will produce when 3c PRD fires)

---

## Section 4 — Corrected grill-me decisions

Grill-me Qs that need revision:

| Q | Original decision | Corrected |
|---|---|---|
| Q9 | NEW `missed_call_texts` standalone | FK to existing `calls` |
| Q10 | NEW `appointments` table | ALTER existing |
| Q13 | Single `/activity` endpoint returning events from NEW tables | Same endpoint, query UNION across existing calls+appointments+automation_rule_executions+email_sequence_sends+reviews |
| Q15 | JSONB `automation_config` on widget_configs for ALL automations | Same JSONB BUT missed-call config already on `tenants.textback_*` — don't duplicate |
| Q22 | Re-check availability on click, return 409 | Catch EXCLUDE constraint violation at DB level, return 409 |
| Marketing Q: opt-in table | NEW `marketing_opt_ins` with UNIQUE | Use existing `leads.unsubscribed` + ALTER ADD `sms_marketing_opted_in` |
| Marketing Q: review_replies | NEW table | Use existing `reviews.ai_draft_response/owner_response/responded` |
| Marketing Q: review_requests tracking | NEW table | Existing `appointments.review_request_sent_at` + optional minimal sends table |
| Marketing Q: plan gating | Plan tier check | `tenants.marketing_addon_active=true` |

---

## Section 5 — Implications for the 4 PRDs

### ops-automation-surfacing_spec.md (693 lines, SCHEMA-CONFLICTED)
**Action:** respawn with this reference as input. Agent should ALTER existing tables + reuse existing automation framework, not invent parallel infra.

### marketing-automation_spec.md (925 lines, SCHEMA-CONFLICTED)
**Action:** respawn with this reference as input. Major simplification — `reviews` table already has approval flow columns, plan gating already on `tenants.marketing_addon_active`, opt-out already on `leads.unsubscribed`.

### onboarding-v2_spec.md (pending)
**Action:** 3b not yet fired. Include this reference in its prompt to prevent similar errors.

### self-maintenance_spec.md (pending)
**Action:** 3c not yet fired. Include this reference. Specifically check existing `automation_rules` trigger `scheduled_daily` + `scheduled_weekly` — cron scheduling already a primitive.

---

## Lesson for future audits

Phase 1's 4 Explore agents traced USER FLOWS (signup, KB setup, agent config, integrations). Missed pre-existing SCHEMA and SERVICE layer. Future audits should include:
- Migration history survey (`ls migrations/ | head -200`)
- Table inventory via `\dt` or equivalent
- Service layer inventory (`ls backend/services/`)
- Config file inventory (`ls config/`)

If Phase 1 had included this, grill-me Q9-Q16 would not have invented tables that already exist.

---

## Pointers
- Source migrations read: 005, 007, 011, 014, 017, 019, 020, 021, 022, 024, 040, 044, 066, 070, 073, 087, 092, 102, 108, 109
- PRDs requiring respawn: `specs/ops-automation-surfacing_spec.md`, `specs/marketing-automation_spec.md`
- PRDs not yet written: `specs/onboarding-v2_spec.md`, `specs/self-maintenance_spec.md`
- Rule violated: `rules/fill-instructions-before-guessing.md`
- Related: `rules/schema-discipline.md`, `audits/audit-onboarding-2026-04-21.md`

---

## Appendix — additional finds (2026-04-21, post initial doc)

### Migration 007 — `integrations` table + `appointments.google_event_id`
```sql
integrations (
  id uuid, tenant_id uuid, provider text (no CHECK),
  access_token, refresh_token, token_expiry tz, metadata jsonb,
  created_at, UNIQUE(tenant_id, provider)
)
```
- General-purpose OAuth provider storage. Extensible to ANY provider.
- `appointments.google_event_id` TEXT column ALREADY EXISTS. Ops-auto PRD proposed adding `gcal_event_id` — use existing `google_event_id` instead.

**PRD impact:**
- Ops-auto: use `appointments.google_event_id` (not a new `gcal_event_id`). Patch after revision agent lands.
- Onboarding-v2: use `integrations` table for Stripe/Twilio/Resend API key storage. Store API key as `access_token`, leave `refresh_token` null. Do NOT create new `tenant_secrets` table.

### Migration 108 — photo-quote infrastructure
```sql
tenant_pricing_rules (client_id, industry CHECK in plumbing/roofing/hvac/auto_body/landscaping/pest, rules_jsonb, disclaimer_text, min_confidence_threshold)
quote_requests (client_id, conversation_id, image_url, thumbnail_url, quote_low, quote_high, severity, confidence, claude_summary, needs_human)
tenant_quote_usage (client_id, period_start, quote_count, overage_count)
```
- **Uses `client_id`, not `tenant_id`** — different from appointments. Schema-discipline mixed pattern continues.
- Powers photo-quote widget (image → Claude estimate). Exists separately from document_drafter scope.

**PRD impact:**
- Ops-auto V2 document_drafter: INTEGRATE with `quote_requests` when quote source is image-based. Document drafter's role = format existing `quote_requests` data into PDF/DOCX. Don't duplicate quote generation.
- Consider: pricing rules in `tenant_pricing_rules.rules_jsonb` should feed document_drafter templates too.

### Migration 109 — `tenant_integrations` is Drive-only
```sql
tenant_integrations (
  client_id, provider CHECK in ('drive','dropbox','onedrive','box'),
  oauth_token_enc bytea, oauth_refresh_token_enc bytea, oauth_expires_at,
  enabled, last_synced_at, last_sync_status
)
integration_sync_log — file sync metadata
kb_section_hashes — KB content dedup
```
- **Scope: storage providers for KB sync.** NOT general OAuth.
- Uses `client_id`, not `tenant_id`. Uses `oauth_token_enc` (bytea, encrypted via pgcrypto).

**PRD impact:**
- Onboarding-v2: `tenant_integrations` (109) is Drive-only. Do NOT extend CHECK constraint to include Stripe/Twilio/Resend/Google Calendar — wrong schema (needs `last_synced_at`, `files_*` concepts don't apply).
- Use **migration 007's `integrations` table** for Stripe/Twilio/Resend keys. Two-table pattern: `integrations` (OAuth + API keys, generic) + `tenant_integrations` (Drive-specific with sync-log concepts).

### Migration numbering coordination (2026-04-21)
Next available: **111**. Current PRD claims:
- Marketing PRD revised: uses **111-113** (committed)
- Ops-auto PRD (revision in flight): will propose **114** 
- Onboarding-v2 PRD (pending): **115-117**
- Self-maintenance PRD (pending): **118-119**

Coordinate when all 4 PRDs ship to prevent collision.

### Lesson addendum
Reading 17 migrations caught 9 invented tables. Reading the remaining 96 migrations WILL surface more. Flow-centric audits are one of three required passes:
1. **Flow audit** — user-facing friction (done 2026-04-21 AM)
2. **Schema audit** — existing tables + columns (done 2026-04-21 PM, this doc)
3. **Service audit** — existing backend/services/ + routers/ capabilities (PENDING — may surface more pre-built infrastructure)

Before any future PRD writes, run all three.
