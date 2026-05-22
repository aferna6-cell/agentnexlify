# AgentNexLiFy Comprehensive Codebase Audit v2

**Date:** 2026-03-02
**Auditor:** Claude Opus 4.6 (comprehensive re-audit)
**Scope:** Full codebase — schema integrity, error handling, JWT staleness, route health, env vars

---

## Executive Summary

The codebase has a **fundamental architectural split**: TWO parallel database schemas are both actively used by different parts of the code. This is the root cause of most bugs. The prior audit (commit `8051466`) documented fixes but many were NOT actually applied — the issues persist.

| Severity | Count |
|----------|-------|
| CRITICAL | 12 |
| HIGH     | 16 |
| MEDIUM   | 11 |
| LOW      | 7 |
| **Total** | **46** |

### The Two Schemas

**OLD Schema** (`backend/models/tables.sql`) — Single-tenant real estate chatbot:
- Tables: `clients`, `leads` (with `client_id`, `status`, `lead_type`, `lead_temperature`, `pre_approved`, etc.), `conversations` (with `client_id`, `channel`, `status`), `messages` (separate table)

**MIGRATION Schema** (`migrations/001+002`) — Multi-tenant SaaS:
- Tables: `tenants`, `widget_configs`, `leads` (with `tenant_id`, `lead_stage`, `service_interest`, `source`, `notes`), `conversations` (with `tenant_id`, `messages` JSONB), `faq_entries`, `automations`

**Files using OLD schema:** `chat.py`, `webhooks.py`, `clients.py`, `signup.py`, `conversation.py`, `claude_agent.py`, `tool_handlers.py`
**Files using MIGRATION schema:** `auth.py`, `billing.py`, `widget.py`, `leads.py`, `automations.py`

### MIGRATION Schema Column Reference

| Table | Columns |
|-------|---------|
| **tenants** | id, business_name, business_type, owner_email, phone, city, plan, plan_status, stripe_customer_id, stripe_subscription_id, monthly_conversation_limit, conversations_used_this_month, reset_date, referral_code, referred_by, referral_discount_pct, password_hash*, owner_name*, created_at, updated_at |
| **widget_configs** | id, tenant_id, api_key (TEXT), bot_name, primary_color, greeting_message, position, collect_name, collect_email, collect_phone, show_watermark, custom_css, allowed_domains, created_at |
| **leads** | id, tenant_id, name, email, phone, service_interest, budget, timeline, lead_score, lead_stage, source, conversation_id, notes, created_at |
| **conversations** | id, tenant_id, session_id, messages (JSONB), lead_id, started_at, last_message_at |
| **faq_entries** | id, tenant_id, question, answer, category, is_active, created_at |
| **automations** | id, tenant_id, type, name, is_enabled, config (JSONB), runs_total, created_at |

*Added by migration 002

---

## 1. Stale Schema / Column Mismatch Issues

