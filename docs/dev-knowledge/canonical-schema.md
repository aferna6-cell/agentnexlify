# Canonical Database Schema Reference

**Last updated:** 2026-04-18
**Migration number:** 106
**Status:** Authoritative — this file reflects PRODUCTION reality, not historical migration intent.

---

## ⚠️ Important Notes

1. Run the full migration chain for new environments. Historical migrations start with legacy `tenant_id` columns on `leads` and `conversations`; later migrations reconcile them to canonical `client_id`.
2. The `leads` and `conversations` tables use `client_id` (not `tenant_id`) as the FK to `tenants.id`. This is intentional and was fixed in migration 076.
3. Lead status uses `status` column (not `lead_stage`). Values: `new`, `visited`, `contacted`, `appointment_booked`, `closed`, `lost`.
4. Service interest uses `areas_of_interest` (not `service_interest`).

---

## Core Tables

### `tenants`
Multi-tenant accounts (business owners).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| business_name | TEXT | NOT NULL | |
| business_type | TEXT | | Industry vertical |
| owner_email | TEXT | UNIQUE, NOT NULL | Login email |
| owner_name | TEXT | | |
| password_hash | TEXT | | bcrypt hash |
| phone | TEXT | | |
| city | TEXT | | |
| website_url | TEXT | | |
| plan | TEXT | DEFAULT 'free' | free/growth/professional/autopilot/enterprise |
| plan_status | TEXT | DEFAULT 'trial' | |
| stripe_customer_id | TEXT | | |
| stripe_subscription_id | TEXT | | |
| monthly_conversation_limit | INTEGER | | |
| conversations_used_this_month | INTEGER | DEFAULT 0 | |
| reset_date | TIMESTAMPTZ | | |
| free_trial_started_at | TIMESTAMPTZ | | |
| trial_ends_at | TIMESTAMPTZ | | |
| referral_code | TEXT | UNIQUE | |
| referred_by | UUID | FK → tenants.id | |
| notification_phone | TEXT | | SMS notification number |
| sms_notifications_enabled | BOOLEAN | DEFAULT false | |
| ai_monthly_token_alert_threshold | INTEGER | | Optional per-tenant AI usage alert override |
| ai_monthly_token_hard_limit | INTEGER | | Optional per-tenant AI usage hard-stop override |
| cancellation_requested_at | TIMESTAMPTZ | | Latest requested subscription cancellation |
| cancellation_reason | TEXT | | Latest customer-selected cancellation reason |
| cancellation_reason_detail | TEXT | | Latest free-text cancellation detail |
| billing_dunning_last_sent_at | TIMESTAMPTZ | | Latest failed-payment notice timestamp |
| billing_dunning_attempt_count | INTEGER | DEFAULT 0 | Latest Stripe invoice attempt count |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | |

### `widget_configs`
Per-tenant widget configuration.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| tenant_id | UUID | FK → tenants.id, NOT NULL | |
| api_key | TEXT | UNIQUE, NOT NULL | Format: `anx_...` |
| bot_name | TEXT | DEFAULT 'Aria' | |
| agent_name | TEXT | DEFAULT 'Agent' | |
| primary_color | TEXT | DEFAULT '#6cff5c' | |
| greeting_message | TEXT | | |
| offline_message | TEXT | | |
| teaser_message | TEXT | | |
| teaser_enabled | BOOLEAN | DEFAULT true | |
| teaser_delay_seconds | INTEGER | DEFAULT 5 | |
| position | TEXT | DEFAULT 'bottom-right' | |
| collect_name | BOOLEAN | DEFAULT true | |
| collect_email | BOOLEAN | DEFAULT true | |
| collect_phone | BOOLEAN | DEFAULT false | |
| show_watermark | BOOLEAN | DEFAULT true | |
| custom_css | TEXT | | |
| allowed_domains | TEXT[] | | Domains where widget can embed |
| booking_enabled | BOOLEAN | DEFAULT true | |
| content_mode | BOOLEAN | DEFAULT false | Professional+ feature |
| business_type | TEXT | | |
| is_online | BOOLEAN | DEFAULT true | |
| custom_instructions | TEXT | | |
| knowledge_base_enabled | BOOLEAN | DEFAULT false | |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | |

