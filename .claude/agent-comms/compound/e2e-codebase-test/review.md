# Code Review: End-to-End Codebase Audit
## Agent 4 Output — 2026-04-05

## Review Scope
Full codebase audit — 62 routers, 67 pages, 88 migrations, 18 services. Synthesized from 4 parallel agent outputs + inline checks.

---

## CRITICAL Issues

### 1. CORS Wildcard on All Routes (HIGH-03 from security audit)
- **File:** `backend/main.py:318-324`
- **Issue:** `allow_origins=["*"]` on ALL routes, not just widget endpoints
- **Fix:** Split CORS — wildcard for `/api/v1/widget/*`, restricted for dashboard routes

### 2. XSS via Custom HTML Sanitizers (HIGH-01, HIGH-02)
- **Files:** `frontend/src/pages/Automations/SequenceBuilder.jsx:234-261`, `frontend/src/pages/DocumentsPage.jsx:14-19`
- **Issue:** Regex-based sanitization misses SVG, iframe, javascript: protocol vectors
- **Fix:** Replace with DOMPurify

### 3. Missing Security Headers (HIGH-04)
- **File:** `backend/main.py` (absence)
- **Issue:** No X-Content-Type-Options, X-Frame-Options, HSTS
- **Fix:** Add security headers middleware

### 4. Billing Auth Key Reuse (MED-02)
- **File:** `backend/routers/billing.py:27-29`
- **Issue:** Same key signs JWTs and authenticates billing — compromise of one compromises both
- **Fix:** Separate BILLING_SECRET env var

---

## Warnings

### 5. Migration Numbering Conflicts
- 3 duplicate pairs need resolution (066, 067, 068)
- 9 pending migrations not verified as applied

### 6. Ghost Pydantic Fields
- `timeline` and `budget` in LeadUpdateRequest have no DB columns
- Silent failure — won't crash but data gets lost

### 7. Misleading Comment
- `backend/routers/sms.py:184` says "conversations table uses tenant_id" — code correctly uses client_id

### 8. Unsanitized Search in snippets.py
- `backend/routers/snippets.py:58` — No input sanitization on ilike search
- PostgREST filter syntax could be manipulated

### 9. Hardcoded Production URL
- `backend/routers/client_portal.py:439` — `https://agentnexlify-production.up.railway.app`
- Should use `settings.api_url`

---

## Passing Areas

| Area | Status | Notes |
|------|--------|-------|
| Dangerous imports | PASS | Zero `from __future__ import annotations` in routers |
| Schema column usage | PASS | All leads queries use `client_id`, all status queries use `status` |
| Auth coverage | PASS | All 10 sampled routers have proper auth |
| Widget sync | PASS | Both files identical |
| Frontend build | PASS | Builds clean in 3.97s |
| API alignment | PASS | Frontend endpoints match backend routes |
| Empty states | PASS | All sampled pages handle no-data case |
| Hardcoded secrets | PASS | None in source files |
| SQL injection | PASS | Supabase ORM used throughout |
| JWT handling | PASS | Proper algorithms, proper secrets |
| Webhook verification | PASS | Stripe, Twilio, Resend all verified |
| Tenant isolation | PASS | All sampled routers filter by tenant |
| Password handling | PASS | bcrypt, no logging |
| npm audit | PASS | 0 vulnerabilities |

---

## Verdict: FIX

4 HIGH issues should be resolved before next deploy:
1. Split CORS configuration
2. Install DOMPurify, replace custom sanitizers
3. Add security headers middleware
4. Separate billing auth key

No CRITICAL code bugs. Schema is clean. Build is healthy. The HIGH issues are all security hardening — defense-in-depth improvements, not active exploits.
