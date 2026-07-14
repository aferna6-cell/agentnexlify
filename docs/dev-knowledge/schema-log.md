# Schema Change Log — AgentNexLiFy

Every database schema change. Claude Code checks this when working with database queries.

---

## 167_widget_proactive.sql (2026-07-14)

**What:** `proactive jsonb` (nullable) added to `widget_configs`.

**Why:** Behavior-triggered widget auto-open (time-on-page / scroll-depth / exit-intent). Config passed through to the embedded widget by `GET /api/v1/widget/config`. Shape: `{"enabled":bool,"delay_seconds":int,"exit_intent":bool,"message":text|null,"once_per_session":bool}`. NULL default = feature off, fully backward compatible.

**Applied:** 2026-07-14 via `mcp__supabase__apply_migration` (prod `pxserpybmajixqrmzaly`).

---

## 166_review_responses.sql (2026-07-14)

**What:** New `review_responses` table — approval-gated AI review replies.

**Why:** Reviews AI (GoHighLevel AI Employee parity). Drafts an AI reply to a customer review and holds it for human approval before posting. `draft -> approved -> posted/rejected` state machine + `approved_by`/`approved_at`. Separate from the `reviews` table's inline `ai_draft_response` (no lifecycle). `review_id` is an FK-less pointer to `reviews.id`; `external_ref` holds a platform review id when unknown. Index `review_responses_tenant_status_idx` on `(tenant_id, status)`.

**Applied:** 2026-07-14 via `mcp__supabase__apply_migration` (prod `pxserpybmajixqrmzaly`).

---

## 165_appointment_reminders.sql (2026-07-14)

**What:** New `appointment_reminders` table + `tenants.appointment_reminders_enabled boolean NOT NULL DEFAULT true`.

**Why:** Automated SMS reminders (24h + 2h) before booked appointments to cut no-shows. Scheduled at booking time; sent by a polling job (`POST /api/v1/appointments/reminders/run`). `UNIQUE (appointment_id, reminder_type)` makes scheduling idempotent. `pending -> sending -> sent|failed|skipped` claim dance lets the 4 Uvicorn workers avoid double-sending. Uses `tenant_id` (appointments differ from leads/conversations). Index `idx_appointment_reminders_due` on `(scheduled_for, status)`. Per-tenant opt-out toggle defaults enabled.

**Note:** The `/run` endpoint is manual (not cron-wired) to avoid double-sending with the legacy `backend/services/automation/scheduled/appointment_jobs.py::send_appointment_reminders()` path. Wire one or the other, not both.

**Applied:** 2026-07-14 via `mcp__supabase__apply_migration` (prod `pxserpybmajixqrmzaly`).

---

## 153_stripe_trial_end.sql (2026-06-16)

**What:** `stripe_trial_end timestamptz` added to `tenants` table (nullable, no default).

**Why:** Stores the Stripe subscription `trial_end` Unix timestamp as ISO 8601. Enables the trial countdown banner to show exact days remaining and charge date instead of generic copy.

**Column:** `tenants.stripe_trial_end` — timestamptz, nullable. Set by `_handle_subscription_updated` webhook handler when `trial_end` is present; cleared to NULL when trial converts.

**Applied:** Pending — apply via `mcp__supabase__apply_migration` or Supabase SQL editor.

---

## 152_pay_gate_exempt.sql (2026-06-15)

**What:** `pay_gate_exempt boolean NOT NULL DEFAULT false` added to `tenants` table.

**Why:** "Can't sign up without paying" feature. New tenants default to `false` (gated). All
tenants that existed before this migration are grandfathered via `UPDATE tenants SET
pay_gate_exempt = true` so no existing customer is blocked.

**Column:** `tenants.pay_gate_exempt` — boolean, not null, default false.

**Applied:** Pending — apply via `mcp__supabase__apply_migration` or Supabase SQL editor.

---

## 150_usage_packs.sql (2026-06-15)

**What:** New table `tenant_usage_packs` for one-time AI usage top-ups purchased via Stripe.

Columns:
- `id` uuid PK, `tenant_id` uuid FK → tenants, `tokens` bigint (>0), `period` text (YYYY-MM-DD first-of-month format), `stripe_session_id` text UNIQUE (idempotency key), `created_at` timestamptz.

Index on `(tenant_id, period)`.

RLS enabled, no public policies (service-key access only).

**How it works:** `backend/services/ai_usage_guard.py::_sum_usage_packs` reads this table and adds the pack total to the plan-derived hard limit in Python before passing to the `reserve_ai_token_budget` RPC. No migration changes to the RPC — the limit is Python-computed.

**Applied:** Pending — apply via `mcp__supabase__apply_migration` or Supabase SQL editor.

---

## widget_health service (2026-06-13) — NO NEW MIGRATION

Ported from PR #212 / GH #215. `backend/services/widget_health.py` probes existing tables:
- `widget_configs.tenant_id` + `widget_configs.allowed_domains` — existed since migration 001
- `integrations.tenant_id` + `integrations.provider` — migration 109
- `activity_log.tenant_id` — migration 004
- `leads.client_id` (NOT tenant_id) + `conversations.client_id` (NOT tenant_id) — invariant
- `appointments.tenant_id`

New endpoint `PUT /api/v1/widget/config/{tenant_id}/allowed-domains` writes back to `widget_configs.allowed_domains` (TEXT[] column, migration 001).

Applied: N/A — no migration needed.

---

## 131_os_engine_telemetry.sql (2026-06-06)

**What:** Two `client_id`-scoped tables for the Agent OS engine's run record (the parts `os_agent_runs` doesn't capture):
- `os_routing_decision` — one row per routing decision (classifier, decision, chosen_agent, confidence, alternates JSONB, accepted/changed_to). Powers `/admin/routing`.
- `os_model_call_log` — one row per model call (purpose, model, input/output tokens, cost_usd, ok, error). Powers `/admin/costs`. Offline/failed calls logged at cost 0.

Both: `run_id` nullable UUID (no FK; references `os_agent_runs.id` when a run fired), RLS deny-public, index on `(client_id, created_at DESC)`.

**Backend wiring:** `backend/services/agent_os_bridge.py::_persist_telemetry` (best-effort, never breaks the turn) writes both from the orchestration RunRecordBundle. `tenant_scope._TENANT_COLUMN_OVERRIDES` maps both to `client_id`. Mappers `map_routing_decision_row` + `map_model_call_row` unit-tested in `backend/tests/test_agent_os_bridge.py`.

**Applied:** NO — pending deploy. Apply via `mcp__supabase__apply_migration` when the Agent OS engine path goes live.

## Migration History

### 001 — Initial Schema
Creates core tables: `tenants`, `widget_configs`, `leads`, `conversations`, `faq_entries`, `automations`. Enables RLS on all tables. Creates `update_updated_at()` trigger and `reset_monthly_conversations()` function. Tenants have plan (free/growth/professional/enterprise), Stripe fields, referral system. Leads have `tenant_id` FK, lead_score, lead_stage, source. Widget configs have api_key (UUID), branding options, allowed_domains.

### 002 — Add Tenant Auth
Adds `password_hash` (TEXT) and `owner_name` (TEXT) to tenants. Expands business_type CHECK to include salon, auto_shop, medical. Changes widget_configs.api_key from UUID to TEXT (for "anx_" prefix keys).

### 003 — Support Messages
Creates `support_messages` table (id, name, email, message, created_at). RLS enabled with service_role access.

### 004 — CRM Tables
Creates `activity_log` (tenant_id, lead_id, activity_type, description, metadata JSONB) and `client_notes` (tenant_id, lead_id, content). Composite indexes for fast lookups.

### 005 — Appointments
Creates `business_hours` (tenant_id unique, timezone, hours JSONB, slot_duration_minutes, buffer_minutes) and `appointments` (tenant_id, lead_id, customer details, start/end time, status, google_event_id). EXCLUDE constraint prevents double-booking. Adds `booking_enabled` to widget_configs.

### 005 — Automation Sequences (duplicate number)
Creates `automation_sequences`, `automation_steps`, `automation_executions`, `automation_logs`. Multi-step email series with trigger events, step ordering, execution tracking, and audit logging.

### 006 — Chat Messages
Creates `chat_messages` (tenant_id, session_id, role user/assistant, content, created_at). This is the canonical message store — conversations table schema is noted as unreliable.

### 007 — Google Calendar Integration (duplicate number)
Creates `integrations` table (tenant_id, provider, access_token, refresh_token, token_expiry, metadata JSONB). Unique on (tenant_id, provider). Adds google_event_id to appointments.

### 007 — Team Members (duplicate number)
Creates `team_members` (tenant_id, email, name, role owner/admin/member/viewer, password_hash, invite_token, invite_accepted, last_login). Unique on (tenant_id, email).

### 007 — Webhooks (duplicate number)
Creates `webhooks` (tenant_id, name, url, events TEXT[], secret, is_active, failure_count) and `webhook_logs` (webhook_id, event, payload JSONB, response_status, success).

### 008 — Branding
Adds `branding` (JSONB DEFAULT '{}') to widget_configs for white-label support.

### 009 — Business Page
Adds business page fields to tenants: business_slug (UNIQUE), business_description, business_phone, business_address, business_city, business_state, business_hours_display, business_logo_url, business_cover_url, business_page_enabled (BOOLEAN), business_services (TEXT[]).

### 010 — Business Page Tiers
Adds tier customization to tenants: bp_color_theme, bp_font_family, bp_hide_powered_by (BOOLEAN), bp_custom_css, bp_meta_title, bp_meta_description.

### 011 — Google Review Link
Adds `google_review_link` (TEXT) to tenants for review request automation.

### 012 — Free Trial
Adds `free_trial_started_at` (TIMESTAMPTZ) to tenants. Backfills existing free plan users with created_at.

### 013 — Fix Plan Names & Unlimited Conversations
Data migration: renames plans 'foundation'→'growth', 'operations'→'professional'. Clears monthly_conversation_limit (all plans now unlimited). Updates CHECK constraint to only allow: free, growth, professional, enterprise.

### 014 — Email Templates
Adds `email_templates` table for reusable email template library. Columns: id (UUID PK), tenant_id (FK→tenants), name (TEXT), category (TEXT DEFAULT 'custom'), subject_template (TEXT), body_template (TEXT), is_shared (BOOLEAN), created_at, updated_at. Index on tenant_id. RLS enabled.

### 015 — Widget Offline Mode
Adds `is_online` (BOOLEAN NOT NULL DEFAULT TRUE) and `offline_message` (TEXT DEFAULT 'We are currently offline...') to `widget_configs`. Allows businesses to toggle between live chat and offline contact form mode. Both columns use `IF NOT EXISTS` for safety.

### 016 — Lead Tags
Adds `tags` (TEXT[] DEFAULT '{}') to `leads` table. GIN index on tags for efficient array queries. Tags are auto-extracted from conversations by Claude during lead capture (e.g., "interested in: kitchen remodel", "budget: high", "timeline: urgent").

### 017 — Recurring Appointments
Adds `recurrence_rule` (TEXT, nullable — 'weekly'/'biweekly'/'monthly'), `recurrence_parent_id` (UUID FK→appointments.id ON DELETE CASCADE), and `recurrence_end_date` (DATE, nullable) to `appointments`. Index on recurrence_parent_id for querying series instances. Parent appointment holds rule + end_date; child instances link back via recurrence_parent_id.

### 018 — Conversation Tags
Adds `tags` (TEXT[] DEFAULT '{}') to `conversations` table. GIN index on tags. Allows business owners to label conversations (e.g., "sales", "support", "complaint"). Tags managed via PUT endpoint, displayed in ConversationsPage sidebar with filter dropdown.

### 019 — Reviews Table (Reputation Manager)
Creates `reviews` table: id (UUID PK), tenant_id (FK→tenants), platform (TEXT, default 'google'), author_name (TEXT), rating (INT, CHECK 1-5), review_text (TEXT), review_date (TIMESTAMPTZ), ai_draft_response (TEXT), owner_response (TEXT), responded (BOOLEAN, default false), external_review_id (TEXT for dedup), created_at, updated_at. Indexes on tenant_id, (tenant_id, platform), (tenant_id, rating). RLS enabled.

### 020 — Review Request Config
Adds `review_request_config` (JSONB, default `{"enabled": false, "delay_hours": 24, "method": "email"}`) to `tenants`. Adds `review_request_sent_at` (TIMESTAMPTZ) to `appointments` for tracking which completed appointments have had review requests sent.

### 021 — Lead Unsubscribe (CAN-SPAM compliance)
Adds `unsubscribed` (BOOLEAN DEFAULT FALSE) and `unsubscribed_at` (TIMESTAMPTZ) to leads table. Partial index on `unsubscribed = TRUE` for efficient filtering in automation queries. Automation engine skips unsubscribed leads. Every outgoing email includes a signed unsubscribe link.

### 022 — Email Events (open/click tracking)
Creates `email_events` table for tracking email opens and clicks. Columns: tenant_id, lead_id (nullable), event_type ('open'/'click'), execution_id (nullable, for sequences), campaign_tag (nullable, for campaigns), details (JSONB). Indexed on tenant_id, execution_id, and (event_type, created_at). RLS enabled.

### 023 — Content Items (Content Studio)
Creates `content_items` table for storing source content that gets repurposed into platform-specific posts. Columns: tenant_id (FK→tenants), title (TEXT), source_type (TEXT: 'text'/'description'/'file'), source_content (TEXT), platform_versions (JSONB, keyed by platform), status (TEXT: 'draft'/'generated'/'scheduled'/'published'), tags (TEXT[]), created_at, updated_at. Indexed on tenant_id and (tenant_id, status). RLS enabled.

### 024 — Appointments updated_at
Adds `updated_at` (TIMESTAMPTZ DEFAULT NOW()) to `appointments`. Used by `automation_engine.send_pending_review_requests()` to determine when an appointment was marked completed and whether enough delay has passed to send a review request. Created during schema drift remediation — this column was referenced in code but had no migration file.

**All migrations 014-024 applied to live Supabase on 2026-03-12.**

### 025 — Content scheduling date
Adds `scheduled_for` (DATE) to `content_items` and an index on `(tenant_id, scheduled_for)` for non-null rows. This powers the Content Studio calendar view and scheduled-post filtering.

### 026 — Lead assignment
Adds nullable `assigned_to` (UUID FK → `team_members.id`, `ON DELETE SET NULL`) to `leads`, plus an index on `(client_id, assigned_to)` for assigned rows. This supports team lead ownership without breaking unassigned leads.

### 027 — AI feedback
Creates `ai_feedback` for per-message thumbs up/down ratings and optional corrections. Columns: `tenant_id`, `session_id`, `message_index`, `rating`, `correction`, `created_at`. Indexed by tenant/date and tenant/session. Used to inject owner corrections back into the widget system prompt.