### `leads`
Captured leads from widget, forms, and conversations.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| client_id | UUID | FK → tenants.id, NOT NULL | **NOT tenant_id** |
| name | TEXT | | |
| email | TEXT | | |
| phone | TEXT | | |
| areas_of_interest | TEXT | | **NOT service_interest** |
| budget | TEXT | | |
| timeline | TEXT | | |
| status | TEXT | DEFAULT 'new' | new/visited/contacted/appointment_booked/closed/lost |
| source | TEXT | DEFAULT 'widget' | |
| conversation_id | UUID | FK → conversations.id | |
| notes | TEXT | | |
| lead_score | INTEGER | DEFAULT 0 | 1-10 scale |
| lead_temperature | TEXT | | hot/warm/cold (added ad-hoc, migration 094) |
| lead_type | TEXT | | buyer/seller/service_inquiry (added ad-hoc, migration 094) |
| must_haves | TEXT | | (added ad-hoc, migration 094) |
| pre_approved | BOOLEAN | DEFAULT false | (added ad-hoc, migration 094) |
| conversation_summary | TEXT | | (added ad-hoc, migration 094) |
| next_steps | TEXT | | (added ad-hoc, migration 094) |
| appointment_date | TIMESTAMPTZ | | (added ad-hoc, migration 094) |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | (added ad-hoc, migration 094) |
| tags | TEXT[] | | Migration 016 |
| assigned_to | UUID | FK → team_members.id | Migration 026 |
| deal_value | NUMERIC | | Migration 052 |
| insurance_carrier | TEXT | | Migration 062 |
| insurance_member_id | TEXT | | Migration 062 |
| insurance_group | TEXT | | Migration 062 |
| date_of_birth | DATE | | Migration 064 |
| email_bounced | BOOLEAN | DEFAULT false | Migration 069 |
| unsubscribed | BOOLEAN | DEFAULT false | Migration 021 |
| unsubscribed_at | TIMESTAMPTZ | | Migration 021 |
| custom_fields | JSONB | | Migration 048 |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | |

### `conversations`
Chat sessions with the widget.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| client_id | UUID | FK → tenants.id, NOT NULL | **NOT tenant_id** |
| session_id | TEXT | NOT NULL | |
| messages | JSONB | | Array of message objects |
| lead_id | UUID | FK → leads.id | |
| lead_captured | BOOLEAN | DEFAULT false | Migration 074 |
| channel | TEXT | DEFAULT 'widget' | |
| started_at | TIMESTAMPTZ | DEFAULT NOW() | |
| last_message_at | TIMESTAMPTZ | | |

### `faq_entries`
Per-tenant FAQ for the AI assistant.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| tenant_id | UUID | FK → tenants.id, NOT NULL | |
| question | TEXT | NOT NULL | |
| answer | TEXT | NOT NULL | |
| category | TEXT | DEFAULT 'General' | |
| is_active | BOOLEAN | DEFAULT true | |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | |

### `team_members`
Team member accounts for a tenant.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| tenant_id | UUID | FK → tenants.id, NOT NULL | |
| email | TEXT | NOT NULL | |
| name | TEXT | | |
| role | TEXT | DEFAULT 'member' | owner/admin/member |
| password_hash | TEXT | | |
| invite_accepted | BOOLEAN | DEFAULT false | |
| last_login | TIMESTAMPTZ | | |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | |

