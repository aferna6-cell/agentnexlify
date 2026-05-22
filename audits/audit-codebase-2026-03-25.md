# AgentNexLiFy — Codebase Audit Report

**Date:** 2026-03-25
**Auditor:** Claude Code (automated)
**Scope:** Full codebase — security, backend, frontend, migrations, tests

---

## Executive Summary

The codebase is generally well-structured with good security fundamentals (bcrypt hashing, Pydantic validation, parameterized queries). However, **3 CRITICAL** and **8 HIGH** severity issues were found that must be addressed before any new feature work.

| Severity | Count | Key Issues |
|----------|-------|------------|
| CRITICAL | 3 | Stripe test mode links, SMS import crash, duplicate migration numbers |
| HIGH | 8 | No forgot password, dead social links, no rate limiting on auth, incomplete RLS, JWT secret per-worker, localStorage tokens, no multi-tenant tests, missing widget API tests |
| MEDIUM | 6 | Wildcard CORS (justified), fake scarcity, raw exception in crawl.py, incomplete Stripe tests, inconsistent test mocking, API key logging |
| LOW | 4 | Missing testimonials, no widget on own site, contact page barebones, industry dropdown limited |
| GOOD | 5 | HTML escaping, SQL injection protection, Pydantic validation, Claude model strings correct, no `__future__` annotations |

---

## Verification Update — 2026-03-25

This report was re-verified against the current repository state after the initial automated pass. Several findings above were already stale by the time of manual verification.

### Re-verified as resolved in the current tree

- Dynamic Stripe Checkout already exists on the production landing page via `frontend/src/pages/Home.jsx` and `backend/routers/auth.py`, and the paid-plan selection now carries through signup before redirecting to Checkout.
- Forgot/reset password already exists in `frontend/src/components/LoginPage.jsx`, `frontend/src/pages/ForgotPasswordPage.jsx`, `frontend/src/pages/ResetPasswordPage.jsx`, and `backend/routers/auth.py`, including 1-hour reset token expiry.
- Auth rate limiting is already applied on register, login, forgot-password, and reset-password routes in `backend/routers/auth.py`.
- The widget handoff SMS path no longer imports a missing module; `backend/routers/widget_chat.py` uses `backend.services.twilio_service.send_sms`.
- The current production `Home.jsx` no longer ships dead social links, fake “10 spots” scarcity copy, or missing testimonials/social-proof.
- The signup industry list is already expanded in `frontend/src/pages/SignupPage.jsx`.
- Dedicated widget API and multi-tenant isolation suites already exist in `tests/test_widget_api.py` and `tests/test_multi_tenant_isolation.py`.

### Verified during this pass

- `pytest -q`: **305 passed**
- `cd frontend && npm run build`: **passed**
- Added/updated test coverage for password reset, authenticated checkout session creation, current appointment overlap behavior, and webhook retry behavior.
- Added a startup warning in `backend/main.py` when `API_SECRET_KEY` is missing so multi-worker JWT invalidation is visible in logs.

### Remaining open gaps after re-verification

- The repository still has **no configured lint command/toolchain**; `npm run lint` fails because no `lint` script exists.
- `API_SECRET_KEY` still falls back to a per-process random value when unset; this is now warned loudly at startup, but production still depends on correct environment configuration.
- `localStorage` remains the SPA auth token store.
- Full RLS verification still requires live Supabase inspection; local code review alone cannot prove production policy coverage.
- Phase 2 UX items still open include demo booking, dogfooding the widget on the marketing site, and Google OAuth signup.

---

## CRITICAL Findings

### C1: Stripe Checkout Links Are TEST MODE
- **Files:** `frontend/src/pages/Home.jsx` (lines 655, 688, 720), `landing-page-v2/index.html` (lines 1493, 1526, 1559, 1592)
- **Impact:** ALL paid plan checkout links point to `buy.stripe.com/test_*`. No real payments can be processed. The entire revenue pipeline is broken.
- **Fix:** Replace static test links with dynamic server-side Stripe Checkout Session creation via `/api/v1/stripe/checkout`.

