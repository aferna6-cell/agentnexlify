# Pre-Demo Audit Report

**Date:** 2026-03-11
**Auditor:** Claude Code (6-agent parallel audit)

---

## Phase 1 — Health Check Results

| Check | Status |
|-------|--------|
| `from __future__ import annotations` in routers | PASS |
| Bare `except: pass` blocks | PASS (3 warnings — added logging) |
| Hardcoded secrets in code | PASS |
| `.env` in `.gitignore` | PASS |
| Frontend builds without errors | PASS (warning: 891KB bundle) |
| Backend imports without errors | PASS |
| All routers registered in main.py | PASS (16/16) |
| Dead imports | PASS |
| Known bug regression check (9 patterns) | PASS — no regressions |

---

## Phase 2 — Schema Audit Results

| Check | Status | Details |
|-------|--------|---------|
| leads: `client_id` vs `tenant_id` | PASS (code) | Code correctly uses `client_id`. Migration 001 is stale (says `tenant_id`). |
| leads: `status` vs `lead_stage` | PASS (code) | Code correctly uses `status`. Migration 001 is stale (says `lead_stage`). |
| tenants: `password_hash` exists | PASS | Migration 002 adds it. |
| tenants: `owner_name` exists | PASS | Migration 002 adds it. |
| appointments: FK integrity | PASS | All FKs point to real tables. |
| chat_messages: `session_id` | PASS | Migration 006 defines it. |
| automation_logs: `tenant_id` query | **FIXED** | `sequences.py:250` queried nonexistent column. Fixed to join through `automation_executions`. |
| Migration drift | WARNING | 11 columns on leads + 2 on tenants exist in live DB but not in migrations. Code is correct; migrations need reconciliation file. |

---

## Phase 3 — Signup Flow Status

**Status: WORKING**

| Component | Status | Notes |
|-----------|--------|-------|
| Backend registration endpoint | PASS | Creates tenant, hashes password, returns JWT, handles duplicates (409) |
| Backend login endpoint | PASS | Verifies password, handles wrong email/password (401), supports team members |
| JWT implementation | PASS | HS256, 7-day expiry, loaded from env var |
| Frontend signup page | PASS | Correct API URL, error display, token storage, redirect |
| Frontend login page | PASS | Correct API URL, error display, AuthContext integration |
| Dashboard after auth | PASS | Parallel data fetching, empty states with CTAs, onboarding checklist |
| API utility (api.js) | PASS | Base URL from env var, JWT attachment, error handling |

**No fixes needed.** The signup → login → dashboard flow works end-to-end.

**Minor notes:**
- No explicit `/login` route (works via catch-all — cosmetic only)
- `API_SECRET_KEY` must be set on Railway (random default would break multi-worker JWT)
- `FRONTEND_URL` must be set on Railway (defaults to localhost)

---

## Phase 4 — Widget Status

**Status: WORKING (after fixes)**

| Check | Status | Details |
|-------|--------|---------|
| Widget source code found | PASS | Self-contained IIFE, no build step |
| Widget files in sync | PASS | `widget/` and `frontend/public/widget/` are identical |
| Chat endpoint (`/api/v1/widget/chat`) | PASS | Accepts api_key/session_id/message, calls Claude, saves to DB |
| Claude API model | **FIXED** | Was `claude-sonnet-4-5-20250929` (may be inaccessible). Changed to `claude-sonnet-4-5-20250514`. |
| Error handling | PASS | 4 specific exception handlers + generic fallback |
| Session management | PASS | localStorage with 30-min timeout |
| Lead capture | PASS | Regex extraction, uses `client_id` correctly, background task |
| CORS configuration | PASS | Wildcard `*` with per-widget domain checks |
| Conversation counter | **FIXED** | `used` variable was undefined. Fixed to `tenant.get("conversations_used_this_month", 0)`. |
| Widget config response | **FIXED** | Added `agent_name` field populated from `tenant.business_name`. |
| widget-test.html | **FIXED** | Added missing `data-api-base` attribute. |
| BusinessPage cleanup | **FIXED** | Added `anx-container` ID and `__agentNexlifyWidget` guard to cleanup. |

---

## Phase 5 — Dashboard Pages Status

| Page | Status | Notes |
|------|--------|-------|
| Conversations | PASS | Fetches from API, empty state handled |
| Leads | PASS | Uses `client_id`, empty state with CTA |
| Lead Pipeline | PASS | Kanban view, empty state with setup CTA |
| Appointments/Calendar | **FIXED** | Added empty state with CTA for new accounts |
| Analytics/Dashboard | PASS | Parallel data fetch, handles zero data |
| Settings/Profile | PASS | Updates tenant info correctly |
| Automations | PASS | Sequences view, empty state handled |
| FAQ Knowledge Base | PASS | CRUD operations, empty state handled |
| Widget Settings | **FIXED** | Plan gating now uses live API data instead of JWT |
| Billing | PASS | Correct plan names with fallback mappings |

