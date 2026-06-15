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
- **M2** — `admin_api_secret_key` falls back to `api_secret_key` (JWT key).
  Enforce a distinct value in production. (Deferred: a hard boot-fail could take
  prod down if the env var isn't set first — coordinate with deploy.)
- **M3** — JWT expiry 24h carries stale plan/role claims. Add a server-side
  token-version check or shorten expiry — more relevant once plans change.
- **L1** — `rate_limit.py` XFF fallback uses leftmost (attacker-controlled) IP;
  align with `limiter.py` (last entry).
- **L2** — add rate limits to Instagram/Facebook OAuth callbacks.
- **L3** — Twilio HMAC builds URL from `request.url`; use `settings.base_url`.

Schema:
- Create `audit_log` table (match `integration_key_vault` insert shape).
- Repoint `lead_field_definitions` → `custom_field_definitions` after confirming columns.

## Pricing / billing rebuild — spec locked, build pending
- Two plans only: Chatbot $19.99/mo, Full Agent OS $99.99/mo. No Free tier. Clean cut.
- Cap underlying Anthropic $ spend per plan; customer sees only a usage meter.
- Overage: buy-more-usage top-ups when the limit is hit.
- External dependency: Stripe products/prices must be created in the Stripe
  dashboard (no Stripe tooling in-session); code reads price IDs from env.