### C2: SMS Notification Import Crash
- **File:** `backend/routers/widget_chat.py` (line 456)
- **Impact:** Imports `send_sms_notification` from `backend.services.sms` — this module does not exist. Will raise `ModuleNotFoundError` at runtime when SMS notifications are triggered. Additionally, the function is async but called without `await`.
- **Fix:** Import from `backend.services.twilio_service` and use `background_tasks.add_task()` for the async call.

### C3: Duplicate Migration Numbers
- **Files:** `migrations/005_appointments.sql` + `migrations/005_automation_sequences.sql` (2 files share number 005), `migrations/007_google_calendar_integration.sql` + `migrations/007_team_members.sql` + `migrations/007_webhooks.sql` (3 files share number 007)
- **Impact:** If migrations are applied by number alone, only one file per number executes, leaving tables missing.
- **Note:** These are historical and likely already applied manually. Document for future reference but do not renumber (would break applied migration tracking).

---

## HIGH Findings

### H1: No "Forgot Password" Feature
- **Files:** `frontend/src/components/LoginPage.jsx`, no `ForgotPassword` page exists
- **Impact:** Business owners who forget passwords are completely locked out. No password reset flow exists in backend or frontend.
- **Fix:** Create forgot password page, backend endpoint for reset token generation (via Resend email), and password reset endpoint.

### H2: Dead Social Media Links
- **Files:** `Home.jsx` (lines 828, 833), `FreeWidget.jsx` (lines 394-395, 402, 405), `ComparisonPage.jsx` (lines 305, 308)
- **Impact:** Twitter/X and LinkedIn links point to `href="#"`. Looks broken and unprofessional.
- **Fix:** Remove links until real social profiles exist, or link to real profiles.

### H3: No Rate Limiting on Auth Endpoints
- **File:** `backend/routers/auth.py`
- **Impact:** Login and register endpoints have no rate limiting. Vulnerable to brute force and credential stuffing attacks.
- **Fix:** Add `@limiter.limit("5/minute")` to login, `@limiter.limit("3/minute")` to register.

### H4: Incomplete RLS Policies
- **Files:** Multiple migration files
- **Impact:** Some tables have RLS enabled but no policies defined (activity_log, client_notes). Data may be exposed.
- **Fix:** Verify all RLS-enabled tables have appropriate SELECT/INSERT/UPDATE/DELETE policies.

### H5: JWT Secret Regenerated Per Startup
- **File:** `backend/config.py` (line 31)
- **Impact:** `api_secret_key` uses `secrets.token_urlsafe(32)` as fallback. With 4 Uvicorn workers, JWTs from one worker are invalid for others unless `API_SECRET_KEY` env var is set.
- **Fix:** Ensure `API_SECRET_KEY` is always set in production. Add startup warning if using random fallback.

### H6: localStorage for Auth Tokens
- **Files:** `AuthContext.jsx`, `LoginPage.jsx`, `SignupPage.jsx`, `AcceptInvitePage.jsx`, `Home.jsx`
- **Impact:** JWT tokens stored in localStorage are vulnerable to XSS token theft.
- **Note:** This is common SPA practice and acceptable given proper XSS prevention (which is in place via HTML escaping). Migration to httpOnly cookies is recommended but not urgent.

### H7: No Multi-Tenant Isolation Tests
- **Impact:** No dedicated test verifies that tenant A cannot access tenant B's data. This is the most critical security property of the platform.
- **Fix:** Create `tests/test_multi_tenant_isolation.py` covering all data models.

### H8: No Widget API Endpoint Tests
- **Impact:** The most user-facing API (widget chat) has no dedicated tests.
- **Fix:** Create `tests/test_widget_api.py` covering session creation, message send/receive, lead capture.

---

## MEDIUM Findings

### M1: Wildcard CORS Configuration
- **File:** `backend/main.py` (lines 310-313)
- **Detail:** `allow_origins=["*"]` — justified by design (widget embedded on arbitrary customer domains). Per-widget origin validation is enforced at application level in `widget_helpers.py:_check_origin()`.
- **Recommendation:** Document why wildcard is necessary. Consider restricting non-widget endpoints.

