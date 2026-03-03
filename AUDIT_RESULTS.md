# AgentNexLiFy Codebase Audit Results

**Date:** 2026-03-02
**Scope:** Full backend + frontend audit — schema mismatches, error handling, JWT staleness, env vars

---

## Executive Summary

The codebase has two generations of code mixed together:
1. **Old single-tenant** code (real estate agent chatbot): uses `clients` table, `messages` table, `client_id` FK
2. **New multi-tenant SaaS** code (AgentNexLiFy): uses `tenants` table, JSONB messages, `tenant_id` FK

The old code was never fully migrated. Several routers and services still reference tables/columns that don't exist in the current schema.

---

## 1. Schema Mismatch Issues

### Actual Schema (from migrations/001_initial_schema.sql)

| Table | Columns |
|-------|---------|
| **tenants** | id, business_name, business_type, owner_email, phone, city, plan, plan_status, stripe_customer_id, stripe_subscription_id, monthly_conversation_limit, conversations_used_this_month, reset_date, referral_code, referred_by, referral_discount_pct, created_at, updated_at |
| **widget_configs** | id, tenant_id, api_key, bot_name, primary_color, greeting_message, position, show_watermark, allowed_domains, created_at |
| **leads** | id, tenant_id, name, email, phone, service_interest, budget, timeline, lead_score, lead_stage, source, conversation_id, notes, created_at |
| **conversations** | id, tenant_id, session_id, messages (JSONB), lead_id, started_at, last_message_at |
| **faq_entries** | id, tenant_id, question, answer, is_active, sort_order, created_at |
| **automations** | id, tenant_id, type, is_enabled, config (JSONB), last_triggered_at, trigger_count, created_at |

**Tables that DO NOT exist:** `clients`, `messages`

### Critical Mismatches Found

| # | Severity | File | Line(s) | Issue | Schema Reality |
|---|----------|------|---------|-------|----------------|
| 1 | CRITICAL | backend/routers/clients.py | All | Entire file queries `clients` table | Table doesn't exist |
| 2 | CRITICAL | backend/routers/signup.py | 33, 68, 95 | Queries `clients` table | Table doesn't exist |
| 3 | CRITICAL | backend/routers/chat.py | 23, 56 | Queries `clients` table, `client_id` | Table doesn't exist |
| 4 | CRITICAL | backend/routers/webhooks.py | 33 | Queries `clients` table | Table doesn't exist |
| 5 | CRITICAL | backend/services/conversation.py | 21-40 | Uses `client_id`, `status`, `channel` on conversations | Should be `tenant_id`; no `status`/`channel` columns |
| 6 | CRITICAL | backend/services/conversation.py | 51, 113, 127 | Queries `messages` table | Table doesn't exist; messages are JSONB in conversations |
| 7 | CRITICAL | backend/routers/auth.py | 95-98 | Inserts `password_hash`, `owner_name` into tenants | Columns don't exist in schema |
| 8 | CRITICAL | backend/routers/auth.py | 129-132 | Selects `password_hash` from tenants | Column doesn't exist |
| 9 | CRITICAL | backend/tools/tool_handlers.py | 113, 133-145 | Queries `messages` table; uses `lead_type`, `pre_approved`, `areas_of_interest`, `must_haves`, `lead_temperature`, `conversation_summary`, `next_steps` | `messages` table doesn't exist; those lead columns don't exist |
| 10 | MODERATE | backend/models/schemas.py | 233-254 | `LeadRow` model has `client_id`, `lead_temperature`, `status`, `appointment_date` | Already fixed |
| 11 | MODERATE | backend/models/schemas.py | ~260 | `ClientRow` model for non-existent `clients` table | Table doesn't exist |

### Notes on Issues 7-8 (password_hash, owner_name)

These columns may have been added to the live Supabase database manually (outside migrations), because auth registration and login are reportedly working. **Do NOT remove these from code** — they match the live DB even if not in the migration file. The migration file is likely out of date.

---

## 2. Silent Error Handling Issues