| # | Severity | File | Line(s) | Issue | Expected (MIGRATION) |
|---|----------|------|---------|-------|----------------------|
| 1.1 | **CRITICAL** | `backend/tools/tool_handlers.py` | 133 | `_handle_log_lead` uses `client_id` | Should be `tenant_id` |
| 1.2 | **CRITICAL** | `backend/tools/tool_handlers.py` | 138-145 | Writes `lead_type`, `pre_approved`, `areas_of_interest`, `must_haves`, `lead_temperature`, `conversation_summary`, `next_steps`, `updated_at` to leads | None of these columns exist. Should use: `service_interest`, `lead_stage`, `source`, `notes` |
| 1.3 | **CRITICAL** | `backend/tools/tool_handlers.py` | 48 | `_handle_book_appointment` sets `tenant_id = client.id` where client is `ClientRow` (from `clients` table) | FK mismatch: `clients.id` ≠ `tenants.id` |
| 1.4 | **HIGH** | `backend/routers/chat.py` | 20-32 | Queries `clients` table with `widget_api_key` | Multi-tenant uses `widget_configs.api_key` |
| 1.5 | **HIGH** | `backend/routers/chat.py` | 59 | `.eq("client_id", client.id)` on conversations | Should be `tenant_id` |
| 1.6 | **HIGH** | `backend/services/conversation.py` | 24, 34, 49-55, 107-113 | Uses `client_id` in conversations + queries `messages` table | `conversations` uses `tenant_id`; messages are JSONB, no `messages` table |
| 1.7 | **HIGH** | `backend/routers/webhooks.py` | 32-38 | Queries `clients.notification_phone` | `clients` table doesn't exist in MIGRATION |
| 1.8 | **HIGH** | `backend/routers/signup.py` | 22-33 | Inserts into `clients` table | Should use `tenants` + `widget_configs` |
| 1.9 | **HIGH** | `backend/routers/clients.py` | 1-68 | Entire file: CRUD on `clients` table | Table doesn't exist in MIGRATION |
| 1.10 | **MEDIUM** | `frontend/.../LeadPipeline.jsx` | 41, 44, 58 | References `lead.lead_type`, `lead.areas_of_interest`, `lead.lead_temperature` | Don't exist in MIGRATION leads — always undefined |
| 1.11 | **MEDIUM** | `frontend/.../LeadDetailDrawer.jsx` | 27-133 | References `lead_temperature`, `lead_type`, `areas_of_interest`, `must_haves`, `pre_approved`, `conversation_summary`, `next_steps`, `appointment_date`, `status` | None exist in MIGRATION leads |
| 1.12 | **LOW** | `frontend/.../LeadDetailDrawer.jsx` | 29 | Score display: `/ 100` | Should be `/ 10` (lead_score range is 1-10) |
| 1.13 | **LOW** | `scripts/setup_supabase.py` | 36 | Tests with `clients` table | Should use `tenants` |
| 1.14 | **LOW** | `backend/models/schemas.py` | 133-148 | `ClientRow` model for OLD schema `clients` table | Unused by MIGRATION system |

---

## 2. Silent Error Swallowing Issues

| # | Severity | File | Line(s) | Issue | Fix |
|---|----------|------|---------|-------|-----|
| 2.1 | **CRITICAL** | `backend/routers/billing.py` | 131-134 | Stripe webhook catches all errors, returns HTTP 200. Stripe won't retry | Return 500 for retriable errors |
| 2.2 | **CRITICAL** | `backend/routers/stripe_webhooks.py` | 61-63 | Same as 2.1 (duplicate endpoint) | Return 500 |
| 2.3 | **HIGH** | `backend/routers/widget.py` | 265-270 | Anthropic API failure returns fake success message with 200 | At minimum log and flag in response |
| 2.4 | **HIGH** | `backend/routers/widget.py` | 274-279 | Conversation save failure: messages lost silently | Log error, don't swallow |
| 2.5 | **HIGH** | `backend/routers/widget.py` | 100-102 | `_get_or_create_conversation` returns fake in-memory conversation on ANY error | Masks DB connection failures |
| 2.6 | **HIGH** | `backend/routers/leads.py` | 32-34 | `get_leads` returns `{"leads": []}` on error | Return 500 |
| 2.7 | **HIGH** | `backend/routers/leads.py` | 59-61 | `get_lead_summary` returns zeros on error | Return 500 |
| 2.8 | **MEDIUM** | `backend/routers/widget.py` | 225-226 | Usage counter increment failure silent | Tenant gets unlimited free conversations |
| 2.9 | **MEDIUM** | `backend/routers/widget.py` | 243-244 | FAQ query failure silent | Bot lacks FAQ knowledge |
| 2.10 | **MEDIUM** | `backend/routers/widget.py` | 286-287 | Lead extraction failure silent | Lead data permanently lost |
| 2.11 | **MEDIUM** | `backend/routers/auth.py` | 235-245 | Dashboard leads count defaults to 0 on error | Has logger.warning but client unaware |
| 2.12 | **MEDIUM** | `demo-platform/server/app.py` | 89-90 | `{"error": str(e)}` with HTTP 200 | Return proper status code |
| 2.13 | **MEDIUM** | `backend/services/notifications.py` | 57-58, 87-88 | Email/SMS failures swallowed by callers | Hot lead alerts silently vanish |

---

