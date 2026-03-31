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

**Applied:** Pending — must be run on live Supabase manually.

### 066 — Appointment Waitlist
New table `waitlist_entries` for appointment waitlist management. Columns: tenant_id (FK→tenants, ON DELETE CASCADE), lead_id (FK→leads, ON DELETE SET NULL), customer_name (TEXT NOT NULL), customer_email (TEXT), customer_phone (TEXT), preferred_date (DATE NOT NULL), preferred_time_start/end (TEXT), service_type_id (FK→service_types, ON DELETE SET NULL), notes (TEXT), status (TEXT CHECK: waiting/notified/booked/expired/cancelled, DEFAULT 'waiting'), notified_at (TIMESTAMPTZ), booked_appointment_id (FK→appointments, ON DELETE SET NULL), created_at (TIMESTAMPTZ). Indexed on (tenant_id, status) and (tenant_id, preferred_date) for waiting entries. RLS enabled.

**Applied:** Pending — created 2026-03-23, not yet applied to Supabase. **Note: DUPLICATE FILE — both `066_appointment_waitlist.sql` and `066_waitlist.sql` exist in migrations/. Verify they are identical before applying; delete the duplicate.**

### 067 — Lead Scoring Configuration
New table `scoring_configs` for per-tenant configurable lead scoring weights. Columns: tenant_id (FK→tenants, ON DELETE CASCADE), factor (TEXT NOT NULL), weight (INTEGER CHECK 0-100, DEFAULT 10), description (TEXT), is_enabled (BOOLEAN DEFAULT true), created_at (TIMESTAMPTZ). Unique index on (tenant_id, factor). Indexed on tenant_id. RLS enabled.

**Applied:** Pending — created 2026-03-23, not yet applied to Supabase. **Note: DUPLICATE FILE — both `067_lead_scoring_config.sql` and `067_scoring_configs.sql` exist in migrations/. Verify they are identical before applying; delete the duplicate.**

_Update this file after every migration. The post-edit Claude Code hook will remind you._

### 068 — Invoice Number Unique Index (duplicate number)
Adds unique index `idx_invoices_tenant_number ON invoices(tenant_id, invoice_number)`. Prevents duplicate invoice numbers under concurrent creation. Backend retries with incremented sequence on conflict.

**Applied:** Pending — created 2026-03-25, not yet applied to Supabase.

### 068 — Password Reset Tokens (duplicate number)
Adds `reset_token` (TEXT) and `reset_token_expires` (TIMESTAMPTZ) to `tenants`. Partial index on `reset_token` for non-null values. Supports password reset flow via email token.

**Applied:** Pending — created 2026-03-25, not yet applied to Supabase. **Note: duplicate migration number — must renumber before applying.**

### 069 — Lead Email Bounced
Adds `email_bounced` (BOOLEAN DEFAULT FALSE) and `email_bounced_at` (TIMESTAMPTZ) to `leads`. Partial index on bounced leads. Resend webhook sets this flag; automation engine and email sender skip bounced leads.

**Applied:** Pending — created 2026-03-25, not yet applied to Supabase.

### 070 — Pipeline Automations
Creates `pipeline_automations` table for auto-trigger actions when leads move between pipeline stages. Columns: tenant_id (FK→tenants, ON DELETE CASCADE), name (TEXT), trigger_stage (TEXT NOT NULL), actions (JSONB NOT NULL DEFAULT '[]'), is_active (BOOLEAN DEFAULT TRUE), created_at, updated_at. Indexed on tenant_id and (tenant_id, trigger_stage) for active automations. Actions support: email, create_task, notify_team.

**Applied:** Pending — created 2026-03-25, not yet applied to Supabase.

### 071 — Widget Teaser Message
Adds `teaser_message` (TEXT, nullable) to `widget_configs`. Stores the text displayed in the teaser bubble when the chat widget is minimized. Shown after a 3-second delay to prompt visitor engagement. Nullable — when NULL, the widget falls back to its default teaser behavior. Uses `ADD COLUMN IF NOT EXISTS` for safe re-runs.

**Applied:** 2026-03-31 via Supabase Management API. Verified: `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'widget_configs' AND column_name = 'teaser_message'` returned `[{"column_name":"teaser_message","data_type":"text"}]`.

### 072 — Widget Custom Instructions
Adds `custom_instructions` (TEXT, nullable) to `widget_configs`. Stores per-tenant AI system prompt overrides — identity line, business-specific facts, rules, and disclaimers. When set, replaces the generic "You are a friendly AI assistant for X" opener in `_build_system_prompt`. Standard platform rules (lead capture, language matching, handoff) still apply. Wired into `widget_helpers._build_system_prompt` via `custom_instructions` param; passed from `widget_chat.py` as `widget.get("custom_instructions")`.

**Applied:** 2026-03-31 via Supabase MCP. MTOptions tenant (`69411b59-5b0a-4eb2-88a6-525eee47133d`) system prompt set: identity as MTOptions Assistant (Pinpoint Financial Group LLC), pricing/trial facts, risk disclaimers, "never mention AgentNexLiFy" rule.