### 028 — Website crawl cache
Adds `tenants.website_url` and creates `website_content` for cached crawl results (`pages_json`, `extracted_text`, `crawl_status`, `error_message`, `pages_found`, `crawled_at`). This supports Cloudflare-powered website scanning and prompt enrichment without re-crawling on every chat request.

**Applied:** Migrations 025-032 applied on 2026-03-15 via Supabase MCP.

## Known Schema Gotchas

| Issue | Detail |
|-------|--------|
| leads.client_id | Correct FK column name for leads table. Code has historically confused this with tenant_id. |
| leads.status | Correct column name for lead status. Code has historically used lead_stage. |
| tenants.password_hash | Added in migration 002. Exists in schema. |
| tenants.owner_name | Added in migration 002. Exists in schema. |
| chat_messages | Canonical message store (migration 006). The older conversations table is unreliable. |
| Duplicate migration numbers | 005 (appointments, automation_sequences) and 007 (google_calendar, team_members, webhooks) have duplicate numbers. |
| Plan names | Only free, growth, professional, enterprise are valid (migration 013). |
| conversations_used_this_month | Cleared by migration 013 — all plans now unlimited. |

## Schema Drift (Discovered 2026-03-11 Pre-Demo Audit)

The following changes exist in the live Supabase database but have NO corresponding migration file:

### leads table — major drift from migration 001
| Change | Migration Says | Live DB Has |
|--------|---------------|-------------|
| FK column renamed | `tenant_id` | `client_id` |
| Status column renamed | `lead_stage` | `status` |
| New column | — | `lead_type TEXT` |
| New column | — | `lead_temperature TEXT` (CHECK: hot/warm/cold) |
| New column | — | `areas_of_interest TEXT` |
| New column | — | `must_haves TEXT` |
| New column | — | `pre_approved BOOLEAN` |
| New column | — | `conversation_summary TEXT` |
| New column | — | `next_steps TEXT` |
| New column | — | `appointment_date TIMESTAMPTZ` |
| New column | — | `updated_at TIMESTAMPTZ` |

### tenants table — 2 untracked columns
| Change | Migration Says | Live DB Has |
|--------|---------------|-------------|
| New column | — | `notification_phone TEXT` |
| New column | — | `sms_notifications_enabled BOOLEAN DEFAULT false` |

### automation_logs table — no tenant_id
The `automation_logs` table has NO `tenant_id` column. Code that queries `automation_logs.tenant_id` directly will fail. Must join through `automation_executions` instead.

**Action needed:** A reconciliation migration (014+) should document these changes. The code is correct for the live DB; only the migration files are stale.

## Live Schema Audit — 2026-03-11

Verified live Supabase schema against CLAUDE.md and code. Key findings:

### tenants.business_type — default/CHECK mismatch
- Default: `'general'::text`
- CHECK constraint: `business_type = ANY (ARRAY['plumbing', 'dental', 'realestate', 'legal', 'fitness', 'restaurant', 'salon', 'auto_shop', 'medical', 'other'])`
- `'general'` is NOT in the CHECK constraint list. Should be `'other'`.
- **Risk:** Low — signup form always sets a value from the dropdown. Would fail only if someone bypasses the form.
- **Fix:** Change default to `'other'` in a future migration.

### tenants.monthly_conversation_limit — still has default 50
- Migration 013 was supposed to clear limits, but the column default is still `50`.
- Code doesn't enforce the limit (removed in the billing fix commit), so this is harmless.
- **Risk:** Low — only affects initial row creation, and the code ignores this column.

### clients table — legacy table
- `clients` table exists with 2 rows. Has `agent_name`, `service_area`, `bot_name`, `widget_api_key`, etc.
- This appears to be the original V1 schema before `tenants` was introduced.
- ~~`conversations` table still has FK to `clients.id` (legacy).~~ **Fixed in migration 076** — FK now points to `tenants.id`.
- `leads` table FK `client_id` references `tenants.id` (NOT `clients.id`) per the code.
- **Risk:** The `clients` table should be deprecated/removed in a future cleanup.

### All other tables — confirmed matching
Tables verified against CLAUDE.md schema table: tenants, widget_configs, leads, chat_messages, conversations, appointments, business_hours, automation_sequences, automation_steps, automation_executions, automations, faq_entries, activity_log, client_notes, integrations, team_members, webhooks, webhook_logs, automation_logs.

## Schema Drift Remediation — 2026-03-12

**Problem:** Migrations 014-023 existed as SQL files but were never applied to the live Supabase database. The code referenced columns and tables that didn't exist, causing:
- Dashboard crash: `column widget_configs.is_online does not exist`
- Automation engine crash: `column appointments.updated_at does not exist`

**Fix:** Applied all 10 missing migrations to the live database via Supabase SQL editor. Created migration 024 for `appointments.updated_at` (referenced in code but not in any migration file).

**Tables/columns added:**
- `widget_configs`: `is_online`, `offline_message`
- `leads`: `tags`, `unsubscribed`, `unsubscribed_at`
- `appointments`: `recurrence_rule`, `recurrence_parent_id`, `recurrence_end_date`, `review_request_sent_at`, `updated_at`
- `conversations`: `tags`
- `tenants`: `review_request_config`
- New tables: `email_templates`, `reviews`, `email_events`, `content_items`
- `content_items`: `scheduled_for` (DATE, added in migration 025)
- `leads`: `assigned_to` (UUID FK→team_members, ON DELETE SET NULL, added in migration 026)
- New table: `ai_feedback` (id, tenant_id, session_id, message_index, rating, correction, created_at) — migration 027
- `tenants`: `website_url` (TEXT, added in migration 028)
- New table: `website_content` (id, tenant_id, url, pages_json JSONB, extracted_text TEXT, crawl_status TEXT, error_message TEXT, pages_found INT, crawled_at TIMESTAMPTZ) — migration 028
- New table: `menu_items` (id UUID, tenant_id UUID FK, name TEXT, description TEXT, price NUMERIC(10,2), category TEXT, modifiers_json JSONB, available BOOLEAN, image_url TEXT, sort_order INT, created_at TIMESTAMPTZ) — migration 029. Index on (tenant_id, category).

### 029 — Menu Items (Restaurant)
Creates `menu_items` table for restaurant menu management. Columns: tenant_id (FK→tenants), name (TEXT), description (TEXT), price (NUMERIC(10,2)), category (TEXT), modifiers_json (JSONB), available (BOOLEAN DEFAULT true), image_url (TEXT), sort_order (INT DEFAULT 0), created_at (TIMESTAMPTZ). Indexed on (tenant_id, category). RLS enabled.

### 030 — Orders (Restaurant)
Creates `orders` table for restaurant order management. Columns: tenant_id (FK→tenants, ON DELETE CASCADE), lead_id (FK→leads, ON DELETE SET NULL, nullable), session_id (TEXT), customer_name/phone/email (TEXT), items_json (JSONB NOT NULL), subtotal/tax/total (NUMERIC(10,2)), order_type (TEXT: 'pickup'/'delivery'), delivery_address (TEXT), status (TEXT DEFAULT 'new': new/confirmed/preparing/ready/delivered/cancelled), notes (TEXT), created_at (TIMESTAMPTZ). Indexed on (tenant_id, status) and (tenant_id, created_at DESC). RLS enabled.

**Applied:** 2026-03-15 via Supabase MCP.

### 031 — Job Board (Jobs + Applications)
Creates `jobs` table (tenant_id FK→tenants, title TEXT, description TEXT, pay_range TEXT, schedule TEXT, location TEXT, skills TEXT[], is_active BOOLEAN DEFAULT true, created_at, updated_at). Creates `job_applications` table (job_id FK→jobs, tenant_id FK→tenants, applicant_name TEXT, applicant_phone TEXT, message TEXT, status TEXT DEFAULT 'new': new/contacted/interviewed/hired/rejected, notes TEXT, created_at). Indexed on jobs(tenant_id, is_active), job_applications(job_id, status), job_applications(tenant_id, created_at DESC). RLS enabled on both tables.

**Applied:** 2026-03-15 via Supabase MCP.

### 032 — Tenant Tag Definitions (AI Conversation Categorization)
Creates `tenant_tag_definitions` table for customizable AI auto-categorization tags. Columns: tenant_id (FK→tenants, ON DELETE CASCADE), tag_name (TEXT), tag_color (TEXT DEFAULT '#6b7280'), is_system (BOOLEAN DEFAULT false), is_enabled (BOOLEAN DEFAULT true), created_at (TIMESTAMPTZ). Unique constraint on (tenant_id, tag_name). Indexed on tenant_id. RLS enabled. Seeds 6 system tags (New Lead, Pricing Question, Complaint, Appointment Request, Urgent, Follow-up Needed) for all existing tenants via CROSS JOIN. New tenants get seeded on first API access via the backend.

**Applied:** 2026-03-15 via Supabase MCP.

### 033 — Action Items (AI-Extracted Tasks)
Creates `action_items` table for AI-extracted actionable items from conversations. Columns: tenant_id (FK→tenants, ON DELETE CASCADE), conversation_id (FK→conversations, ON DELETE SET NULL, nullable), lead_id (FK→leads, ON DELETE SET NULL, nullable), description (TEXT NOT NULL), due_date (DATE, nullable), priority (TEXT CHECK: low/medium/high, DEFAULT 'medium'), status (TEXT CHECK: pending/done/dismissed, DEFAULT 'pending'), assigned_to (FK→team_members, ON DELETE SET NULL, nullable), created_at (TIMESTAMPTZ). Indexed on (tenant_id, status), (tenant_id, due_date) for non-null, and conversation_id for non-null. RLS enabled.

**Applied:** 2026-03-15 via Supabase MCP.

### 034 — Shared Inbox (Conversation Assignment + Internal Notes)
Adds `assigned_to` (UUID FK→team_members, ON DELETE SET NULL) to `conversations` table for team member ownership. Creates `conversation_notes` table for internal team notes on conversations (never visible to customers). Columns: conversation_id (FK→conversations, ON DELETE CASCADE), tenant_id (FK→tenants, ON DELETE CASCADE), author_id (FK→team_members, ON DELETE CASCADE), content (TEXT NOT NULL), created_at (TIMESTAMPTZ). Indexed on conversation_id and tenant_id. RLS enabled.

**Applied:** 2026-03-15 via Supabase MCP. Note: index uses `client_id` (not `tenant_id`) since conversations table uses that FK name.

### 035 — Team Presence Tracking
Adds `last_active_conversation_id` (UUID FK→conversations, ON DELETE SET NULL) and `last_active_at` (TIMESTAMPTZ) to `team_members` table. Used for showing which team member is currently viewing/handling a conversation in the shared inbox.

**Applied:** 2026-03-15 via Supabase MCP.

### 036 — Snippets / Quick Replies
Creates `snippets` table for pre-written response templates. Columns: tenant_id (FK→tenants, ON DELETE CASCADE), title (TEXT NOT NULL), content (TEXT NOT NULL), shortcut (TEXT, optional), category (TEXT DEFAULT 'General'), usage_count (INTEGER DEFAULT 0), created_at (TIMESTAMPTZ). Indexed on tenant_id, (tenant_id, category), and unique on (tenant_id, shortcut) where not null. RLS enabled.

**Applied:** 2026-03-15 via Supabase MCP.

### 037 — Response Metrics (Analytics Dashboard Upgrade)
Creates `response_metrics` table for tracking conversation response times and outcomes. Columns: tenant_id (FK→tenants, ON DELETE CASCADE), conversation_id (FK→conversations, ON DELETE SET NULL), session_id (TEXT), first_message_at (TIMESTAMPTZ), first_response_at (TIMESTAMPTZ), response_time_seconds (INTEGER), channel (TEXT DEFAULT 'widget'), resolved_at (TIMESTAMPTZ), outcome (TEXT CHECK), created_at (TIMESTAMPTZ). Indexed on tenant_id and (tenant_id, created_at DESC). RLS enabled.

**Applied:** 2026-03-15 via Supabase MCP.

### 038 — Chat Flows (Visual Flow Builder)
Creates `chat_flows` table for customizable chat conversation flows. Columns: tenant_id (FK→tenants, ON DELETE CASCADE), name (TEXT NOT NULL), description (TEXT), flow_json (JSONB NOT NULL, stores nodes and edges), is_active (BOOLEAN DEFAULT false), is_template (BOOLEAN DEFAULT false), created_at, updated_at (TIMESTAMPTZ). Indexed on tenant_id and active flows. RLS enabled. Only one flow can be active per tenant (enforced in backend).

**Applied:** 2026-03-15 via Supabase MCP.

### 039 — Leads Compound Index
Adds compound index `idx_leads_client_created ON leads(client_id, created_at DESC)` for faster lead list queries and analytics date-range filters.

**Applied:** 2026-03-15 via Supabase MCP.

### 040 — Missed Call Text-Back Settings
Adds 4 columns to `tenants`: `textback_enabled` (BOOLEAN DEFAULT false), `textback_message` (TEXT), `textback_quiet_start` (TEXT, e.g. "22:00"), `textback_quiet_end` (TEXT, e.g. "07:00"). Configures per-tenant auto text-back behavior for missed calls.

**Applied:** 2026-03-15 via Supabase MCP.

### 041 — MCP API Keys
Adds `mcp_api_key` (TEXT, unique index) and `mcp_enabled` (BOOLEAN DEFAULT false) to `tenants`. Dedicated API keys for MCP server authentication, separate from widget API keys.

**Applied:** 2026-03-15 via Supabase MCP.

### 042 — Contractor Bid Manager (Bids + Templates)
Creates `bid_templates` (tenant_id, name, description, default_items JSONB) and `bids` (tenant_id, lead_id, title, description, items_json JSONB, subtotal/tax/total NUMERIC, terms, timeline, warranty, status CHECK draft/sent/viewed/accepted/rejected/expired, pdf_url, sent_at, viewed_at). Indexed on (tenant_id, status) and (tenant_id, created_at DESC). RLS enabled.

**Applied:** 2026-03-15 via Supabase MCP.

### 043 — Client Portal (Service Records + Portal Tokens)
Creates `service_records` (tenant_id, lead_id, title, description, service_date, photos_json/documents_json JSONB, notes, invoice_amount) and `portal_tokens` (tenant_id, lead_id, token UNIQUE). Indexed on tenant_id, lead_id, and token. RLS enabled.

**Applied:** 2026-03-15 via Supabase MCP.

### 044 — AI Answering Service (Calls)
Creates `calls` (tenant_id, lead_id, caller_phone, called_number, direction inbound/outbound, duration_seconds, status, recording_url, transcript JSONB, summary, sentiment positive/neutral/negative, action_taken, twilio_call_sid). Indexed on (tenant_id, created_at DESC), (tenant_id, status), and twilio_call_sid. RLS enabled.

**Applied:** 2026-03-15 via Supabase MCP.