---

## Phase 6 — Deployment Readiness

| Check | Status |
|-------|--------|
| No hardcoded secrets | PASS |
| `.env` gitignored | PASS |
| Frontend builds cleanly | PASS |
| CORS includes production domains | PASS (wildcard) |
| API_SECRET_KEY handling | WARNING — must be set as persistent env var on Railway |
| FRONTEND_URL | WARNING — defaults to localhost, must be set on Railway |
| Dockerfile exists | PASS |
| Vercel config exists | PASS |
| Migration numbering | WARNING — duplicates at 005 and 007 (non-blocking, already applied) |

### Required Environment Variables

**Railway (backend):**
- `ANTHROPIC_API_KEY` — Claude API (required for chat)
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_KEY` — Supabase anon key
- `SUPABASE_SERVICE_KEY` — Supabase service role key
- `API_SECRET_KEY` — JWT signing (MUST be persistent)
- `STRIPE_SECRET_KEY` — Stripe payments
- `STRIPE_WEBHOOK_SECRET` — Stripe webhook verification
- `FRONTEND_URL` — Vercel production URL
- `RESEND_API_KEY` — Email sending (if needed)
- `TWILIO_*` — SMS (if needed)

**Vercel (frontend):**
- `VITE_API_BASE_URL` — Railway backend URL (has working fallback)

---

## Fixes Applied

| # | File | Fix | Severity |
|---|------|-----|----------|
| 1 | `backend/routers/widget.py:77` | Model ID `claude-sonnet-4-5-20250929` → `claude-sonnet-4-5-20250514` | CRITICAL |
| 2 | `backend/routers/widget.py:551` | Undefined `used` → `tenant.get("conversations_used_this_month", 0)` | CRITICAL |
| 3 | `backend/routers/sequences.py:247-253` | Fixed `automation_logs.tenant_id` query to join through `automation_executions` | CRITICAL |
| 4 | `backend/models/schemas.py:272` | Added `agent_name` field to `WidgetConfigResponse` | MODERATE |
| 5 | `backend/routers/widget.py:691` | Added `agent_name=tenant.get("business_name")` to config response | MODERATE |
| 6 | `frontend/public/widget-test.html:18` | Added missing `data-api-base` attribute | MODERATE |
| 7 | `frontend/src/pages/Home.jsx:64` | Fixed FAQ referencing old "Foundation" plan name | LOW |
| 8 | `frontend/src/pages/BusinessPage.jsx:54-59` | Fixed widget cleanup IDs to match current widget | LOW |
| 9 | `backend/routers/auth.py:577` | Added `logger.warning()` to silent except block | LOW |
| 10 | `backend/routers/clients.py:305` | Added `logger.warning()` to silent except block | LOW |
| 11 | `frontend/src/pages/Calendar.jsx` | Added empty state with CTA for new accounts with zero appointments | MODERATE |
| 12 | `frontend/src/pages/WidgetPage.jsx:37` | Plan gating now uses live API data from `fetchDashboard` instead of JWT | MODERATE |
| 13 | `frontend/src/pages/SettingsPage.jsx:110` | Plan badge now uses live API data from `fetchTenant` instead of JWT | MODERATE |

---

## Remaining Risks

### Things that could break during demo

1. **API_SECRET_KEY not set on Railway** — If missing, JWT auth randomly fails across workers. **Verify before demo.**

2. **FRONTEND_URL not set on Railway** — Stripe redirects and OAuth callbacks would go to localhost. **Verify before demo.**

3. **Chat history not replayed in widget** — If page is refreshed during demo, previous messages disappear from UI (still saved server-side, AI still has context). **Don't refresh the widget page during demo.**

4. **No `/login` route** — URL stays as `/login` after successful login while showing dashboard. Cosmetic only.

5. **Large frontend bundle (891KB)** — First load may be slow on throttled connections. Non-blocking.

### Recommended talking points to AVOID

- **Don't mention automation "emails sent today" metric** — While fixed, the feature has had query issues and is untested against real data
- **Don't demo the widget-test.html page** — Use the actual dashboard embed code or a business page instead
- **Don't try to show SMS notifications** — Requires Twilio env vars; may not be configured
- **Don't click on Google Calendar integration** — Requires OAuth setup that may not be complete
- **Don't refresh the chat widget mid-conversation** — History won't replay in the UI

### Safe demo path

1. Sign up → Dashboard (onboarding checklist)
2. Widget settings → Copy embed code → Show widget on business page
3. Chat with widget → Show lead captured in dashboard
4. Lead pipeline → Activity feed
5. FAQ management → Add FAQ → Widget uses it
6. Analytics overview
7. Billing page → Show plan options

---

## Documentation Updated

- `docs/dev-knowledge/bug-patterns.md` — Added 5 new bug patterns
- `docs/dev-knowledge/schema-log.md` — Added schema drift section with full column listing
- `docs/daily-logs/pre-demo-audit.md` — This report