### M2: Fake Scarcity on All Pricing Tiers
- **File:** `Home.jsx` (lines 638, 670, 703)
- **Detail:** "Waived - Only 10 Spots Remaining" on ALL three tiers. Identical scarcity undermines trust.
- **Fix:** Replace with honest "Setup fee waived for early customers" messaging.

### M3: Raw Exception in crawl.py
- **File:** `backend/routers/crawl.py` (line 54)
- **Detail:** `raise HTTPException(status_code=400, detail=str(e))` may expose internal details.
- **Fix:** Catch specific exceptions and return user-friendly messages.

### M4: Stripe Tests Incomplete
- **File:** `tests/test_stripe_webhook.py`
- **Detail:** Tests cover signature verification and event handling but not subscription creation, plan changes, or refunds.

### M5: Inconsistent Test Mocking Strategy
- **Detail:** Different test files use different mocking approaches. No standard test fixture pattern.

### M6: API Key Preview in Logs
- **File:** `backend/routers/widget_chat.py` (lines 371-374)
- **Detail:** Logs first 12 chars of Anthropic API key. Should log only "CONFIGURED" or "MISSING".

---

## LOW Findings

### L1: No Testimonials/Social Proof on Landing Page
### L2: No Chat Widget on Own Website (not dogfooding)
### L3: Contact Page Too Barebones
### L4: Industry Dropdown Missing Key Verticals (only 10 options)

---

## GOOD Findings (No Action Required)

- **G1:** HTML output properly escaped via `html.escape()` across all templates ✓
- **G2:** SQL injection protected via Supabase parameterized query builder ✓
- **G3:** All Pydantic models properly validate request inputs ✓
- **G4:** All Claude API calls use valid model ID `claude-sonnet-4-6` ✓
- **G5:** No `from __future__ import annotations` in any FastAPI file ✓
- **G6:** Password hashing uses bcrypt with proper salt ✓
- **G7:** No hardcoded secrets in committed code (secrets only in .env, which is gitignored) ✓

---

## Test Coverage Summary

| Area | Test File | Coverage | Gap |
|------|-----------|----------|-----|
| Authentication | test_auth_endpoints.py (9 tests) | PARTIAL | No password reset, no token refresh |
| Stripe Webhooks | test_stripe_webhook.py (16 tests) | PARTIAL | No subscription lifecycle |
| Appointments | test_appointments.py (9 tests) | BASIC | No timezone, recurrence |
| Booking Overlap | test_booking_overlap.py (18 tests) | FULL | — |
| Automations | test_automation_engine.py (34 tests) | COMPREHENSIVE | — |
| Calls | test_calls.py (36 tests) | COMPREHENSIVE | — |
| Business Page | test_business_page.py (30 tests) | COMPREHENSIVE | — |
| Local SEO | test_local_seo.py (25 tests) | COMPREHENSIVE | — |
| **Multi-Tenant Isolation** | NONE | **MISSING** | **CRITICAL** |
| **Widget API** | NONE | **MISSING** | **CRITICAL** |
| **Lead Management** | NONE | **MISSING** | HIGH |
| **Revenue Analytics** | NONE | **MISSING** | HIGH |
| **Invoicing** | NONE | **MISSING** | HIGH |

---

## Migration Status

- **Total files:** 67 (001-067)
- **Duplicate numbers:** 005 (x2), 007 (x3) — historical, already applied
- **Pending confirmation:** 025-032 (may not be applied to live Supabase)
- **Uncommitted:** 066 (waitlist), 067 (lead scoring config)
- **All SQL syntax:** Valid ✓
- **All foreign keys:** Reference existing tables ✓

---

## Immediate Action Plan

1. Fix C2 (SMS import crash) — runtime error
2. Fix C1 (Stripe test links) — revenue pipeline broken
3. Fix H3 (auth rate limiting) — security
4. Fix H1 (forgot password) — user lockout
5. Fix H2 (dead links) — professionalism
6. Write H7 (multi-tenant tests) — security verification
7. Write H8 (widget API tests) — critical path coverage
8. Fix M2 (fake scarcity) — trust
9. Fix M3 (raw exception) — info leak
10. Fix M6 (API key logging) — security hygiene