### 045 — Local SEO Profile Scores
Creates `seo_profiles` table for GBP profile completeness and local keyword recommendations. Columns: tenant_id (FK→tenants, ON DELETE CASCADE, UNIQUE), completeness_score (INTEGER DEFAULT 0), missing_fields (JSONB), recommendations (JSONB), keyword_suggestions (JSONB), last_analyzed_at (TIMESTAMPTZ), created_at, updated_at. Indexed on tenant_id. RLS with service_role.

**Applied:** Verified applied 2026-03-19 (originally added in Cycle 69-72).

### 046 — Business Autopilot Settings
Adds 3 columns to `tenants`: `autopilot_enabled` (BOOLEAN DEFAULT false), `onboarding_completed_at` (TIMESTAMPTZ), `last_monthly_report_at` (TIMESTAMPTZ). Supports autopilot onboarding progress and monthly report tracking.

**Applied:** Verified applied 2026-03-19 (originally added in Cycle 69-72).

### 047 — CSAT/NPS Satisfaction Surveys
Creates `csat_responses` table for post-conversation satisfaction tracking. Columns: tenant_id (FK→tenants, ON DELETE CASCADE), conversation_id (FK→conversations, ON DELETE SET NULL), lead_id (FK→leads, ON DELETE SET NULL), session_id (TEXT), rating (INTEGER CHECK 1-5), feedback (TEXT), channel (TEXT DEFAULT 'email'), created_at (TIMESTAMPTZ). Indexed on (tenant_id, created_at DESC). RLS with service_role.

**Applied:** Verified applied 2026-03-19 (originally added in Cycle 86).

### 048 — Custom Lead Fields
Creates `custom_field_definitions` table for per-tenant configurable lead attributes. Columns: tenant_id (FK→tenants, ON DELETE CASCADE), field_name (TEXT), field_type (TEXT CHECK: text/number/dropdown/date/checkbox, DEFAULT 'text'), options (JSONB DEFAULT '[]'), is_required (BOOLEAN DEFAULT false), sort_order (INTEGER DEFAULT 0), created_at (TIMESTAMPTZ). Unique on (tenant_id, field_name). Also adds `custom_fields` (JSONB DEFAULT '{}') to `leads` table. Indexed on tenant_id. RLS with service_role.

**Applied:** Verified applied 2026-03-19 (originally added in Cycle 87).

### 049 — SEO Audit, GEO Scores, Keyword Rankings
Creates `seo_audits` (tenant_id, overall_score, categories JSONB, critical_issues/warnings/passed_checks/recommendations JSONB, pages_analyzed). Creates `geo_scores` (tenant_id, overall_score, platform_scores JSONB, visibility_factors/recommendations JSONB, business_name/type/city/website_url). Creates `keyword_rankings` (tenant_id, keyword, difficulty_score, estimated_position, search_volume_estimate, recommendations JSONB). All indexed on tenant_id. RLS with service_role. Unique constraint on (tenant_id, keyword) for keyword_rankings.

**Applied:** 2026-03-17 via Supabase MCP.

### 050 — Social Media Marketing + Campaigns
Creates `social_posts` (tenant_id, platform CHECK facebook/instagram/twitter/linkedin/google_business, content, media_urls JSONB, hashtags TEXT[], status CHECK draft/scheduled/published/failed, scheduled_for, published_at, external_post_id, engagement_data JSONB). Creates `marketing_campaigns` (tenant_id, name, type CHECK email/sms, subject, body, target_filter JSONB, status CHECK draft/scheduled/sending/sent/failed, scheduled_for, sent_at, totals for recipients/sent/opened/clicked). Creates `campaign_sends` (campaign_id, tenant_id, lead_id, channel, recipient, status CHECK sent/delivered/opened/clicked/bounced/failed, timestamps). All indexed, RLS with service_role.

**Applied:** 2026-03-17 via Supabase MCP.

### 051 — Invoicing & Text-to-Pay
Creates `invoices` table for tracking billable work with Stripe Payment Link integration. Columns: tenant_id (FK→tenants, ON DELETE CASCADE), lead_id (FK→leads, ON DELETE SET NULL), bid_id (FK→bids, ON DELETE SET NULL), invoice_number (TEXT NOT NULL), items_json (JSONB NOT NULL DEFAULT '[]'), subtotal/tax_amount/total (NUMERIC(10,2)), tax_rate (NUMERIC(5,2)), status (TEXT CHECK: draft/sent/viewed/paid/overdue/cancelled, DEFAULT 'draft'), due_date (DATE), paid_at (TIMESTAMPTZ), payment_method (TEXT), stripe_payment_link (TEXT), stripe_payment_id (TEXT), notes (TEXT), sent_at/sent_via (TEXT), created_at/updated_at (TIMESTAMPTZ). Indexed on tenant_id, lead_id, and (tenant_id, status). RLS with service_role.

**Applied:** 2026-03-18 via Supabase MCP.

### 052 — Sales Pipeline Stages
Creates `pipeline_stages` table for tenant-configurable sales pipeline stages. Columns: tenant_id (FK→tenants, ON DELETE CASCADE), name (TEXT NOT NULL), sort_order (INTEGER DEFAULT 0), color (TEXT DEFAULT '#3b82f6'), is_won (BOOLEAN DEFAULT false), is_lost (BOOLEAN DEFAULT false), created_at (TIMESTAMPTZ). Indexed on tenant_id. RLS with service_role. Also adds to `leads` table: deal_value (NUMERIC(12,2) DEFAULT 0), expected_close_date (DATE), stage_changed_at (TIMESTAMPTZ DEFAULT now()).

**Applied:** 2026-03-18 via Supabase MCP.

### 053 — Smart Lists (Dynamic Lead Segments)
Creates `smart_lists` table for tenant-configurable saved filter presets that dynamically resolve to lead sets. Columns: tenant_id (FK→tenants, ON DELETE CASCADE), name (TEXT NOT NULL), description (TEXT), filter_json (JSONB NOT NULL DEFAULT '{}'), cached_lead_count (INTEGER DEFAULT 0), last_refreshed_at (TIMESTAMPTZ), is_default (BOOLEAN DEFAULT false), created_at/updated_at (TIMESTAMPTZ). Indexed on tenant_id. RLS with service_role.

**Applied:** 2026-03-18 via Supabase MCP.

### 054 — Form & Survey Builder
Creates `forms` table for embeddable forms that auto-create leads on submission. Columns: tenant_id (FK→tenants, ON DELETE CASCADE), name (TEXT NOT NULL), description (TEXT), fields_json (JSONB NOT NULL DEFAULT '[]'), settings_json (JSONB NOT NULL DEFAULT '{}'), is_active (BOOLEAN DEFAULT true), submission_count (INTEGER DEFAULT 0), public_token (TEXT UNIQUE), redirect_url (TEXT), success_message (TEXT DEFAULT 'Thank you...'), created_at/updated_at (TIMESTAMPTZ). Creates `form_submissions` table: form_id (FK→forms, ON DELETE CASCADE), tenant_id (FK→tenants, ON DELETE CASCADE), lead_id (FK→leads, ON DELETE SET NULL), data_json (JSONB NOT NULL DEFAULT '{}'), source_url (TEXT), ip_address (TEXT), created_at (TIMESTAMPTZ). Indexed on tenant_id, public_token, form_id. RLS with service_role.

**Applied:** 2026-03-18 via Supabase MCP.

### 055 — Campaign Sending Started At
Adds `sending_started_at` (TIMESTAMPTZ) to `marketing_campaigns` table. Used by the background campaign send task to detect stalled campaigns (stuck in 'sending' for >30 minutes).

**Applied:** 2026-03-18 via Supabase MCP.

### 056 — Google Place ID
Adds `google_place_id` (TEXT) to `tenants` table. Enables direct Google write-review links (`https://search.google.com/local/writereview?placeid={id}`) in review request automation.

**Applied:** 2026-03-18 via Supabase MCP.

### 057 — Conversation Channel Index + SMS Backfill
Adds index `idx_conversations_channel ON conversations(client_id, channel)` for omnichannel inbox filtering. Backfills existing SMS conversations (`session_id LIKE 'sms_%'`) to `channel='sms'`. Note: `channel` column (TEXT DEFAULT 'widget') already existed on conversations table.

**Applied:** 2026-03-18 via Supabase MCP.

### 058 — Fix Conversations Lead FK
Drops and re-creates `conversations.lead_id` FK constraint with `ON DELETE SET NULL`. The original constraint had no ON DELETE clause, causing dangling references when leads were deleted or merged.

**Applied:** 2026-03-18 via Supabase MCP.

### 059 — Invoice Item Templates
New table `invoice_item_templates` for reusable line items in invoices. Columns: tenant_id, description, unit_price, category, sort_order, is_active. GIN index on tenant_id.

**Applied:** 2026-03-19 via Supabase MCP.

### 060 — Invoice Deposits & Recurring
Adds columns to `invoices`: deposit_amount (NUMERIC), amount_paid (NUMERIC), is_recurring (BOOLEAN), recurrence_interval (TEXT with CHECK), next_invoice_date (DATE), parent_invoice_id (UUID FK→invoices).

**Applied:** 2026-03-19 via Supabase MCP.

### 061 — Documents & E-Signatures
Two new tables:
- `documents`: tenant_id, lead_id, title, template_html, rendered_html, status (draft/sent/viewed/signed/expired/cancelled), signer_name/email/phone, signed_at, signature_data, signature_ip, signing_token (unique UUID), expires_at, sent_at/via, viewed_at, notes.
- `document_templates`: tenant_id, name, category, template_html, variables (TEXT[]), is_active.

**Applied:** 2026-03-19 via Supabase MCP.

### 062 — Lead Insurance Fields
Adds 3 TEXT columns to `leads`: insurance_carrier, insurance_member_id, insurance_group. For dental/medical businesses to track patient insurance information.

**Applied:** 2026-03-21 via Supabase MCP.

### 063 — Service Types for Booking
New table `service_types` for defining services with custom durations. Columns: tenant_id, name, duration_minutes, description, price, is_active, sort_order. Enables service-based slot duration in appointment booking.

**Applied:** 2026-03-21 via Supabase MCP.

### 064 — Lead Date of Birth
Adds `date_of_birth DATE` to leads table for birthday greetings automation.

### 065 — Client Accounts (White-Label Login)
New table `client_accounts` for client portal authentication. Columns: tenant_id, lead_id, email, password_hash, created_at. Unique constraints on (tenant_id, email) and (tenant_id, lead_id). Also adds `client_login_enabled BOOLEAN DEFAULT false` to tenants table.

**Applied:** 2026-06-13 (verified live via Supabase introspection — `client_accounts` table present). Was logged "Pending" but had in fact been applied. Stale-log false positive (see 2026-06-13 audit).

### 066 — Appointment Waitlist
New table `waitlist_entries` for appointment waitlist management. Columns: tenant_id (FK→tenants, ON DELETE CASCADE), lead_id (FK→leads, ON DELETE SET NULL), customer_name (TEXT NOT NULL), customer_email (TEXT), customer_phone (TEXT), preferred_date (DATE NOT NULL), preferred_time_start/end (TEXT), service_type_id (FK→service_types, ON DELETE SET NULL), notes (TEXT), status (TEXT CHECK: waiting/notified/booked/expired/cancelled, DEFAULT 'waiting'), notified_at (TIMESTAMPTZ), booked_appointment_id (FK→appointments, ON DELETE SET NULL), created_at (TIMESTAMPTZ). Indexed on (tenant_id, status) and (tenant_id, preferred_date) for waiting entries. RLS enabled.

**Applied:** 2026-06-13 (verified live — applied under renamed object `waitlist_entries`; see 2026-06-13 audit). **Note: Duplicate `066_waitlist.sql` renumbered to `083_waitlist.sql` (2026-04-05).**

### 067 — Lead Scoring Configuration
New table `scoring_configs` for per-tenant configurable lead scoring weights. Columns: tenant_id (FK→tenants, ON DELETE CASCADE), factor (TEXT NOT NULL), weight (INTEGER CHECK 0-100, DEFAULT 10), description (TEXT), is_enabled (BOOLEAN DEFAULT true), created_at (TIMESTAMPTZ). Unique index on (tenant_id, factor). Indexed on tenant_id. RLS enabled.

**Applied:** 2026-06-13 (verified live — applied as `scoring_configs` + `leads.lead_score`; see 2026-06-13 audit). **Note: Duplicate `067_scoring_configs.sql` renumbered to `084_scoring_configs.sql` (2026-04-05).**

_Update this file after every migration. The post-edit Claude Code hook will remind you._

### 068 — Invoice Number Unique Index
Adds unique index `idx_invoices_tenant_number ON invoices(tenant_id, invoice_number)`. Prevents duplicate invoice numbers under concurrent creation. Backend retries with incremented sequence on conflict.

**Applied:** 2026-06-13 (verified live — unique index `idx_invoices_tenant_number` present; see 2026-06-13 audit).

### 069 — Lead Email Bounced
Adds `email_bounced` (BOOLEAN DEFAULT FALSE) and `email_bounced_at` (TIMESTAMPTZ) to `leads`. Partial index on bounced leads. Resend webhook sets this flag; automation engine and email sender skip bounced leads.

**Applied:** 2026-06-13 (verified live — `leads.email_bounced` present; see 2026-06-13 audit).

### 070 — Pipeline Automations
Creates `pipeline_automations` table for auto-trigger actions when leads move between pipeline stages. Columns: tenant_id (FK→tenants, ON DELETE CASCADE), name (TEXT), trigger_stage (TEXT NOT NULL), actions (JSONB NOT NULL DEFAULT '[]'), is_active (BOOLEAN DEFAULT TRUE), created_at, updated_at. Indexed on tenant_id and (tenant_id, trigger_stage) for active automations. Actions support: email, create_task, notify_team.

**Applied:** 2026-06-13 (verified live — pipeline automation tables present; see 2026-06-13 audit).

### 071 — Widget Teaser Message
Adds `teaser_message` (TEXT, nullable) to `widget_configs`. Stores the text displayed in the teaser bubble when the chat widget is minimized. Shown after a 3-second delay to prompt visitor engagement. Nullable — when NULL, the widget falls back to its default teaser behavior. Uses `ADD COLUMN IF NOT EXISTS` for safe re-runs.

**Applied:** 2026-03-31 via Supabase Management API. Verified: `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'widget_configs' AND column_name = 'teaser_message'` returned `[{"column_name":"teaser_message","data_type":"text"}]`.

### 072 — Widget Custom Instructions
Adds `custom_instructions` (TEXT, nullable) to `widget_configs`. Stores per-tenant AI system prompt overrides — identity line, business-specific facts, rules, and disclaimers. When set, replaces the generic "You are a friendly AI assistant for X" opener in `_build_system_prompt`. Standard platform rules (lead capture, language matching, handoff) still apply. Wired into `widget_helpers._build_system_prompt` via `custom_instructions` param; passed from `widget_chat.py` as `widget.get("custom_instructions")`.