| # | Severity | File | Line(s) | Issue |
|---|----------|------|---------|-------|
| 1 | CRITICAL | backend/routers/billing.py | 120-134 | Stripe webhook catches all exceptions, returns 200 — Stripe won't retry failed plan upgrades |
| 2 | CRITICAL | backend/services/conversation.py | 39-40 | `result.data[0]` with no null check — crashes if insert fails |
| 3 | CRITICAL | backend/services/conversation.py | 106-118 | Messages table insert with no error handling |
| 4 | CRITICAL | backend/routers/automations.py | 112, 182, 190 | SMS send result never checked — missed-call textback silently fails |
| 5 | MODERATE | backend/main.py | 103-109 | Global error handler catches HTTPException, returns 500 for all |
| 6 | MODERATE | backend/services/stripe_service.py | 48-61 | Stripe Customer.search/create with no try/except |
| 7 | LOW | backend/services/notifications.py | 30-34 | Logs full message body when SMTP not configured |

---

## 3. JWT / Stale Data Issues

| # | Severity | File | Line(s) | Issue |
|---|----------|------|---------|-------|
| 1 | HIGH | frontend/src/context/AuthContext.jsx | All | No JWT refresh mechanism. Token valid for 7 days with stale claims. After Stripe upgrade, plan in JWT stays "free" |
| 2 | MEDIUM | frontend/src/components/Sidebar.jsx | 46 | Business name from JWT, never refreshed after profile changes |
| 3 | LOW | frontend/src/pages/Dashboard/index.jsx | 85 | Plan falls back to stale JWT if API call fails (acceptable fallback) |

---

## 4. Environment Variable Issues

| # | Severity | Issue |
|---|----------|-------|
| 1 | CRITICAL | `api_secret_key` in config.py regenerates on every restart — invalidates all JWTs and forces re-login on every deploy |
| 2 | CRITICAL | .env file contains live Anthropic + Supabase keys — should be in .gitignore |
| 3 | HIGH | Stripe keys (STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET) missing from .env — Stripe calls fail with empty string |
| 4 | MODERATE | All critical env vars default to "" — app starts successfully but fails at runtime |

---

## 5. Fixes Applied in This Audit

### Fix 1: Global error handler — don't swallow HTTPException
**File:** backend/main.py — APPLIED
- Re-raises HTTPException so FastAPI returns proper 4xx status codes

### Fix 2: Remove dead single-tenant router registrations
**File:** backend/main.py — APPLIED
- Removed imports + registrations for: clients, signup, chat, webhooks
- Moved rate limiter creation to main.py (was imported from chat.py)
- Active routers: auth, automations, billing, leads, stripe_webhooks, widget

### Fix 3: tool_handlers.py — remove non-existent lead columns
**File:** backend/tools/tool_handlers.py — APPLIED
- `client_id` → `tenant_id`
- Removed non-existent columns: lead_type, pre_approved, areas_of_interest, must_haves, lead_temperature, conversation_summary, next_steps
- Removed `updated_at` (not in leads schema)
- Fixed hot lead check: uses `lead_score >= 8` instead of `lead_temperature == "hot"`

### Fix 4: conversation.py — rewrite for multi-tenant schema
**File:** backend/services/conversation.py — APPLIED
- `client_id` → `tenant_id`
- Remove `messages` table queries (use JSONB on conversations)
- Remove `status`, `channel` columns
- Add error handling on all DB operations

### Fix 5: Stripe webhook — return 500 on handler failure so Stripe retries
**Files:** backend/routers/billing.py, backend/routers/stripe_webhooks.py — APPLIED

### Fix 6: Clean up obsolete Pydantic models
**File:** backend/models/schemas.py — APPLIED
- Removed `ConversationRow` (had client_id, channel, status — all wrong)
- Removed `MessageRow` (for non-existent messages table)

---

## 6. Issues Requiring Manual Attention

### Must Fix (code changes won't help)
1. **Add .env to .gitignore** — live secrets are in the repo
2. **Set STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET on Railway** — without these, billing is broken
3. **Set a persistent API_SECRET_KEY on Railway** — currently regenerates on every deploy, invalidating all user sessions
4. **Verify tenants table** has `password_hash` and `owner_name` columns in live Supabase — migration file doesn't include them but auth code depends on them

### Old Single-Tenant Code (De-registered, Files Remain on Disk)
These files are no longer imported or registered in main.py but remain on disk for reference:
- `backend/routers/clients.py` — dead code, old single-tenant client management
- `backend/routers/signup.py` — dead code, old single-tenant signup flow
- `backend/routers/chat.py` — dead code, old single-tenant chat (widget.py replaces it)
- `backend/routers/webhooks.py` — Twilio SMS webhook, uses old `clients` table
- `backend/services/claude_agent.py` — old single-tenant AI agent, uses `ClientRow`

These can be safely deleted when ready.
