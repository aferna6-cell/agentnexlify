# Schema Change Log — AgentNexLiFy

Every database schema change. Claude Code checks this when working with database queries.

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
- `conversations` table still has FK to `clients.id` (legacy).
- `leads` table FK `client_id` references `tenants.id` (NOT `clients.id`) per the code.
- **Risk:** Confusion. The `clients` table should be deprecated/removed in a future cleanup.

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

_Update this file after every migration. The post-edit Claude Code hook will remind you._