**Applied:** 2026-03-31 via Supabase MCP. MTOptions tenant (`69411b59-5b0a-4eb2-88a6-525eee47133d`) system prompt set: identity as MTOptions Assistant (Pinpoint Financial Group LLC), pricing/trial facts, risk disclaimers, "never mention AgentNexLiFy" rule.

### 073 — Email Sequences
Creates four tables for a dedicated email/SMS drip sequence system, separate from the older `automation_sequences` (migration 005) system:
- `email_sequences`: sequence definitions with `trigger_type` ('lead_captured', 'tag_added', 'manual'), `trigger_config` JSONB, and `is_active`. FK to tenants via `tenant_id`.
- `email_sequence_steps`: individual steps with `step_order`, `delay_days` + `delay_hours` (separate fields, more granular than the old `delay_minutes`), `subject`, `body`, and `email_type` ('email'/'sms'). FK to email_sequences via `sequence_id`.
- `email_sequence_enrollments`: tracks lead enrollment with `UNIQUE(sequence_id, lead_id)` dedup constraint, `status` ('active'/'completed'/'cancelled'/'paused'), and `current_step`. FKs to leads(id) and tenants(id).
- `email_sequence_sends`: per-send audit trail with `scheduled_for` TIMESTAMPTZ (for queue processing), `sent_at`, `error`. FKs to enrollments, steps, leads, and tenants.

Five indexes: tenant lookup on sequences, sequence lookup on steps, tenant+status on enrollments, tenant+status+scheduled_for on sends (covering index for queue worker), enrollment_id on sends.

All four tables: RLS enabled, service_role full access policy. Pattern matches migrations 019, 050, 051.

**Applied:** 2026-03-31 via Supabase MCP (mcp__supabase__apply_migration). All four tables confirmed created.

### 074 — conversations.lead_captured
Adds `lead_captured` (BOOLEAN NOT NULL DEFAULT false) to the `conversations` table. Populated by `_capture_leads_from_session()` in `backend/routers/widget_helpers.py` after a lead is successfully inserted (new lead path) or identified (existing lead path). Enables analytics, filtering, and reporting that depend on knowing whether a conversation resulted in a lead capture.

**Applied:** 2026-04-01 via Supabase MCP.

### 075 — Widget Teaser Config
Adds two columns to `widget_configs` to fully control the teaser bubble:
- `teaser_delay_seconds` (INTEGER NOT NULL DEFAULT 3) — seconds after page load before bubble appears (0-60)
- `teaser_enabled` (BOOLEAN NOT NULL DEFAULT TRUE) — global on/off switch for the teaser bubble

Note: `teaser_message` was already added in migration 071. Migration 075 completes the teaser bubble feature.

MTOptions tenant (both tenant rows) seeded with `teaser_enabled=true`, `teaser_message='Have questions about our options alerts? Ask me!'`, `teaser_delay_seconds=3`.

**Applied:** 2026-04-01 via Supabase MCP (075_widget_teaser_config.sql). File renamed from 074 to avoid collision with existing 074_conversations_lead_captured.sql.

### 076 — Fix conversations FK + add leads.source

**Root cause of analytics showing 0 conversations:**
`conversations.client_id` had a FK pointing to the legacy `clients` table (leftover from original real-estate platform). Widget chat inserts `client_id = tenant_id` (a UUID from `tenants`). The FK violation caused every insert to fail silently, keeping `conversations` permanently empty. Any endpoint querying `conversations` returned 0.

Changes:
- Drops `conversations_client_id_fkey` (was → `clients.id`) and re-creates it pointing to `tenants(id) ON DELETE CASCADE`
- Adds `source TEXT DEFAULT 'widget'` to `leads` table for lead-source analytics
- Back-fills existing leads with `source = 'widget'`

**Applied:** 2026-04-01 via Supabase MCP.

### 077 — Widget Knowledge Base
Adds `knowledge_base` (TEXT, nullable) to `widget_configs`. Stores the AI-generated markdown knowledge base produced during the onboarding wizard (step 3). Injected into the widget chat system prompt via `widget_chat.py` when present, giving the AI business-specific context without requiring manual prompt editing. Editable post-onboarding from the dashboard. Uses `ADD COLUMN IF NOT EXISTS` for safe re-runs.

**Applied:** 2026-06-13 (verified live — `widget_configs.knowledge_base` column present; see 2026-06-13 audit).

### 078 — Expand business_type CHECK constraint
Drops and recreates the `tenants.business_type` CHECK constraint to include 27 valid values (up from 10). Fixes CHECK constraint violations during signup for the new industries added to the onboarding wizard dropdown.

New values added: accounting, bakery, bar_nightclub, cafe, catering, chiropractic, cleaning, electrical, food_truck, hvac, landscaping, moving, pest_control, photography, roofing, tutoring, veterinary

Existing values retained: auto_shop, dental, fitness, legal, medical, other, plumbing, realestate, restaurant, salon

**Applied:** 2026-06-13 (verified live via Supabase introspection — `tenants.business_type` CHECK lists all 28 industry types). Was logged "Pending" but had in fact been applied; signups across these industries work in production. The schema-sync "CRITICAL pending" alert was a stale-log false positive.

### 079 — Wizard Drop-Off Events
Creates `wizard_events` table for onboarding wizard funnel analytics. Columns: tenant_id (FK→tenants, ON DELETE CASCADE), step (INTEGER CHECK 1-6), action (TEXT CHECK: enter/complete/skip/abandon), created_at (TIMESTAMPTZ). Indexed on tenant_id and step. RLS enabled with service_role full access. Used by the `POST /api/v1/onboarding/wizard-event` endpoint to track conversion through the 6-step onboarding wizard.

**Applied:** 2026-06-13 (verified live — `wizard_events` table present; see 2026-06-13 audit).

### 080 — Conversations RLS Policies + Unique Constraint
Fixes critical bug: conversations table had RLS enabled (migration 001) but NO policies, causing silent INSERT failures from anon/authenticated roles. Adds three RLS policies (service_role full access, authenticated scoped to client_id=auth.uid(), anon full access for widget). Deduplicates existing (client_id, session_id) pairs and adds UNIQUE constraint `conversations_client_session_unique` on (client_id, session_id) to prevent duplicate conversation records and enable safe UPSERT.

**Applied:** 2026-04-02 via Supabase MCP.

### Migration 081 — Knowledge Base Tables (2026-04-04)
- Enabled pgvector extension
- Created `kb_articles` table: slug (unique), title, category, summary, content, embedding (vector 1024), source_urls (text[]), tags (text[]), word_count
- Created `kb_sources` table: source_url (unique), file_path, category, relevance_score, title, compiled (boolean)
- HNSW index on kb_articles.embedding for cosine similarity
- Index on kb_sources.compiled for pending source queries

### Migration 082 — Repurpose Jobs (2026-04-04)
- Created `repurpose_jobs` table: tenant_id (FK), source_type, source_url, source_content, source_title, tone, outputs (JSONB), status, connected IDs
- RLS enabled with tenant policy + service role policy
- Indexes on tenant_id and status

### Migration 083 — Waitlist (2026-04-05, renumbered)
_Renumbered from `066_waitlist.sql` to `083_waitlist.sql` to resolve duplicate numbering with `066_appointment_waitlist.sql`._ Same content as documented under 066 — Appointment Waitlist above.

**Applied:** 2026-06-13 (verified live — `waitlist_entries` present; see 2026-06-13 audit). Renumbered from 066.

### Migration 084 — Scoring Configs (2026-04-05, renumbered)
_Renumbered from `067_scoring_configs.sql` to `084_scoring_configs.sql` to resolve duplicate numbering with `067_lead_scoring_config.sql`._ Same content as documented under 067 — Lead Scoring Configuration above.

**Applied:** 2026-06-13 (verified live — `scoring_configs` present; see 2026-06-13 audit). Renumbered from 067.

### Migration 085 — Password Reset Tokens (2026-04-05, renumbered)
Adds `reset_token` (TEXT) and `reset_token_expires` (TIMESTAMPTZ) to `tenants`. Partial index on `reset_token` for non-null values. Supports password reset flow via email token. _Renumbered from `068_password_reset_tokens.sql` to `085_password_reset_tokens.sql` to resolve duplicate numbering with `068_invoice_number_unique.sql`._

**Applied:** Superseded — password reset ships via `tenants.reset_token` + `tenants.reset_token_expires` columns (see `backend/routers/auth_password_reset.py`), verified live 2026-06-13. The standalone `password_reset_tokens` table was never created and is not needed; this migration is obsolete. Do not apply.

---

**2026-04-05 — Duplicate Migration Renumbering:**
Renumbered 3 duplicate migration files to resolve numbering conflicts:
- `066_waitlist.sql` -> `083_waitlist.sql`
- `067_scoring_configs.sql` -> `084_scoring_configs.sql`
- `068_password_reset_tokens.sql` -> `085_password_reset_tokens.sql`
The "keep" files (`066_appointment_waitlist.sql`, `067_lead_scoring_config.sql`, `068_invoice_number_unique.sql`) retain their original numbers. Historical duplicates at 005 and 007 remain unchanged (documented separately).

### 086 — A/B Testing Tables
Creates three tables for multivariate marketing campaign testing:
- `ab_tests`: tenant_id, name, description, test_type (subject_line/send_time/body_content/campaign_variant), status (draft/running/completed/paused), winner_variant_id, started_at, completed_at.
- `ab_test_variants`: ab_test_id (FK→ab_tests), name, variant_config (JSONB), traffic_pct, sends/opens/clicks/conversions counters.
- `ab_test_sends`: ab_test_id, variant_id, campaign_send_id, tenant_id. Links A/B test variants to individual campaign sends.

**Applied:** 2026-06-13 (verified live — A/B testing tables (×3) present; see 2026-06-13 audit). RLS added in migration 091.

### 087 — Automation Rules
Creates `automation_rules` table for event-driven automation. Columns: tenant_id, name, description, trigger_type (16 event types including lead_captured, tag_added, form_submitted, appointment_created, pipeline_stage_changed, email_opened, scheduled_daily/weekly, etc.), trigger_config (JSONB), conditions (JSONB), actions (JSONB), is_active (BOOLEAN), execution_count, last_triggered_at.

Also creates `automation_rule_logs` for execution audit trail: rule_id, tenant_id, trigger_data (JSONB), actions_executed (JSONB), status (success/partial_failure/failed), error_message.

**Applied:** 2026-06-13 (verified live — `automation_rules` present; see 2026-06-13 audit). RLS added in migration 091.

### 088 — Campaign Analytics Aggregates
Creates `campaign_analytics_aggregates` for pre-computed daily/weekly campaign metrics. Columns: tenant_id, campaign_id (FK→marketing_campaigns), period_start (DATE), period_type (daily/weekly), total_sent/delivered/opened/clicked/bounced, unique_opens/clicks. UNIQUE on (campaign_id, period_start, period_type). Indexed on tenant_id.

**Applied:** 2026-06-13 (verified live — `campaign_analytics_aggregates` present; see 2026-06-13 audit). RLS added in migration 091.

### 089 — Platform Admin Tracking
Adds admin management columns to `tenants`: admin_discount_pct (INTEGER), admin_notes (TEXT), acquired_at (TIMESTAMPTZ), first_paid_at (TIMESTAMPTZ). Adds indexes on created_at and (plan, plan_status) for growth queries.

Creates `admin_promotions` table: tenant_id, promotion_type (free_tier/discount/extended_trial/partner_deal/case_study/referral), discount_pct (0-100), notes, starts_at, expires_at, is_active.

**Applied:** 2026-06-13 (verified live — `tenants.admin_discount_pct`/`acquired_at` + `admin_promotions` + `platform_monthly_revenue` present; see 2026-06-13 audit). RLS added in migration 091.

### 090 — Add Autopilot Plan to CHECK Constraint
Drops and recreates `tenants_plan_check` to include `autopilot`: `CHECK (plan IN ('free', 'growth', 'professional', 'autopilot', 'enterprise'))`. Fixes constraint violations when creating autopilot subscriptions.

**Applied:** 2026-06-13 (verified live via Supabase introspection — `tenants_plan_check` includes `autopilot`). Was logged "Pending" but had in fact been applied; autopilot subscriptions work in production. The schema-sync "CRITICAL pending" alert was a stale-log false positive.

### 091 — RLS and Guards for Migrations 086-089
Enables RLS and creates tenant isolation policies on all tables from migrations 086-089: ab_tests, ab_test_variants, ab_test_sends, automation_rules, automation_rule_logs, campaign_analytics_aggregates, admin_promotions. Uses `IF NOT EXISTS` guards throughout.

**Applied:** 2026-06-13 (verified live — RLS enabled on all 8 target tables (ab_test*/automation_rule*/campaign_analytics_aggregates/admin_promotions/platform_monthly_revenue); see 2026-06-13 audit).

### 092 — Appointment Reminder Tracking
Adds `reminder_24h_sent_at` (TIMESTAMPTZ) and `reminder_1h_sent_at` (TIMESTAMPTZ) to `appointments`. Replaces fragile notes-field string matching for reminder deduplication. Partial indexes on tenant_id for unsent reminders.

**Applied:** 2026-06-13 (verified live — `appointments.reminder_24h_sent_at`/`reminder_1h_sent_at` present; see 2026-06-13 audit).

---

## Schema Guardian Audit — 2026-04-06 (Migrations 086-092)

**Corrections to entries above (documented here to avoid rewriting history):**

### 086 — ab_test_variants columns are WRONG in the entry above
The entry says `variant_config (JSONB), traffic_pct, sends/opens/clicks/conversions counters`. The actual migration SQL has: `name TEXT, subject TEXT, body TEXT, send_time_override TIME, allocation_percent INTEGER DEFAULT 50 (CHECK 0-100), is_winner BOOLEAN DEFAULT FALSE`. The backend code (`backend/routers/ab_tests.py`) matches the SQL, not the log entry.

### 087 — Table name is WRONG in the entry above
The entry says `automation_rule_logs`. The actual table is `automation_rule_executions`. Column names also differ: `automation_rule_id` (not `rule_id`), `trigger_event` (not `trigger_data`), `actions_run` (not `actions_executed`), status values are `success/partial/failed` (not `success/partial_failure/failed`). Backend code matches the SQL.

### 089 — admin_promotions does NOT have `is_active` column
The entry above incorrectly lists `is_active` as a column. The actual migration has: `id, tenant_id, promotion_type, discount_pct, reason, approved_by, starts_at, expires_at, notes, created_at`. No `is_active`.