## 3. JWT / Stale Data Issues

| # | Severity | File | Line(s) | Issue | Fix |
|---|----------|------|---------|-------|-----|
| 3.1 | **CRITICAL** | `frontend/.../AuthContext.jsx` | 33-38 | Reads `plan` from JWT payload. After Stripe upgrade, JWT still has old plan for up to 7 days | Fetch `/me` on mount |
| 3.2 | **CRITICAL** | `backend/routers/auth.py` | 43-57 | Bakes `plan` + `business_name` into JWT. No refresh mechanism | Add `/me` data to AuthContext |
| 3.3 | **HIGH** | `frontend/.../Sidebar.jsx` | 24 | Falls back to JWT `user.plan` before Dashboard API loads | Use live API data |
| 3.4 | **MEDIUM** | `frontend/.../AuthContext.jsx` | 36 | Default plan `"starter"` — not a valid plan name | Should be `"free"` |
| 3.5 | **MEDIUM** | `frontend/.../SignupPage.jsx` | 68-70 | Bypasses `useAuth().login()`, sets localStorage directly + full page reload | Use AuthContext |
| 3.6 | **MEDIUM** | `backend/routers/auth.py` | 29 | 7-day JWT, no refresh endpoint | Add token refresh |

---

## 4. API Route Health Check Issues

| # | Severity | File | Line(s) | Issue | Fix |
|---|----------|------|---------|-------|-----|
| 4.1 | **CRITICAL** | `backend/routers/automations.py` | 202, 216, 241 | `list_automations`, `toggle_automation`, `update_automation_config` have NO auth. IDOR vulnerability | Add JWT auth + tenant_id verification |
| 4.2 | **HIGH** | `frontend/src/utils/api.js` | 44 | `fetchActivity` calls `/api/v1/activity/{tenantId}` — route doesn't exist (always 404) | Remove or build endpoint |
| 4.3 | **HIGH** | `backend/routers/billing.py` | 28-30, 38, 360 | Checkout + portal use `X-Api-Secret` header instead of JWT. Frontend sends Bearer JWT. Billing unreachable from dashboard | Switch to JWT auth |
| 4.4 | **MEDIUM** | `billing.py` + `stripe_webhooks.py` | 98, 28 | Duplicate Stripe webhook endpoints. Double-processing risk | Remove one |
| 4.5 | **MEDIUM** | `backend/routers/billing.py` | 109-113 | `except (stripe.SignatureVerificationError, Exception)` catches everything | Narrow exception handling |
| 4.6 | **MEDIUM** | `backend/routers/widget.py` | 277 | `"last_message_at": "now()"` stores literal string, not timestamp | Use ISO timestamp |
| 4.7 | **MEDIUM** | `backend/routers/automations.py` | 242 | `config: dict` accepts arbitrary JSON, no validation | Add schema validation |
| 4.8 | **LOW** | `frontend/src/utils/api.js` | 48 | `fetchWidgetConfig` → non-existent `/api/v1/widget-config/` | Remove dead function |
| 4.9 | **LOW** | `frontend/src/utils/api.js` | 52 | `fetchUsage` → non-existent `/api/v1/usage/` | Remove dead function |

---

## 5. Environment Variable Issues

| # | Severity | File | Line(s) | Issue | Fix |
|---|----------|------|---------|-------|-----|
| 5.1 | **CRITICAL** | `backend/config.py` | 29 | `api_secret_key = secrets.token_urlsafe(32)` — regenerates on every restart. Invalidates ALL JWTs on deploy | Require in `.env`, fail fast |
| 5.2 | **HIGH** | `frontend/.../LoginPage.jsx` | 18-19 | `console.log('API URL:')` — debug logging in production | Remove |
| 5.3 | **HIGH** | `frontend/.../SignupPage.jsx` | 20 | `console.log('ENV:')` — same | Remove |
| 5.4 | **MEDIUM** | `.env.example` | — | `VITE_API_BASE_URL` not documented | Add to example |
| 5.5 | **MEDIUM** | `backend/services/stripe_service.py` | 15-23 | Stripe price IDs are placeholders (`"price_foundation_setup"`) | Needs real Stripe price IDs |
| 5.6 | **LOW** | `backend/config.py` | 28 | `WIDGET_ALLOWED_ORIGINS` defaults to `*` | Restrict in production |
| 5.7 | **LOW** | `demo-platform/server/app.py` | 41 | `ALLOWED_ORIGINS` not documented | Add to example |