### `tenant_ai_usage_monthly`
Monthly DB-backed AI usage ledger used before widget Claude calls.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| tenant_id | UUID | FK -> tenants.id, PK | |
| period_month | DATE | PK | First day of UTC month |
| input_tokens | INTEGER | DEFAULT 0 | |
| output_tokens | INTEGER | DEFAULT 0 | |
| cache_creation_input_tokens | INTEGER | DEFAULT 0 | |
| cache_read_input_tokens | INTEGER | DEFAULT 0 | |
| reserved_tokens | INTEGER | DEFAULT 0 | Pre-call reservations for multi-worker safety |
| call_count | INTEGER | DEFAULT 0 | |
| blocked_count | INTEGER | DEFAULT 0 | |
| alert_sent_at | TIMESTAMPTZ | | |
| hard_blocked_at | TIMESTAMPTZ | | |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | |

### `billing_refunds`
Admin audit trail for Stripe refunds.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| tenant_id | UUID | FK -> tenants.id | |
| stripe_refund_id | TEXT | UNIQUE, NOT NULL | |
| stripe_payment_intent_id | TEXT | | |
| stripe_charge_id | TEXT | | |
| amount_cents | INTEGER | | |
| currency | TEXT | DEFAULT 'usd' | |
| stripe_reason | TEXT | | Stripe refund reason |
| internal_reason | TEXT | NOT NULL | |
| requested_by | TEXT | NOT NULL | |
| status | TEXT | DEFAULT 'pending' | |
| raw_refund | JSONB | DEFAULT '{}' | Sanitized Stripe response |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | |

### `tenant_cancellation_events`
Historical cancellation reason records.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| tenant_id | UUID | FK -> tenants.id | |
| stripe_subscription_id | TEXT | | |
| plan | TEXT | | |
| reason | TEXT | NOT NULL | |
| reason_detail | TEXT | | |
| feedback | TEXT | | |
| current_period_end | TIMESTAMPTZ | | |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | |

### `billing_dunning_events`
Failed-payment notices generated from Stripe `invoice.payment_failed`.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| tenant_id | UUID | FK -> tenants.id | |
| stripe_invoice_id | TEXT | NOT NULL | |
| stripe_subscription_id | TEXT | | |
| stripe_customer_id | TEXT | | |
| attempt_count | INTEGER | DEFAULT 0 | |
| next_payment_attempt | TIMESTAMPTZ | | |
| amount_due_cents | INTEGER | | |
| currency | TEXT | DEFAULT 'usd' | |
| hosted_invoice_url | TEXT | | |
| invoice_pdf | TEXT | | |
| email_sent | BOOLEAN | DEFAULT false | |
| email_detail | TEXT | | |
| raw_invoice | JSONB | DEFAULT '{}' | Sanitized Stripe invoice snapshot |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | |

---

## Key Naming Conventions

| Concept | Column Name | Table | Avoid |
|---------|-------------|-------|-------|
| Tenant FK in leads/conversations | `client_id` | leads, conversations | ~~`tenant_id`~~ |
| Tenant FK in other tables | `tenant_id` | faq_entries, widget_configs, etc. | |
| Lead status | `status` | leads | ~~`lead_stage`~~ |
| Service interest | `areas_of_interest` | leads | ~~`service_interest`~~ |
| Widget API key | `api_key` | widget_configs | |

---

## Migration History Notes

- **001-003:** Historical baseline; later migrations reconcile legacy column names.
- **076:** Fixed `conversations.client_id` FK to point to `tenants.id` instead of `clients.id`.
- **094:** Reconciled 8 ad-hoc columns on `leads` that existed in production but had no migration.
- **096:** Makes `client_id` reconciliation fresh-deploy safe and adds DB-backed automation/email quota locks.
- **106:** Adds AI usage caps, refund audit trail, cancel reasons, and dunning logs.

---

## Row Level Security (RLS)

All tables have RLS enabled. Policies enforce tenant isolation:
- `tenants`: Users can only read/update their own tenant record
- `leads`: Users can only access leads where `client_id = current_tenant_id`
- `conversations`: Users can only access conversations where `client_id = current_tenant_id`
- `widget_configs`: Users can only access their own widget config
- See migration 091/093 for full RLS policy definitions