### 091 — RLS policies use wrong pattern
Policies use `auth.uid()` which is a Supabase Auth function. This codebase uses custom JWT auth and service_role key. Every other migration uses `current_setting('role', true) = 'service_role'`. The `auth.uid()` policies will never match for any caller. A corrective migration (093) is needed.

### 091 — References `automation_rule_logs` in entry above
Should be `automation_rule_executions`. The actual SQL file correctly uses `automation_rule_executions`.

---

### 093 — Fix RLS Policies (Corrective Migration for 091)
**Date:** 2026-04-07
Replaces the incorrect `auth.uid()` RLS policies from migration 091 with the correct `auth.role() = 'service_role'` pattern. All tables from 091 are fixed: ab_tests, ab_test_variants, ab_test_sends, automation_rules, automation_rule_executions, campaign_analytics_aggregates, admin_promotions.

**Why the fix was needed:** Migration 091 used `auth.uid()` (Supabase Auth pattern) but this codebase uses custom FastAPI JWT auth with service_role key. The `auth.uid()` policies would silently return 0 rows for any PostgREST query with anon/authenticated roles. The service_role key bypasses RLS, so FastAPI queries were unaffected, but the policies were semantically wrong and created security confusion.

**Correct RLS pattern for this codebase:**
```sql
CREATE POLICY table_policy ON table_name
    FOR ALL USING (auth.role() = 'service_role');
```
All tenant isolation is enforced at application layer in FastAPI, not at RLS layer.

**Applied:** 2026-06-13 (verified live — RLS policies present on the 086-089 tables; see 2026-06-13 audit).

---

### 094 — Reconcile Leads Schema with Production Reality
**Date:** 2026-04-07
Adds 8 columns to `leads` that existed in production but had no migration files — they were added ad-hoc to Supabase and are required by active backend code. Without this migration, any new environment (test/staging/demo) fails at runtime.

Columns added (all `IF NOT EXISTS`):
- `lead_temperature` TEXT with CHECK constraint (`hot`, `warm`, `cold`) — used by lead scoring and pipeline views
- `lead_type` TEXT — CRM categorization (buyer, seller, service_inquiry, etc.)
- `must_haves` TEXT — property preferences or service requirements
- `pre_approved` BOOLEAN DEFAULT false — mortgage pre-approval flag
- `conversation_summary` TEXT — AI-generated chat session summary
- `next_steps` TEXT — AI-recommended follow-up actions
- `appointment_date` TIMESTAMPTZ — scheduled or suggested appointment
- `updated_at` TIMESTAMPTZ DEFAULT NOW() — last modification timestamp

Indexes: `idx_leads_temperature`, `idx_leads_type`, `idx_leads_appointment_date` (partial, non-null only).

**Applied:** 2026-06-13 (verified live — `leads.lead_temperature`/`conversation_summary` present; see 2026-06-13 audit).

### 095 — Conversation Memory Column
**Date:** 2026-04-07
Adds `memory` JSONB column to `conversations` table for structured conversation memory. Enables context continuity across AI interactions without full message history in prompt.

GIN index `idx_conversations_has_memory` on `memory` column (partial, non-null only).

**Applied:** 2026-06-13 (verified live — conversation memory column present; see 2026-06-13 audit).

### 096 — Production Hardening
**Date:** 2026-04-07
Large multi-purpose migration with 4 sections:

**1. Client ID canonicalization (leads + conversations):**
- Adds `client_id` UUID to both `leads` and `conversations` (IF NOT EXISTS)
- Backfills from `tenant_id` where `client_id` is NULL
- Adds FK to `tenants(id)` as NOT VALID first, validates only if no orphans exist
- Sets NOT NULL only if all rows have valid client_id
- Indexes on `client_id` for both tables

**2. Automation locks:**
- Creates `automation_locks` table (name TEXT PK, owner TEXT, locked_until TIMESTAMPTZ)
- `try_acquire_automation_lock(name, owner, ttl_seconds)` — atomic lock acquisition via UPSERT
- `release_automation_lock(name, owner)` — deletes lock row
- Replaces per-process in-memory coordination for multi-worker safety

**3. Durable email quotas:**
- Creates `tenant_email_daily_sends` (tenant_id + send_date PK, send_count INTEGER)
- `reserve_email_send_quota(tenant_id, daily_limit)` — atomic increment with cap
- Replaces process-local counters that reset on restart

**4. OAuth state nonces:**
- Creates `oauth_states` table (provider + nonce PK, tenant_id, expires_at, consumed_at)
- Prevents replay/cross-session OAuth linking attacks
- Indexes on (tenant_id, provider) and expiry for cleanup

All new tables have RLS enabled with `auth.role() = 'service_role'` policy. Functions use SECURITY DEFINER with `SET search_path = public`.

**Note:** Migration tolerates orphaned `client_id` values — FK is left NOT VALID with a NOTICE if orphans exist (commit 738ba0b).

**Applied:** 2026-06-13 (verified live — `leads.client_id` + `conversations.client_id` + `automation_locks`/`oauth_states`/`tenant_email_daily_sends` present; see 2026-06-13 audit). Multi-worker locks confirmed live.

### 097 — No-Show Recovery Tracking Columns
**Date:** 2026-04-08
Adds two columns to `appointments` for no-show recovery outreach tracking:
- `noshow_recovery_sent_at` TIMESTAMPTZ — when initial recovery message was sent
- `noshow_followup_sent_at` TIMESTAMPTZ — when follow-up was sent

Partial index `idx_appointments_noshow_recovery` on `(status, noshow_recovery_sent_at)` WHERE `status = 'no_show'` — optimizes the recovery query that finds no-show appointments needing outreach.

**Applied:** 2026-06-13 (verified live — `appointments.noshow_recovery_sent_at`/`noshow_followup_sent_at` present; see 2026-06-13 audit).

### 098 — Daily Briefing, No-Show Recovery Toggles, Pre-Chat Form Config
**Date:** 2026-04-08
Adds tenant feature toggles and widget pre-chat form:
- `tenants.daily_briefing_enabled` BOOLEAN DEFAULT false — morning SMS briefing with leads, appointments, tasks
- `tenants.noshow_recovery_enabled` BOOLEAN DEFAULT true — auto SMS+email to no-show appointments
- `widget_configs.pre_chat_form` JSONB DEFAULT null — JSON config for pre-chat form fields `[{name, label, type, required}]`

Column comments added for documentation.

**Applied:** 2026-06-13 (verified live — `tenants.daily_briefing_enabled` present; see 2026-06-13 audit). Required for daily briefing and pre-chat form features.

### 099 — AI Lead Qualification Fields
**Date:** 2026-04-09
Adds structured output from the Claude Managed Agents `lead_qualifier` agent to the `leads` table. Runs asynchronously on paid plans after a new lead is captured. Complements (does not replace) the rule-based `lead_scoring` service — the inline scorer runs on every lead, the AI qualifier only on plans >= growth.

- `leads.qualification_json` JSONB — full structured response (intent_score, fit_score, recommendation, reasoning, suggested_first_reply)
- `leads.qualification_recommendation` TEXT — extracted recommendation with CHECK constraint (`hot_call_now`, `warm_nurture_sequence`, `cold_drop`, `disqualify_spam`)
- `leads.qualified_at` TIMESTAMPTZ — when the last successful qualification run completed

Partial indexes `idx_leads_qualification_recommendation` and `idx_leads_qualified_at` — optimize dashboard filters for hot-lead views.

**Applied:** 2026-04-09 via Supabase Management API (MCP auth was unavailable). Required for AI lead qualification feature (backend/services/lead_qualification.py).

### 100 — AI-Drafted Documents (quotes / invoices / proposals)
**Date:** 2026-04-09
Extends the existing `documents` table (from migration 061) to support binary files generated by the Claude Managed Agents `document_drafter` agent via the docx/xlsx/pdf skills. Agent writes to `/mnt/session/outputs/`, exports the artifact as `content_base64` in its final JSON reply, and the backend persists the decoded bytes inline in `documents.file_bytes`.

- `documents.kind` TEXT — CHECK (quote | invoice | proposal), nullable for legacy rows
- `documents.file_bytes` BYTEA — source of truth for generated file bytes in V1
- `documents.file_type` TEXT — CHECK (docx | xlsx | pdf)
- `documents.file_name` TEXT — suggested download filename
- `documents.anthropic_file_id` TEXT — optional debugging metadata if we ever capture an upstream file identifier
- `documents.draft_metadata` JSONB — line items, totals, session_id, file size
- `documents.generated_by_agent` TEXT — agent slug (e.g. `document_drafter`)

Relaxes `documents.template_html` from NOT NULL to nullable so AI-drafted rows (no HTML template) coexist with the legacy HTML contract flow.

Partial indexes `idx_documents_kind` and `idx_documents_generated_by_agent` on non-null rows.

**Applied:** 2026-04-09 via Supabase Management API. Required for AI document drafting feature (backend/services/document_drafting.py + POST /api/v1/managed-agents/{tid}/draft-document).

### 101 — Widget AI Fallback Flag
**Date:** 2026-04-10
Adds opt-in boolean to `widget_configs` controlling whether widget chat escalates to the `support_agent` managed agent as a second-tier fallback when the first-tier Claude reply emits the `FALLBACK_TO_SUPPORT_AGENT` marker.

- `widget_configs.enable_ai_fallback` BOOLEAN NOT NULL DEFAULT false — rollout is tenant-by-tenant

See `backend/routers/widget_chat.py:Step 9a` and `docs/managed-agents.md` for the full flow description.

**Applied:** 2026-06-13 (verified live — `widget_configs.enable_ai_fallback` column present; see 2026-06-13 audit).

### 102 — Marketing Suite Add-on (backfill)
**Date:** 2026-04-12 (file mtime) — backfilled 2026-04-20
Adds `$49.99/mo` Marketing Suite add-on subscription columns to `tenants`. Carve-out policy: strip marketing features from plans, force add-on. Existing paid tenants grandfathered so live customers keep access.

- `tenants.marketing_addon_active` BOOLEAN NOT NULL DEFAULT false
- `tenants.marketing_addon_stripe_sub_id` TEXT
- `tenants.marketing_addon_started_at` TIMESTAMPTZ
- `tenants.marketing_addon_grandfathered` BOOLEAN NOT NULL DEFAULT false
- Index `idx_tenants_marketing_addon_sub` on `marketing_addon_stripe_sub_id`
- One-time UPDATE grandfathers existing active paid tenants (growth/professional/autopilot/enterprise)

Gates: SEO Audit Hub, Social Media, Marketing Campaigns, Marketing Dashboard, A/B Tests, Automation Rules, Trigger Logs. Deactivation script: `scripts/migrations/deactivate_grandfathered_marketing.sh` (run when notice window expires).

**Applied:** Status unknown — backfill log entry only. Verify via Supabase MCP before next billing event.

### 103 — Structured Lead Parser Flag
**Date:** 2026-04-15
Adds opt-in boolean to `widget_configs` controlling whether widget chat runs the `structured_extractor` managed agent as a **background enrichment pass** on each user message. Fills `name/email/phone/interest/timeline/budget` fields the regex parser missed.

- `widget_configs.enable_structured_lead_parser` BOOLEAN NOT NULL DEFAULT false — rollout opt-in per tenant
- Cost ceiling: ~$0.002/call (Haiku); MTOptions ~$1.41/mo at 704 msgs
- Latency on chat happy path: 0ms (background task — fires after response sent)
- Phase 1 of 5 in `/plans/lead-parser-replacement_plan.md`
- Source spec: `/specs/lead-parser-replacement_spec.md`

**Applied:** 2026-04-15 via Supabase Dashboard SQL editor.

### 106 - Launch Risk Guardrails
**Date:** 2026-04-18
Adds launch-readiness safety tables and tenant columns for the paid-launch risk sprint.

- `tenants.ai_monthly_token_alert_threshold` / `ai_monthly_token_hard_limit` optional per-tenant overrides for widget AI cost caps
- `tenant_ai_usage_monthly` monthly token ledger with reserved tokens, actual usage, blocked count, and threshold timestamps
- RPCs `reserve_ai_token_budget`, `record_ai_token_usage`, and `release_ai_token_reservation` for multi-worker-safe AI usage enforcement
- `billing_refunds` admin refund audit trail keyed by Stripe refund ID
- `tenant_cancellation_events` cancellation reason history
- `billing_dunning_events` failed-payment/dunning event log for `invoice.payment_failed`
- `tenants.cancellation_*` and `tenants.billing_dunning_*` latest-state columns

All new tables use service-role RLS policies. Required by `backend/services/ai_usage_guard.py`, `backend/routers/billing.py`, and `backend/routers/auth.py`.

**Applied:** 2026-04-19 via `mcp__supabase__apply_migration` (version `20260420023659`). Verified via `mcp__supabase__list_migrations`.

### 107 — Admin Refund Request Idempotency
**Date:** 2026-04-18
Adds operator-supplied idempotency key to `billing_refunds` so retries after transient Stripe/audit-log failures cannot create duplicate refunds.

- `billing_refunds.refund_request_id` TEXT NULL — operator-supplied idempotency key
- Partial UNIQUE INDEX `idx_billing_refunds_tenant_request` on `(tenant_id, refund_request_id) WHERE refund_request_id IS NOT NULL`

Depends on migration 106 (`billing_refunds` table). Required by admin refund endpoint in `backend/routers/billing.py`.

**Applied:** 2026-04-19 via `mcp__supabase__apply_migration` (version `20260420023706`). Verified via `mcp__supabase__list_migrations`.

### 104 — Structured Lead Parser Default True (planned)
**Date:** Planned ~2026-04-22
Changes `widget_configs.enable_structured_lead_parser` DEFAULT from `false` to `true` so new tenants get enrichment automatically.

**Gate:** Apply ONLY after ≥95% lead-field completion rate holds for 7 days across all Phase 5 testers. See `audits/audit-lead-enrichment-2026-04-15.md`.

- `widget_configs.enable_structured_lead_parser` DEFAULT changed from false → true
- Existing rows unchanged (ALTER COLUMN SET DEFAULT only affects new inserts)

**Applied:** NOT YET — pre-written, awaiting gate criteria. Apply ~2026-04-22.

### 105 — Leads Enrichment Source
**Date:** 2026-04-15
Adds `enrichment_source` column to `leads` to track how lead fields were populated.

- `leads.enrichment_source` TEXT NULL — values: `'regex'` (basic parser), `'ai'` (structured_extractor), `NULL` (legacy/manual)
- Set to `'ai'` by `_enrich_lead_from_message` in `backend/routers/widget_helpers.py` when AI enrichment writes fields
- Returned by `GET /api/v1/leads/:tenant_id` and displayed as "AI" badge in LeadsPage
- Drives lead quality stat bar (% with name + email + phone) in LeadsPage dashboard

**Applied:** 2026-04-15 via Supabase Dashboard SQL editor.

