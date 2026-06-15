# Launch-Readiness Audit — 2026-06-15

Verification sweep ahead of official launch. Four checks run: full test suite,
schema-vs-code drift, security/tenant-isolation audit, pricing/billing map.

## Results

### Tests — PASS
`pytest backend/tests` → 862 passed, 35 skipped. Frontend + hermetic green in CI.

### Tenant isolation / security — PASS with hardening
No CRITICAL. **No tenant-isolation leaks, no missing webhook signature checks,
no hardcoded secrets, no XSS sinks.** `tenant_scope` helpers used consistently.

Fixed in this PR (both in the newly-shipped support widget):
- **H1** — `platform_support` sessions are now server-issued + HMAC-signed
  (`_issue_session`/`_resolve_session`), so a caller cannot guess/forge another
  visitor's `session_id` to read their transcript or inject into their chat.
- **H2** — per-session message cap (`_MAX_SESSION_MESSAGES = 40`) on the public
  support chat, bounding Claude cost/abuse alongside the per-IP rate limit.
- **M1** — corrected the misleading `_verify_resend_signature` docstring (code
  already rejects on empty secret; docstring claimed the opposite).

### Schema drift — 2 silent gaps (deferred, non-blocking)
Both wrapped in try/except, so they degrade silently rather than crash:
- `backend/services/integration_key_vault.py:132` writes to `audit_log` (table
  does not exist) → integration-key audit logging silently broken.
- `backend/routers/widget_chat.py:818` reads `lead_field_definitions` (does not
  exist) — likely a misnamed reference to the existing `custom_field_definitions`.

### Pricing / billing map — input to repricing work
Per-plan AI spend caps already exist and are enforced before every Claude call
(`ai_usage_guard.py`). **No overage / pay-for-more-usage path exists yet.** Plan
names/prices are hardcoded in ~9 places (backend config, stripe_service,
billing amount-map, frontend ×4, landing-page ×2).

## Deferred follow-ups (tracked, not in this PR)

Security (hardening, not launch-blocking):
- **M2** — DONE. `admin_api_secret_key` no longer falls back to `api_secret_key`
  in production (`admin_analytics._admin_secret`); a leaked JWT key can't grant
  admin access. Fails closed at the route (401), not at boot.
- **L1** — DONE. `rate_limit.py` XFF fallback now uses the right-most (trusted
  edge) entry, matching `limiter.py`.
- **L2** — DONE. `@limiter.limit("20/minute")` added to the Instagram + Facebook
  OAuth callbacks.

Still deferred (touch hot paths — warrant a dedicated, unrushed change):
- **M3** — JWT 24h stale plan/role claims. Token-version check needs a per-request
  DB read on the auth hot path (perf) + careful backward-compat to avoid mass
  logout. Deferred to its own change.
- **L3** — Twilio HMAC URL from `request.url`; switch to `settings.base_url`.
  Current code fails safe (rejects); changing it risks breaking live webhook
  verification if base_url is misconfigured. Deferred.

Schema:
- DONE — `audit_log` table created (migration 151, applied to prod).
- DONE — widget_chat repointed `lead_field_definitions` → `custom_field_definitions`
  (columns confirmed identical).

## Pricing / billing rebuild — DONE (#288, merged 2026-06-15)
- Two plans: Chatbot $19.99/mo, Full Agent OS $99.99/mo. No Free tier. Clean cut.
- Per-plan AI cap shown as a usage meter; buy-more-usage overage (migration 150).
- Also found + fixed: `admin_analytics.PLAN_PRICE_CENTS` MRR drift (now the two plans).
- Remaining: 3 competitor-comparison landing pages (not on the live domain);
  operator must create the 3 Stripe prices + set Railway env vars.