---

## Environment Variables Checklist

| Variable | Required? | Sensitive? | Default | Notes |
|----------|-----------|------------|---------|-------|
| `ANTHROPIC_API_KEY` | Yes | Yes | `""` | AI chat won't work |
| `SUPABASE_URL` | Yes | No | `""` | |
| `SUPABASE_KEY` | Yes | Yes | `""` | Anon/public key |
| `SUPABASE_SERVICE_KEY` | Yes | **NEVER expose** | `""` | Full DB access |
| `API_SECRET_KEY` | **MUST SET** | **Yes** | Random/restart | JWT signing — BUG if unset |
| `STRIPE_SECRET_KEY` | Billing | **Yes** | `""` | |
| `STRIPE_WEBHOOK_SECRET` | Billing | **Yes** | `""` | |
| `FRONTEND_URL` | Yes | No | `localhost:5173` | Stripe redirects |
| `TWILIO_ACCOUNT_SID` | SMS | Yes | `""` | |
| `TWILIO_AUTH_TOKEN` | SMS | **Yes** | `""` | |
| `TWILIO_PHONE_NUMBER` | SMS | No | `""` | E.164 format |
| `SMTP_HOST` | Email | No | `smtp.gmail.com` | |
| `SMTP_PORT` | Email | No | `587` | |
| `SMTP_USER` | Email | No | `""` | |
| `SMTP_PASS` | Email | **Yes** | `""` | |
| `VITE_API_BASE_URL` | Frontend | No | Railway URL | **Not documented** |

**Security:** No sensitive keys exposed to frontend. `SUPABASE_SERVICE_KEY` server-side only.

---

## Fixes To Apply

| # | File | Fix |
|---|------|-----|
| F1 | `tool_handlers.py` | Fix `_handle_log_lead`: `client_id` → `tenant_id`, map old columns to MIGRATION |
| F2 | `tool_handlers.py` | Fix `_handle_book_appointment`: consistent FK |
| F3 | `leads.py` | Return 500 on DB errors, not empty arrays |
| F4 | `automations.py` | Add JWT auth to all 3 unprotected routes |
| F5 | `billing.py` | Return 500 on webhook handler failure |
| F6 | `stripe_webhooks.py` | Same as F5 |
| F7 | `billing.py` | Switch checkout/portal from X-Api-Secret to JWT |
| F8 | `AuthContext.jsx` | Fetch `/me` on mount for live plan data |
| F9 | `AuthContext.jsx` | Fix "starter" fallback to "free" |
| F10 | `LeadPipeline.jsx` | Use MIGRATION schema columns |
| F11 | `LeadDetailDrawer.jsx` | Use MIGRATION schema columns, fix "/ 100" |
| F12 | `LoginPage.jsx` | Remove console.log |
| F13 | `SignupPage.jsx` | Remove console.log, use AuthContext properly |
| F14 | `api.js` | Remove non-existent endpoint functions |
| F15 | `widget.py` | Fix `last_message_at` timestamp |
| F16 | `config.py` | Fail fast if API_SECRET_KEY unset |

## Manual Attention Required

| # | Issue | Action |
|---|-------|--------|
| M1 | **Schema fate decision.** OLD-schema files (chat.py, webhooks.py, clients.py, signup.py, conversation.py, claude_agent.py) need rewrite or removal | Architecture decision |
| M2 | **Stripe price IDs are placeholders** | Create real prices in Stripe Dashboard |
| M3 | **API_SECRET_KEY in production** | Verify it's set in prod `.env` |
| M4 | **Duplicate webhook endpoints** | Pick one, remove the other |
| M5 | **No activity endpoint** | Build it or remove from frontend |
| M6 | **Old routes still mounted** in main.py | Remove when ready |
| M7 | **VITE_API_BASE_URL** | Add to `.env.example` |