### 108 — Photo-Quote Widget Tables
**Date:** 2026-04-20
Creates 3 tables supporting photo-upload quote feature (spec: `specs/photo-quote_spec.md`, epic: #47, migration issue: #36).

**Tables:**
- `tenant_pricing_rules` — per-tenant per-vertical pricing rules (tiered severity jsonb), optional disclaimer + confidence threshold overrides. UNIQUE (client_id, industry). Industry enum: plumbing, roofing, hvac, auto_body, landscaping, pest.
- `quote_requests` — one row per customer photo submission. Full image purged at 30d (`full_image_purged_at`), thumbnail + metadata retained permanently. Severity enum: minor, major, needs_human. Indexed for client+created_at and for retention-job scanning.
- `tenant_quote_usage` — monthly counter per tenant, PK (client_id, period_start). Drives Stripe metered billing (500/mo included, $0.15 overage).

**Function:**
- `purge_photo_quote_images_30d() → int` — SECURITY DEFINER. Called daily by backend scheduler (issue #40). Sets `image_url=null` + `full_image_purged_at=now()` for rows >30d.

**RLS:** service_role only on all 3 tables. Tenant access via backend API — no direct PostgREST.

**Conventions:** `client_id` (not `tenant_id`) per CLAUDE.md Rule 1. All FKs cascade on tenant delete.

**Applied:** 2026-04-20 via `mcp__supabase__apply_migration`. Verified via `mcp__supabase__list_tables` — all 3 tables present with RLS enabled.

### 109 — Drive KB Onboarding Tables
**Date:** 2026-04-20
Creates 3 tables for multi-provider KB sync (spec: `specs/drive-kb-onboarding_spec.md`, epic: #56, migration issue: #48). v1 ships Drive only; Dropbox/OneDrive/Box plug in via same schema later.

**Tables:**
- `tenant_integrations` — per-tenant per-provider OAuth integration. UNIQUE (client_id, provider). Provider enum: drive, dropbox, onedrive, box. Encrypted tokens via pgcrypto (`oauth_token_enc`, `oauth_refresh_token_enc` bytea).
- `integration_sync_log` — per-sync summary row. Counters for files_added/updated/skipped/pii_flagged + sections_reembedded/skipped (drives diff-based embedding cost savings per Q8 B).
- `kb_section_hashes` — SHA256 per section per tenant, PK (client_id, section_id). Drives re-embed decision: skip unchanged sections, re-embed only diffs.

**RLS:** service_role only on all 3 tables.
**Conventions:** `client_id` not `tenant_id`. All FKs cascade.
**Applied:** 2026-04-20 via `mcp__supabase__apply_migration`. Verified.

### 110 — Tenant API Keys (Zapier)
**Date:** 2026-04-20
Single-table migration for Zapier app authentication (spec: `specs/zapier-crm-export_spec.md`, epic: #64, migration issue: #57).

**Table:**
- `tenant_api_keys` — bcrypt hash + 8-char display prefix + soft-delete via `revoked_at`. Partial index on `key_prefix` where not revoked — auth middleware does prefix lookup before bcrypt verify for performance.

**Security:**
- Plaintext keys NEVER stored — only bcrypt hash (cost 12).
- Prefix shown in dashboard for identification.
- Audit trail preserved via soft-delete (keeps `created_at`, `revoked_at`).

**RLS:** service_role only. Tenant access via backend CRUD endpoints.
**Conventions:** `client_id` not `tenant_id`.
**Applied:** 2026-04-20 via `mcp__supabase__apply_migration`. Verified.

### 111 — Missed-Call Text-Back (Phase 1)
**Date:** 2026-04-22
**Commit:** 6020a43
Ships the first ops automation table backing the missed-call-text-back workflow (2026-04-21 pivot memory: `project_automation_vs_crm_pivot.md`).

**Table:**
- `missed_call_texts` — one row per inbound missed call → outbound SMS pairing. Captures `call_sid`, `sms_sid`, `from_phone`, `to_phone`, `template_id`, `status` enum (`sent`/`failed`/`skipped`), plus `converted_to_lead_id` FK for Phase-2 attribution. Tenant FK cascades.

**Column add:**
- `tenants.avg_ticket_override` — `decimal(10,2)` nullable. Phase-2 attribution (dollars recovered per tenant). Landed early; cheap + allows backfill independent of attribution UI.

**Backfill:**
- Insert `missed_call_textback` automation row for every existing tenant (`is_enabled=true`, default hold config `{mode: hold, hold_seconds: 60, template_id: default}`). `ON CONFLICT DO NOTHING` keeps re-runs safe.

**RLS:** `missed_call_texts` RLS enabled with `tenant_id = auth.uid()` policy. Note — this migration uses `tenant_id` column name (diverges from project `client_id` convention on newer tables). Rationale: matches existing `tenants.id = auth.uid()` session pattern used by `automations`/`leads`. Flagged here so future schema-guardian passes don't misread as drift.

**Index:** `(tenant_id, created_at DESC)` for activity-feed queries.

**Applied:** 2026-04-22 via migration file commit. Prod apply **unverified** — needs `mcp__supabase__apply_migration` confirmation (tracked in current-tasks.md Priority 0).


### 112 — Onboarding v2 widget_configs columns
**Date:** 2026-04-25
ALTER widget_configs adding 3 columns for v2 wizard cohort tracking + readiness badge (spec: `specs/onboarding-v2_spec.md` §6.1.1).

**Columns added:**
- `onboarding_version TEXT NOT NULL DEFAULT 'v1'` CHECK IN ('v1','v2') — cohort filter for funnel analytics
- `ready_to_launch BOOLEAN NOT NULL DEFAULT false` — drives "Ready to launch" badge
- `readiness_criteria JSONB NOT NULL DEFAULT '{services_count, hours_filled, faqs_count, logo_uploaded}'::jsonb` — per-tenant checklist state

**Index:** `idx_widget_configs_onboarding_version` partial WHERE `onboarding_version = 'v2'` (cohort queries).

**Backward compat:** every existing tenant lands on `v1` + `ready_to_launch=false` automatically. v2 wizard completion flips on new signups only (per spec §3 — no re-onboarding existing tenants).

**Migration number note:** spec reserved 115-117 but actual gap was 111→. Used 112 (next sequential per migration-workflow rule).

**RLS:** unchanged (widget_configs already gated to service_role + tenant-scoped via existing policies).
**Conventions:** `tenant_id` (widget_configs uses tenant_id, not client_id — leads/conversations are the client_id outliers).
**Applied:** NOT YET — pending `mcp__supabase__apply_migration` after review.


### 113 — Fraud Guardrails
**Date:** 2026-04-25
Adds `signup_attempts` table for velocity-based fraud detection on registration (criterion 10.2).

**Table:**
- `signup_attempts` — IP address, email, optional tenant_id FK, blocked_reason, created_at.

**Indexes:**
- `idx_signup_attempts_ip_created` — velocity lookups by IP
- `idx_signup_attempts_email_created` — velocity lookups by email

**RLS:** service_role only.
**Conventions:** `tenant_id` (not `client_id`) on FK.
**Applied:** NOT YET — pending `mcp__supabase__apply_migration` after review.


### 111 — Missed Call Texts (Phase 1)
**Date:** 2026-04-22
Adds `missed_call_texts` table for missed-call-textback automation, `tenants.avg_ticket_override` for Phase 2 attribution, and seeds the `missed_call_textback` automation row for every existing tenant.

**Table:**
- `missed_call_texts` — `tenant_id` FK to `tenants(ON DELETE CASCADE)`, `call_sid`, `sms_sid`, `from_phone`, `to_phone`, `template_id`, `status` CHECK (`sent`/`failed`/`skipped`), `created_at`, `converted_to_lead_id` FK to `leads`.

**Column add:**
- `tenants.avg_ticket_override decimal(10,2)` — manual override for revenue attribution.

**Indexes:**
- `idx_missed_call_texts_tenant_created` on `(tenant_id, created_at DESC)`.

**Backfill:** seeds one `automations` row per tenant: `type='missed_call_textback'`, `is_enabled=true`, default config `{mode:"hold", hold_seconds:60, template_id:"default"}`. `ON CONFLICT DO NOTHING`.

**RLS:** enabled. Policy `missed_call_texts_tenant_isolation` — `tenant_id = auth.uid()`.
**Conventions:** `tenant_id` (NOT `client_id` — leads/conversations are the outliers; new tables use `tenant_id`).
**Applied:** YES — 2026-04-22 (per `-- Applied:` marker in migration file).


### 114 — Idempotency Keys
**Date:** 2026-04-23
Adds `idempotency_keys` table to dedup webhook redeliveries from Stripe and Twilio.

**Table:**
- `idempotency_keys` — `key TEXT PRIMARY KEY` (format `'provider:event_id'`, e.g. `'stripe:evt_abc123'` or `'twilio:<MessageSid>'`), `provider TEXT NOT NULL`, `created_at TIMESTAMPTZ DEFAULT now()`, `response_status INT`, `response_body JSONB` (cached payload for replay).

**Indexes:**
- `idempotency_keys_created_at_idx` on `(created_at)` — supports TTL cleanup queries.

**TTL:** 7 days, manual cron — no auto-delete trigger. Recommended cleanup query in migration comment: `DELETE FROM idempotency_keys WHERE created_at < now() - INTERVAL '7 days';`.

**RLS:** NOT enabled in this migration — see 116 for the security followup.
**Conventions:** no tenant column (cross-tenant dedup store; access gated to service role via 116).
**Applied:** YES — confirmed 2026-04-27.


### 115 — Contextual Reindex Marker
**Date:** 2026-04-24
Adds `contextual_reindexed_at` marker to `kb_articles` so `scripts/reindex_contextual.py` can skip already-processed chunks.

**Column add:**
- `kb_articles.contextual_reindexed_at TIMESTAMPTZ` — set when chunk has been re-embedded with Anthropic contextual retrieval prefix. NULL = not yet reindexed.

**Affected tables:** `kb_articles` (from migration 081 — system-wide wiki, `vector(512)`).

**RLS:** unchanged.
**Conventions:** column add only; no tenant-column impact.
**Applied:** YES — confirmed 2026-04-27.


### 116 — Idempotency Keys RLS (security followup to 114)
**Date:** 2026-04-25
Closes the public-readability gap on `idempotency_keys`. `response_body` JSONB caches webhook payloads (Stripe customer email, subscription IDs, Twilio phone numbers). Without RLS, anon/authenticated callers using project public keys could enumerate cached webhook responses across all tenants.

**Changes:**
- `ALTER TABLE idempotency_keys ENABLE ROW LEVEL SECURITY;`
- `CREATE POLICY "idempotency_keys_deny_public" ON idempotency_keys FOR ALL TO public USING (false) WITH CHECK (false);`

**Effect:** anon + authenticated roles get nothing. Service role bypasses RLS automatically — backend webhook handlers continue to work.
**Conventions:** deny-all-public is the right pattern for cross-tenant infra tables that backend-only code touches.
**Applied:** YES — confirmed 2026-04-27. RLS active on `idempotency_keys`.


### 117 — Zapier API Keys
**Date:** 2026-04-27
**Commit:** feature/58-zapier-auth
Adds `zapier_api_keys` table backing Issue #58 — Zapier API key auth + tier gating + rate limit. Originally numbered 112 on the feature branch; renumbered to 117 to avoid collision with `112_widget_configs_onboarding_v2.sql` after rebase.

**Table:**
- `zapier_api_keys` — `id`, `client_id` FK, `name`, `key_prefix` (8 chars, indexed for lookup), `key_hash` (bcrypt cost 12), `last_used_at`, `revoked_at`, `rate_limit_rpm` (default 100), `created_at`.

**RLS:** service_role only (backend CRUD endpoints handle tenant scoping).
**Conventions:** `client_id` (matches leads/conversations convention).
**Applied:** YES — confirmed via PR #91 squash-merge.


### 118-123 — Agent OS P0 Foundation
**Date:** 2026-05-21
**Branch:** claude/agent-os-grill-resume-cHznV
Six tables backing the Agent OS overhaul P0 (chat-first orchestrator). Spec: `specs/agent-os-overhaul_spec.md`. Plan: `plans/agent-os-p0_plan.md`. Every new table carries the `os_` prefix and is `client_id`-scoped (matches leads/conversations).

**Tables:**
- `118 os_threads` — task-conversation threads. `id`, `client_id`, `title`, `created_by`, `status` (active|archived), timestamps. Index `(client_id, status)`.
- `119 os_messages` — thread messages. `id`, `client_id`, `thread_id` FK→os_threads ON DELETE CASCADE, `role` (user|assistant|agent|system), `content`, `agent_run_id`, `created_at`. Index `(thread_id, created_at)`.
- `120 os_agent_runs` — worker-agent invocations (async). `id`, `client_id`, `thread_id` FK CASCADE, `agent_name`, `status` (queued|running|succeeded|failed), `thought_process` JSONB, `deliverable` JSONB (approval-gated draft, no separate table in P0), `deliverable_status` (pending_approval|approved|rejected), `error_detail`, `bug_reported_at`, timestamps, `completed_at`. Index `(client_id, status)`.
- `121 os_memory_entries` — semantic memory. `id`, `client_id`, `kind` (fact|preference|decision|conversation_summary), `content`, `embedding vector(512)` (voyage-3-lite), `source`, `created_by`, `is_pinned`, timestamps. HNSW cosine index on `embedding`. Also creates `match_os_memory(p_client_id, p_query_embedding, p_match_count)` SQL function for client-scoped ANN search. Karpathy graph layer (os_memory_nodes/edges) deferred past P0.
- `122 os_backlog_requests` — no-fit backlog. `id`, `client_id`, `thread_id` FK→os_threads ON DELETE SET NULL, `summary`, `detail`, `reason`, `status` (open|accepted|declined|deferred), `decided_by`, `decision_note`, `created_at`, `decided_at`. Index `(client_id, status)`.
- `123 os_tenant_usage` — per-tenant usage metering. `id`, `client_id`, `cycle_start` DATE, `agent_runs`, `messages`, `input_tokens`, `output_tokens`, timestamps. UNIQUE `(client_id, cycle_start)`. Index `(client_id, cycle_start DESC)`.

**Extension:** 121 runs `CREATE EXTENSION IF NOT EXISTS vector`.
**RLS:** deny-public on all 6 tables (`FOR ALL TO public USING (false) WITH CHECK (false)` — matches migration 116 pattern). Backend uses the service-role client (bypasses RLS); app-layer tenant scoping via `tenant_scope.py`.
**Conventions:** `client_id` on every table (registered in `_TENANT_COLUMN_OVERRIDES` in `backend/services/tenant_scope.py`).
**Applied:** YES — confirmed 2026-05-21 via Supabase MCP `list_tables` (all 6 tables present, RLS enabled, project `pxserpybmajixqrmzaly`).


### 128 — Per-Tenant Agent OS Auto-Send Toggle
**Date:** 2026-05-27
**Branch:** claude/friendly-bardeen-H6ErW
Adds `tenants.os_auto_send_enabled BOOLEAN NOT NULL DEFAULT FALSE`. When FALSE (default), every Agent OS worker deliverable lands as `pending_approval` and waits for owner review. When TRUE, worker deliverables are marked `approved` directly at worker-success time — skipping the owner review gate. Action-handler firing is decided separately by `os_agent_runs.action_type` (migration 126); this flag only controls the approval gate.

**Risk:** stale prompt + wired action handler + `auto_send=TRUE` → customer-facing action fires with zero human review. Default OFF; owner-gated toggle on the Settings page.

**Backend wiring:** `backend/services/os_workers/__init__.py::_tenant_auto_send_enabled()` reads the flag; `run_worker` branches between `approved` and `pending_approval`. Settings endpoint `PUT /api/v1/auth/settings/{tenant_id}` accepts `os_auto_send_enabled`; `GET /api/v1/auth/tenant/{tenant_id}` returns it. Frontend toggle in `MessagingSettingsCards::AgentOSAutoSendCard`.

**Applied:** YES — 2026-05-27 via Supabase MCP `apply_migration` (project `pxserpybmajixqrmzaly`).

### 129 — chat_messages.os_message_id (Group C Mirror Tag)
**Date:** 2026-05-27
**Branch:** claude/friendly-bardeen-H6ErW
Adds `chat_messages.os_message_id UUID NULL`. Widget OS reply mirror tags each `chat_messages` row with the originating `os_messages.id` so replay is detectable. Partial unique index `chat_messages_os_message_id_uniq ON (tenant_id, os_message_id) WHERE os_message_id IS NOT NULL` enforces dedup only on mirrored rows; legacy pre-mirror rows stay unconstrained.

**Backend wiring:** `backend/services/os_outbound_mirror.py::_mirror_widget` pre-checks `chat_messages` by `(tenant_id, os_message_id)` before insert. Idempotent across the 4 Uvicorn workers in prod.

**Applied:** YES — 2026-05-27 via Supabase MCP `apply_migration` (project `pxserpybmajixqrmzaly`).

### 130 — os_outbound_log (Group C Phase 3, Cross-Process Replay Protection)
**Date:** 2026-05-27
**Branch:** claude/friendly-bardeen-H6ErW
Adds dedup anchor for non-widget channels. Schema: `id UUID PK`, `client_id UUID NOT NULL`, `os_message_id UUID NOT NULL REFERENCES os_messages ON DELETE CASCADE`, `channel TEXT` (`sms | email | facebook`), `provider TEXT` (`twilio_byo | twilio_platform | resend | messenger`), `provider_message_id TEXT DEFAULT ''`, `status TEXT DEFAULT 'sent'`, `sent_at TIMESTAMPTZ DEFAULT now()`. Unique index `os_outbound_log_dedup_uniq ON (client_id, os_message_id, channel)` is the replay-protection lookup; `os_outbound_log_client_sent_idx ON (client_id, sent_at DESC)` for operational queries. RLS enabled + `os_outbound_log_deny_public` policy (service-role only). Tenant column is `client_id` (override registered in `tenant_scope._TENANT_COLUMN_OVERRIDES`).

**Why:** widget mirror is idempotent via `chat_messages.os_message_id` (migration 129) but SMS / email / Facebook had no cross-process guard. With 4 Uvicorn workers, a runner re-fire on the same `os_messages` row would re-send the same SMS / email / FB DM. `os_outbound_log` is the dedup anchor: pre-check by `(client_id, os_message_id, channel)` before sending, post-insert after a successful send. Channel-scoped key supports future fan-out (simultaneous SMS + email mirror of one OS reply).

**Failure semantics:** best-effort. Pre-check DB error falls through to send (rare duplicate beats blocking the customer's reply); post-insert DB error keeps `mirrored` status (customer already got the reply).

**Backend wiring:** `backend/services/os_outbound_mirror.py::_outbound_log_already_sent` + `_outbound_log_record` helpers; `_mirror_sms`, `_mirror_email`, `_mirror_facebook` each gained pre-check + post-insert calls; dispatcher threads `db` through. Tests: `tests/test_agent_os.py::TestOutboundMirrorIdempotency` (9 cases — replay skip per channel, channel-scope correctness, success records row, pre-check DB failure falls through, post-insert DB failure preserves mirrored).

**Applied:** YES — 2026-05-27 via Supabase MCP `apply_migration` (project `pxserpybmajixqrmzaly`). Verified live: 8 columns match schema, 3 indexes present (`os_outbound_log_pkey`, `os_outbound_log_dedup_uniq`, `os_outbound_log_client_sent_idx`), RLS enabled, `os_outbound_log_deny_public` policy in place.

## Migration 133 — os_graph_memory (2026-06-09)

**Tables:** `os_graph_nodes` (one node per `(client_id, entity_type, normalized_name)` — name, summary, capped JSONB `facts` with provenance, `mention_count`, voyage-3-lite 512d `embedding`, HNSW index) + `os_graph_edges` (typed relations, `observed_count` weight, FK cascade to nodes, unique per `(client_id, from_node, to_node, relation)`). Both RLS deny-public.

**Why:** ADR `planning/decisions/2026-05-25-agent-os-graph-memory.md` deferred the graph layer with revisit triggers; trigger #4 (owner-requested navigable memory view) fired 2026-06-09. Extraction cost stays inside the ADR's concern: ONE Haiku call per owner turn after the reply persists (`backend/services/os_graph_memory.py::accumulate_from_turn`), never per memory write. New facts write through to `os_memory_entries` so semantic recall stays consistent. Retrieval feeds `SharedContext.kb` as `KbEntry {topic, answer}` — zero engine changes.

**Backend wiring:** `os_graph_memory.py` (extract/upsert/retrieve), `os_thread_runner.py` (kb enrichment pre-engine + background accumulation post-persist), `routers/os_graph.py` (GET /api/v1/os/graph, owner-only DELETE /graph/nodes/{id}). Frontend: `components/os/MemoryPanel.jsx` in the Agent OS page. Tests: `tests/test_os_graph_memory.py` (11 cases).

**Applied:** YES — 2026-06-09 via Supabase MCP `apply_migration` (project `pxserpybmajixqrmzaly`). Verified live: both tables present with RLS enabled + table comments in place.

## Migration 134 — pricing_ab_events (2026-06-10)

**Table:** `pricing_ab_events` — anonymous marketing-site A/B events. `id UUID PK`, `visitor_id TEXT` (first-party cookie UUID, 8-64 chars, NO PII), `variant TEXT` (`control | variant_b`), `event TEXT` (`view | cta_click`), `plan TEXT` (canonical plan names, nullable), `created_at TIMESTAMPTZ`. Indexes on `(variant, event)` + `created_at`. RLS enabled, service-role-only policy. No tenant FK by design — visitors are pre-signup.

**Why:** launch rubric 9.3 "Pricing page A/B test wired". Experiment `pricing_page_cta_2026_06`: deterministic 50/50 variant by sha256(experiment:visitor_id) — assignment is server-derived and never trusted from the client.

**Backend wiring:** `backend/routers/pricing_experiment.py` (GET variant + POST event, both rate-limited 30/min, event insert fault-tolerant), registered in `main.py`. Frontend: `frontend/src/utils/pricingExperiment.js` (cookie visitor id + variant hook + event tracker), wired to Free-plan CTA in `Home.jsx`. Tests: `backend/tests/test_pricing_experiment.py` (11 cases).

**Applied:** YES — 2026-06-10 via Supabase MCP `apply_migration` (project `pxserpybmajixqrmzaly`).

## Migration 135 — referral columns + backfill (2026-06-10)

**Columns added to `tenants`:** `referral_code TEXT UNIQUE`, `referred_by UUID REFERENCES tenants(id)`, `referral_discount_pct INTEGER DEFAULT 0`. Backfilled `referral_code` for all 7 existing tenants (md5-derived 8-char codes).

**Why:** URGENT prod fix — repo migration 001 lists these columns but the live schema never had them; the referral wiring shipped in PR #227 made `/register` insert a nonexistent column (signup 500). See bug-patterns.md entry "Migration files ≠ live schema".

**Applied:** YES — 2026-06-10 via Supabase MCP `apply_migration` (project `pxserpybmajixqrmzaly`). Verified live: 7/7 tenants have codes.

## Migration 136 — hot_table_columns() RPC (2026-06-10)

**Function:** `public.hot_table_columns()` — returns (table_name, column_name) for the 7 hot tables; SECURITY DEFINER, service-role-only EXECUTE. Powers `scripts/check_schema_drift.py` + the `live-drift` CI job (PostgREST doesn't expose information_schema).

**Applied:** YES — 2026-06-10 via Supabase MCP (project `pxserpybmajixqrmzaly`). Verified live: 203 rows / 7 tables.

## Migration 137 — drop marketing_addon_* columns (2026-06-10)

**Dropped from `tenants`:** `marketing_addon_active`, `marketing_addon_grandfathered`, `marketing_addon_started_at`, `marketing_addon_stripe_sub_id` — unread since the add-on retirement (PR #228). Applied ONLY AFTER Railway rolled out #228 (the prior deploy still SELECTed marketing_addon_active in /me). Drift manifest updated to match.

**Applied:** YES — 2026-06-10 via Supabase MCP (project `pxserpybmajixqrmzaly`), post-rollout health verified.

## Migration 138 — os_uploads + os-uploads storage bucket (2026-06-11)

**Table:** `os_uploads` — Agent OS file/image uploads + AI-generated images. `id UUID PK`, `client_id UUID NOT NULL REFERENCES tenants(id)` (tenant col is **client_id**, registered in `tenant_scope.py` overrides), `kind TEXT CHECK ('upload'|'generated')`, `filename TEXT`, `content_type TEXT`, `size_bytes BIGINT`, `storage_path TEXT`, `public_url TEXT`, `vision_summary TEXT` (Haiku description of uploaded images), `prompt TEXT` (for generated), `created_at TIMESTAMPTZ`. 3 indexes (client_id, created_at, kind). RLS enabled, service-role-only.

**Storage bucket:** `os-uploads` — public, 10MB file limit, MIME allowlist (png/jpeg/webp/gif/pdf). Created via SQL insert into `storage.buckets`.

**Why:** Agent OS composer attachments + image generation (rate-limited: uploads 20/hr + 50/day per tenant; image gen 10/hr + 20/day). Backend: `backend/routers/os_files.py`, `backend/services/image_gen.py`. Also added `os_uploads` to GDPR purge list in `backend/services/account_deletion.py`.

**Applied:** YES — 2026-06-11 via Supabase MCP `apply_migration` (project `pxserpybmajixqrmzaly`); bucket verified live.

## Migration 139 — reconcile migration-001 stale DDL (2026-06-11)

**Guarded no-op on prod**: ADD COLUMN IF NOT EXISTS for `leads.client_id/status/areas_of_interest` + `conversations.client_id`; DROP IF EXISTS the 001-era names (`tenant_id`, `service_interest`, `lead_stage`) that never existed live. Purpose: fresh-DB replays of migrations/ now converge on the live shape (audit 2026-06-10 addendum CRITICAL — same failure class as the referral-columns incident).

**Applied:** YES — 2026-06-11 via Supabase MCP (verified no-op).

## Migration 140 — drift guard expanded to full schema (2026-06-11)

**Function:** `hot_table_columns()` now returns every public BASE TABLE's columns (was 7 hard-coded hot tables). Coverage scoped by `ops/schema/expected-columns.json` (regenerated: 113 tables) so the function never needs another migration. Still SECURITY DEFINER, service-role-only.

**Applied:** YES — 2026-06-11 via Supabase MCP.

## Migration 141 — tenants.os_auto_send_rules (2026-06-11)

**Column:** `os_auto_send_rules JSONB NOT NULL DEFAULT '{}'` — per-agent auto-send overrides (gap G6), e.g. `{"booking": true}`. Gate logic in `agent_os_bridge.resolve_deliverable_status`: per-agent rule beats global `os_auto_send_enabled`; NEVER_AUTO_SEND_AGENTS (invoicing, payments, complaints) cannot be overridden. Updated via PUT /api/v1/auth/settings/{tenant_id} with shape validation.

**Applied:** YES — 2026-06-11 via Supabase MCP. Manifest updated.

## Migration 142 — financial_services business_type (2026-06-11)

**Constraint:** `tenants_business_type_check` rebuilt with `financial_services` added to the 27-value allowlist (gap G8 — MTOptions vertical depth). Same migration moved MTOptions from `other` to `financial_services`. Powers the financial_services guidance pack (os_kb_feed), tailored Agent OS starters, FAQ seeds, and the express-setup dropdown entry.

**Applied:** YES — 2026-06-11 via Supabase MCP; MTOptions row verified moved.

## Migration 143 — tenants.voice_ai_enabled (2026-06-11)

**Column:** `voice_ai_enabled BOOLEAN NOT NULL DEFAULT false` — voice mode switch for inbound Twilio calls (gap G3). false (default) = voicemail mode: greeting + Record → transcription → AI summary → lead → Agent OS callback-text draft through the approval flow. true = live AI answering (Gather speech loop with vertical guidance), plan-gated to professional/enterprise in `backend/routers/calls.py`. Settings via PUT /api/v1/auth/settings + VoiceAICard UI.

**Applied:** YES — 2026-06-11 via Supabase MCP. Manifest updated.

## 2026-06-12 — migration 144: tenants.is_demo
- `tenants.is_demo BOOLEAN NOT NULL DEFAULT false` + partial index `idx_tenants_is_demo`.
- Marks the public live-demo sandbox tenant: demo tenants get outbound
  no-ops (email/SMS via demo_guard), restricted "demo" JWT role, nightly
  data reset. Applied live via Supabase MCP 2026-06-12.

## 2026-06-12 — migration 145: push_subscriptions (APPLIED 2026-06-12 via Supabase MCP)
- New table for Web Push subscriptions (pending-approval browser
  notifications — free alternative to the SMS leg): `id uuid pk`,
  `tenant_id uuid not null`, `endpoint text not null unique`,
  `keys jsonb not null`, `created_at timestamptz default now()` +
  `idx_push_subscriptions_tenant_id`. RLS enabled, service-role-only access.
- **Tenant column decision:** uses `tenant_id` (appointments-style). This is
  a new OS-adjacent table defined fresh — the `client_id` convention applies
  only to the legacy leads/conversations tables.
- Backend: `backend/routers/push_subscriptions.py` (subscribe/unsubscribe +
  public vapid-public-key), `backend/services/os_push_notify.py` (send,
  pywebpush import-guarded, no-ops without VAPID env keys).
- **Applied:** NO — file written only; apply via Supabase MCP. Requires
  Railway env vars VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY / VAPID_SUBJECT
  (manual step pending) before push actually fires.

## 2026-06-13 — migration 146: conversation_email_notify (file written; apply via Supabase MCP)
- Per-tenant "email me the full transcript when a widget conversation wraps".
  `tenants.conversation_email_notify_enabled boolean not null default false`,
  `tenants.conversation_notify_email text` (alert destination; falls back to
  `owner_email` when null), `conversations.notified_at timestamptz` +
  partial index `idx_conversations_unnotified` on `(client_id) WHERE
  notified_at IS NULL`.
- **Tenant column note:** `conversations` uses `client_id` (legacy convention);
  the new `notified_at` column sits alongside it. Tenant settings live on
  `tenants` (same place as `sms_notifications_enabled`/`notification_phone`).
- Backend: `backend/services/conversation_notify.py` (idle-sweep job
  `notify_idle_conversations`, exactly-once via `notified_at` claim), wired into
  the 5-min scheduler batch in `backend/main.py`. Settings read/write added to
  `backend/routers/auth.py` (`update_settings` allowlist + `get_tenant` select).
- Frontend: `ConversationEmailNotificationsCard` in
  `frontend/src/pages/settings/MessagingSettingsCards.jsx`, rendered via
  `SettingsPageContent.jsx`, form fields in `SettingsPage.jsx`.
- **Applied:** NO — apply via Supabase MCP. Additive + nullable/defaulted, safe
  ahead of deploy. (Note: supersedes the audit suggestion to renumber PR #212's
  migrations to 146 — use 147/148/149 there now.)

## 2026-06-13 — conversation email alerts: behavior change (on-NEW, not transcript-on-wrap)
- Per tenant request, the alert now fires the moment a NEW conversation comes in
  (inline from widget_chat `is_new`, background task) with a lightweight heads-up
  (first message + inbox link), NOT the full transcript on idle.
- `notify_idle_conversations` scheduled job + transcript builder removed;
  `conversation_notify.py` now exposes `notify_new_conversation`.
- The `tenants.conversation_email_notify_enabled` + `conversation_notify_email`
  columns (migration 146) are still used. `conversations.notified_at` +
  `idx_conversations_unnotified` are now VESTIGIAL (no reader) — harmless; drop in
  a future cleanup migration if desired.

---

## Verification audit — 2026-06-13 (live prod introspection, project pxserpybmajixqrmzaly)

The daily Schema Sync workflow escalated "CRITICAL: pending migrations — blocks
production" off this file's `Applied: Pending` text. Live introspection proved
that is a **stale-log false alarm, not a prod schema gap**. Confirmed applied:

- 065 client_accounts; 087 automation_rules; 070 automations/pipeline; 086 A/B
  test tables (×3); 088 campaign_analytics_aggregates.
- 078 business_type CHECK (28 industries); 090 plan CHECK (includes `autopilot`)
  — the two "CRITICAL" ones; markers corrected above.
- Applied under RENAMED objects: 066 → `waitlist_entries`, 067/084 → `scoring_configs`
  (+ `leads.lead_score`); 069 → `leads.email_bounced`; 095 → conversation memory
  column; 098 → `tenants.daily_briefing_enabled`.

Second-pass introspection 2026-06-13 — the prior "no live match" entries were
NAME mismatches, not real gaps. All confirmed applied:
- 077 widget knowledge base — applied as a **column** `widget_configs.knowledge_base`
  (the prior pass searched for a `*knowledge_base*` table, hence the miss).
- 079 wizard events — table is **`wizard_events`** (prior pass searched the wrong
  name `wizard_dropoff_events`).
- 085 `password_reset_tokens` — **superseded**, not pending. Password reset ships
  via `tenants.reset_token` + `tenants.reset_token_expires` columns
  (`backend/routers/auth_password_reset.py:88-91` stores them, `:144` looks up by
  `reset_token`), both verified live. The standalone table was never needed.
  Marker flipped to "Superseded — do not apply".

114 public tables total. Bottom line: **every** "Pending" entry was stale; the
schema-sync heuristic trusts this file's text rather than the DB. Follow-up
(DONE 2026-06-13): all 23 remaining `Pending` markers were resolved via live
introspection — 22 flipped to "Applied" (column/table/index/RLS presence
verified in project `pxserpybmajixqrmzaly`) and 085 to "Superseded". Pending
count is now 0, so the text-count `check` job no longer false-fires. The
authoritative DB introspection already lives in the `live-drift` job
(`scripts/check_schema_drift.py` vs `ops/schema/expected-columns.json`) — that,
not the markdown text, is the source of truth for live drift. Any future
`Applied: Pending` marker now means a genuinely unapplied migration.

---

### 147 — Qualifier Settings (per-tenant AI qualifier controls, GH #216)

Adds two owner-facing columns to `tenants` for the AI lead qualifier
(`backend/services/lead_qualification.py`), both additive + idempotent
(`ADD COLUMN IF NOT EXISTS`) with behavior-preserving defaults:

- `qualifier_enabled BOOLEAN NOT NULL DEFAULT true` — kill switch.
- `qualifier_min_intent INTEGER NOT NULL DEFAULT 0` — only spend AI-qualifier
  budget when the cheap rule-based `leads.lead_score` (0-10) clears this gate.
  CHECK `qualifier_min_intent BETWEEN 0 AND 10`.

Ported from PR #212 (migration 134 on `gap-3-research-worker-87IXF`),
renumbered 147. Pairs with the per-vertical rubric service
(`backend/services/qualification_rubrics.py`) and the owner-controls router
(`backend/routers/qualifier_config.py`, `/api/v1/qualifier/*`) + the
`AgentQualifierSettings` dashboard component.

**Applied:** 2026-06-13 via `mcp__supabase__apply_migration` (project
pxserpybmajixqrmzaly). Verified: both columns present with defaults
`true` / `0`.

---

### 148 — Encrypt integrations secrets at rest (onboarding-v2, GH #129/#131)

Adds two BYTEA columns to `integrations` for encrypted third-party secrets
(Stripe/Twilio/Resend API keys), both additive + idempotent:

- `access_token_enc BYTEA` — Fernet token for the API key.
- `refresh_token_enc BYTEA` — Fernet token for the refresh token (NULL for
  API-key providers).

`CREATE EXTENSION IF NOT EXISTS pgcrypto` is included (already present live).
Encryption is app-side via `cryptography.fernet` in
`backend/services/integration_key_vault.py` (spec onboarding-v2 §9 sanctions
app-side over in-DB pgcrypto so the vault is unit-testable to 100% coverage).
Key: `INTEGRATIONS_ENC_KEY` Railway env var; rotation versions via
`INTEGRATIONS_ENC_KEYS`. Never committed, never logged.

**Plaintext deprecation:** the existing `access_token` / `refresh_token` TEXT
columns are retained until a separate sunset migration runs AFTER
`scripts/backfill_integration_encryption.py` is verified (user-rules Rule 8:
no half-migrations). The existing service-role RLS policy is untouched.

**Applied:** 2026-06-14 via `mcp__supabase__apply_migration` (project
pxserpybmajixqrmzaly). Verified: both `access_token_enc` / `refresh_token_enc`
present as `bytea`.

### 149 — Platform support inbox tables (support widget + dashboard form + Agent OS alerts)

Three additive, idempotent (`create table if not exists`) platform-level tables
for the AgentNexLiFy operator's own support channels. Not tenant-scoped (no
`client_id`) — accessed only via the backend service-role key. RLS enabled with
no policies (service key bypasses; anon/authenticated denied — matches public.*).

- `platform_support_messages` — support-chat messages (session_id, role, content).
  Index on `(session_id, created_at)`.
- `platform_support_sessions` — one row per support-chat session; tracks
  `transcript_sent_at` for idempotent end-of-conversation transcript email,
  plus `reporter_email` and `page_url`.
- `support_messages` — dashboard "Send a message" form. The `/api/v1/support/contact`
  endpoint inserted here all along, but the table never existed, so the form 500'd.
  Created now so the form works end-to-end.

Consumed by `backend/routers/platform_support.py` (support widget),
`backend/routers/support.py` (dashboard form). Both forward to the platform
owner via `backend/services/platform_mailer.py` (PLATFORM_SUPPORT_EMAIL).

**Applied:** 2026-06-15 via `mcp__supabase__apply_migration` (project
pxserpybmajixqrmzaly). Verified: all three tables present, `rls_enabled=true`.

### 151 — audit_log (security follow-up)

Creates the `audit_log` table (id, tenant_id, action, metadata jsonb, created_at)
that `integration_key_vault._write_audit` wrote to all along — the table never
existed, so integration-key audit rows silently no-op'd (try/except-wrapped).
RLS on, no policies (service-key only). Indexes on (tenant_id, created_at) and
(action, created_at). Applied to prod 2026-06-15 via apply_migration, verified.

### 154 — conversations.sentiment + conversations.intent (per-conversation classification)

Adds two nullable columns to the client_id-scoped `conversations` table so each
widget conversation can carry a stored sentiment + intent:

- `sentiment TEXT CHECK (sentiment IN ('positive','neutral','negative'))` —
  vocabulary mirrors the `calls` table (migration 044) exactly.
- `intent TEXT` — short noun phrase (e.g. "booking request", "complaint").

Both `ADD COLUMN IF NOT EXISTS` (idempotent, additive). Populated off the user
hot path by `backend/services/conversation_enrichment.py` (Haiku classifier),
driven by the `run_pending_enrichment` batch job
(`backend/services/conversation_enrichment_job.py`) wired into the 30-min tier
of the scheduler loop in `backend/main.py`. Consumed by
`backend/services/agent_os_bridge.py::_load_conversation_sentiment` ->
`map_widget_history`, surfacing as `WidgetConversationData.sentiment` for the
Conversation Insights agent's "Customer sentiment" breakdown. The bridge loader
degrades to an empty map if the columns are absent, so it is safe to deploy the
code before the migration is applied.

**APPLIED to prod 2026-06-18** via `apply_migration` (project pxserpybmajixqrmzaly).
Verified both `conversations.sentiment` (text) and `conversations.intent` (text)
exist via information_schema. Closes the half-shipped state — enrichment code was
already referencing these columns before they existed in prod.

## 117_zapier_api_keys + 129_chat_messages_os_mirror

**APPLIED to prod 2026-06-23** via `apply_migration` (project pxserpybmajixqrmzaly).
The only 2 genuinely-pending migrations (see `audits/audit-schema-drift-2026-06-23.md`:
issue #263's "24 pending" was a false count from 005/007 duplicate-numbered files plus
an unreliable migration-history table). Both pure idempotent `ADD COLUMN IF NOT EXISTS`:
- 117: `tenant_api_keys.rate_limit_rpm` (int default 100), `tenant_api_keys.notes` (text),
  indexes `idx_tenant_api_keys_prefix`, `idx_tenant_api_keys_client`.
- 129: `chat_messages.os_message_id` (uuid null) + partial unique index
  `chat_messages_os_message_id_uniq` on (tenant_id, os_message_id) WHERE os_message_id IS NOT NULL.
Verified all 6 objects exist post-apply (information_schema + pg_indexes). 154 was already
live. Prod schema drift = 0.

## 161_allow_new_plan_names_in_tenants_check (renumbered from 158, 2026-07-09)

File renumbered 158→161 on 2026-07-09 because two migration files shared number 158
(the other: `158_wizard_events_fix_step_range`, GH #373). Both are applied to prod —
verified 2026-07-09 against live pg_constraint: `wizard_events_step_check` is 0–7 with
`demo_referral` allowed, and `tenants_plan_check` includes chatbot + agent_os. Rename
is repo hygiene only; no prod action taken.

**APPLIED to prod 2026-06-23** via `apply_migration` (project pxserpybmajixqrmzaly).
The `tenants_plan_check` constraint still only permitted the retired plan names
(`free`/`growth`/`professional`/`autopilot`/`enterprise`) after the 2026-06-15
reprice — so the live plans `chatbot` ($19.99) and `agent_os` ($99.99, "AI Workforce")
could not be written: any Stripe checkout for a new plan would fail the constraint
and admin SQL upgrades were blocked. DB-layer half of the repricing migration (code
gates fixed via plan_catalog.PREMIUM_PLANS; see bug-patterns.md 2026-06-23).
Dropped + re-added the constraint to allow `free, chatbot, agent_os` + the legacy
names (grandfathered). Verified by setting the Agent Nexlify test account
(aferna6@g.clemson.edu) to `agent_os` — previously rejected with 23514, now succeeds.

## 160_sms_opt_outs

**APPLIED to prod 2026-06-25** via `apply_migration` (project pxserpybmajixqrmzaly).
Durable per-tenant SMS opt-out ledger for TCPA compliance. `client_id` +
`phone_last10` (normalized last-10) with UNIQUE(client_id, phone_last10) and a
lookup index. Checked by `sms_compliance.is_suppressed()` before every outbound
SMS (AI Workforce sms.send + missed-call text-back). Inbound STOP now records
here durably (os_inbound.py), beyond the existing leads.unsubscribed flag.
See docs/dev-knowledge/council-fixes-register.md #1.

## 162_referral_rewards (APPLIED to prod 2026-07-09; renumbered from 160)

**Created 2026-06-23** as 160; renumbered to 162 on 2026-07-09 because 160 was taken
by `160_sms_opt_outs` (applied to prod 2026-06-25) and 161 by the renumbered
`161_allow_new_plan_names_in_tenants_check`. **APPLIED to prod 2026-07-09** via
`apply_migration` (table + both indexes). The reward grant stays inert until
`REFERRAL_REWARD_ENABLED=1` is set in Railway — launching the program is now a
single env-var flip.

New table `referral_rewards` records the flat $20 (2000-cent) Stripe customer-balance
credit granted to a referrer when a tenant they referred pays their FIRST invoice.
- `referred_tenant_id` is UNIQUE → idempotency: one reward per referee, ever. This
  enforces "first paid invoice only" and is safe against Stripe webhook redeliveries
  and the two parallel webhook endpoints (billing.py + stripe_webhooks.py).
- `attribution_channel`: 'promo_code' (tenants.referred_by UUID) or 'widget_watermark'
  (tenants.referred_by_widget_key → widget_configs.api_key → tenant).
- `status`: pending → granted | failed. Pure additive `CREATE TABLE IF NOT EXISTS`.
Consumed by `backend/services/referral_reward.py` (gated on REFERRAL_REWARD_ENABLED,
default OFF) and surfaced (earned credit) on `GET /api/v1/referral/my-stats`.


## 164_leads_client_email_unique (2026-07-10)
Added `UNIQUE (client_id, email)` on `leads` (constraint `leads_client_email_uniq`) to close the duplicate-lead check-then-insert race (launch audit H1). NULLs stay distinct so phone-only leads are unaffected. Applied to prod. Insert sites switched to upsert-ignore-duplicates.
