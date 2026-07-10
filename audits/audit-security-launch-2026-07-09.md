# Security & Tenant-Isolation Audit — Launch Readiness

- **Date:** 2026-07-09
- **Scope:** Backend authz, tenant isolation, webhooks, secrets, cost/DoS. Read-only. No code modified.
- **Method:** End-to-end flow tracing across `backend/routers/*`, `backend/services/*`, `backend/config.py`, `backend/main.py`, plus a frontend secret scan.
- **Overall posture:** Strong. Webhook signature verification, JWT handling, password flows, and the tenant-scope helpers are mature and mostly fail-closed. The findings below are a small number of real gaps against an otherwise well-hardened baseline. **One HIGH** (bulk customer-PII export gated only on the public widget key) should be fixed before/at launch.

---

## CRITICAL

_None confirmed._

---

## HIGH

### H1 — Public widget API key grants bulk customer-PII export via iCal feed
- **Severity:** High
- **Category:** Security (Broken Access Control / PII disclosure)
- **Location:** `backend/routers/appointments.py:595-695` (`ical_feed`, `GET /api/v1/appointments/{tenant_id}/ical`)
- **Issue:** The iCal feed authenticates with `key` checked against `widget_configs.api_key` (lines 610-620). That api_key is the **public embed credential** — it ships in plaintext inside every tenant's website (`data-api-key` on the widget script tag) and is used for anonymous widget chat, slot lookup, and booking. The feed then returns, for a 120-day window (−30d/+90d), every appointment's `customer_name`, `customer_email`, `customer_phone`, and free-text `notes` (lines 630-664).
- **Impact:** Anyone who views a tenant's page source can lift the api_key and download the tenant's full customer contact list (name + email + phone + appointment notes) for ~500 appointments. This is a mass PII/GDPR breach vector affecting every customer of every tenant. A public "widget" key should never unlock bulk read of customer PII.
- **Evidence:** Key validation at `appointments.py:610-620` uses the same `widget_configs.api_key` that `widget_chat.py:321` and `book_appointment` (`appointments.py:220`) treat as public. PII columns selected at `appointments.py:632`.
- **Reproduction:**
  1. Load any tenant site embedding the widget; read `data-api-key` (e.g. `anx_…`) from the HTML.
  2. Read `tenant_id` from the same embed / a widget network call.
  3. `GET https://<api>/api/v1/appointments/<tenant_id>/ical?key=<anx_key>` → `.ics` with all customer contacts.
- **Recommended fix:** Do not gate PII export on the public embed key. Options, best first: (a) require a JWT (`_get_current_tenant` + `_verify_tenant`) and generate the calendar-subscription URL server-side with a **dedicated, revocable, high-entropy feed token** distinct from `widget_configs.api_key` (store in a `calendar_feed_tokens` table); (b) at minimum, drop `customer_email`/`customer_phone`/`notes` from the feed and expose only opaque busy/free blocks. The same concern applies to any other endpoint keyed on `widget_configs.api_key` that returns PII — audit `public_service_types` (service metadata only — OK) and confirm no others leak contact data.
- **Confidence:** Confirmed (code path fully traced).

---

## MEDIUM

### M1 — Billing/refund admin endpoints fall back to the shared API secret in production
- **Severity:** Medium
- **Category:** Security (Privilege separation / inconsistent fail-closed)
- **Location:** `backend/routers/billing.py:60-79` (`_verify_secret`, `_admin_secret`, `_verify_admin_secret`); `backend/config.py:181-214` (`_enforce_production_secrets`)
- **Issue:** `billing.py::_admin_secret()` falls back to `settings.api_secret_key` **unconditionally** when `admin_api_secret_key` is unset (lines 67-72), and `_verify_secret` uses `settings.billing_secret or settings.api_secret_key` (line 62). This contradicts the fail-closed pattern used by every other admin router — `funnel.py:35-48`, `referral.py:35-48`, `admin_analytics.py`, `admin_health.py`, `admin_funnel.py` all return `""` in production when `ADMIN_API_SECRET_KEY` is unset, rejecting all callers. Meanwhile `config._enforce_production_secrets` (line 181) hard-requires only `API_SECRET_KEY`; `BILLING_SECRET` and `ADMIN_API_SECRET_KEY` are optional. So production can boot with the **most sensitive** surface (admin refunds — real money movement, `billing.py` refund handlers) protected by the broad, widely-reused `api_secret_key` rather than a dedicated secret.
- **Impact:** Weakened blast-radius control on the money path. Any compromise or over-sharing of `API_SECRET_KEY` (also the JWT-signing fallback) hands an attacker the ability to issue refunds / mutate billing. The rest of the admin surface is strictly separated; billing — which should be the *most* separated — is the least.
- **Evidence:** Compare `billing.py:67-72` (no `is_production()` guard) with `funnel.py:41-44` / `referral.py:45-48` (explicit `if is_production(): return ""`).
- **Reproduction:** Static: with `ADMIN_API_SECRET_KEY` and `BILLING_SECRET` unset in prod, `_verify_admin_secret`/`_verify_secret` accept `API_SECRET_KEY`, whereas `/api/v1/admin/product-funnel` rejects everything.
- **Recommended fix:** Make billing match the fail-closed pattern: in `_admin_secret()` add `if is_production(): return ""` before the `api_secret_key` fallback, and require `BILLING_SECRET` (and `ADMIN_API_SECRET_KEY`) in `_enforce_production_secrets()`. Note the config warning text (`config.py:228-232`) already implies fallback is intended — reconcile the doc/code so behavior is unambiguous.
- **Confidence:** Confirmed.

---

## LOW

### L1 — AI usage cost cap fails OPEN on datastore error
- **Severity:** Low
- **Category:** Security (Cost/DoS resilience)
- **Location:** `backend/services/ai_usage_guard.py:186-201` (`reserve_ai_tokens`)
- **Issue:** If the `reserve_ai_token_budget` RPC raises (Supabase outage, RPC missing), the guard returns `allowed=True` with `reason="guard_unavailable"` and the Claude call proceeds uncapped. `_sum_usage_packs` (line 90-97) and `record_ai_usage` similarly fail open.
- **Impact:** During a sustained datastore disruption, the per-tenant monthly token hard cap (the "profit guarantee" that bounds Claude spend from api_key abuse) is silently removed platform-wide. An attacker abusing a leaked public api_key during such a window has no cost ceiling.
- **Evidence:** `ai_usage_guard.py:193-201` returns an `allowed=True` reservation on exception.
- **Recommended fix:** Keep fail-open for transient blips but add a circuit-breaker: after N consecutive `guard_unavailable` results, degrade to a conservative static per-request/per-minute cap (or a global kill-switch env flag) rather than unbounded. Alert on `guard_unavailable` rate.
- **Confidence:** Confirmed (design tradeoff; note for launch monitoring).

### L2 — Twilio missed-call / sms-reply signature check ignores forwarded proto/host
- **Severity:** Low
- **Category:** Security (webhook robustness — fails closed)
- **Location:** `backend/routers/twilio_webhooks.py:43-68` (`_verify_twilio_signature`)
- **Issue:** The signed URL is reconstructed from `str(request.url)` without honoring `X-Forwarded-Proto`/`Host`. Behind Railway's TLS-terminating proxy the request scheme is `http`, so the HMAC base string won't match Twilio's `https` URL. Contrast `automations.py:88-91` (voice/os_inbound path) which correctly rebuilds the URL from the forwarded headers.
- **Impact:** Not a bypass — it fails closed (403), so it degrades the missed-call text-back / SMS-reply feature rather than exposing data. Inconsistent with the other Twilio verifier and a latent reliability/behavior-drift risk.
- **Evidence:** `twilio_webhooks.py:50` `url = str(request.url)` vs `automations.py:89-91` forwarded-header reconstruction.
- **Recommended fix:** Reuse the `automations.verify_twilio_request` reconstruction (X-Forwarded-Proto + Host) in `twilio_webhooks.py`, or route both through one shared verifier.
- **Confidence:** High.

### L3 — Missing `role` claim defaults to `owner`
- **Severity:** Low
- **Category:** Security (defense in depth)
- **Location:** `backend/dependencies.py:22` (`require_role` → `claims.get("role", "owner")`)
- **Issue:** A JWT lacking a `role` claim is treated as `owner`. Tokens are always minted server-side with `role` set (`auth.py:115`), so not currently exploitable, but the default is fail-open rather than fail-closed.
- **Impact:** If any future token-mint path omits `role`, the holder silently gets owner privileges.
- **Recommended fix:** Default to the least-privileged role (or reject when `role` is absent).
- **Confidence:** Confirmed (latent).

---

## INFO / BY-DESIGN

### I1 — Public signing page renders tenant-authored HTML
- **Location:** `backend/routers/documents.py:418-463` (`get_document_for_signing` returns `rendered_html`).
- **Note:** The document body is HTML authored by an authenticated tenant (owner/admin) and shown to that tenant's own signer. Template-variable substitution is `html.escape`d (`documents.py:157`), but the base `template_html` is stored/served raw by design (documents are rich HTML). This is self-scoped (tenant → their customer), not cross-tenant. No action required beyond awareness; consider sanitizing/sandboxing (iframe `sandbox`, CSP already restricts embeddable routes) if untrusted sub-users are ever added.

### I2 — Weak signer-identity check on public sign
- **Location:** `backend/routers/documents.py:484-490`.
- **Note:** Name match is enforced only when both expected and provided names are non-empty; an empty provided name skips the check. The unguessable `signing_token` is the real credential and is nulled on sign (`documents.py:500`), so impact is negligible.

### I3 — Referral click endpoint is unauthenticated and attacker-writable
- **Location:** `backend/routers/referral.py:276-302` (`POST /click`).
- **Note:** `body.ref` (a tenant api_key) and `path`/`referrer` are inserted unauthenticated (rate-limited 30/min). Worst case is referral-click stat inflation/spam for a target tenant — no PII, no cross-tenant read. Acceptable for launch; consider basic origin/anti-abuse if referral rewards become money-significant.

---

## POSITIVES CONFIRMED (do not regress)

- **JWT:** Fixed `algorithms=["HS256"]` (`auth_service.py:26`) — no `alg=none`/algorithm-confusion. Tokens carry `exp` (`auth.py:117`). Dedicated `JWT_SECRET_KEY` supported with `API_SECRET_KEY` fallback.
- **Production secret enforcement:** App refuses to boot with missing/weak `API_SECRET_KEY` in production (`config.py:197-211`).
- **Webhook signature verification, all fail-closed:** Stripe (`stripe_webhooks.py:38-55`, + idempotency + safe 500→retry), Twilio voice & inbound SMS (`automations.py:60-99`, `os_inbound.py:306-316`), inbound email Postmark/Mailgun (`os_inbound.py:161-240`), Resend/Svix (`resend_webhooks.py:30-65`), Facebook (`channels_facebook.py:222`).
- **Admin analytics/health/funnel/referral:** fail-closed in production when `ADMIN_API_SECRET_KEY` unset (HMAC `compare_digest`).
- **Passwords:** bcrypt cost 12; dummy-hash timing equalization on login (`auth.py:415-456`); email-enumeration-safe forgot-password; reset token SHA-256-hashed at rest, 1h expiry, reset enforces full registration password policy; login/register/reset rate-limited (`auth_password_reset.py`, `auth.py:334/398`).
- **Tenant isolation:** JWT routes call `verify_tenant`/`_verify_tenant`; public/widget routes cross-check `api_key ↔ tenant_id` (`appointments.py:166/197/221`); `tenant_scope.py` helpers inject/validate the ownership column and refuse cross-tenant inserts; portal read is defense-in-depth scoped by `client_id` so a mismatched `lead_id` returns empty (`client_portal.py:417-425`).
- **CORS `*`:** Safe here — `allow_credentials=False` + Authorization-header (non-cookie) auth means `*` cannot be leveraged for credentialed CSRF (`main.py:696-702`).
- **Cost/DoS on widget:** Per-tenant monthly token hard cap + per-plan chat rate limits bound spend from api_key abuse (`ai_usage_guard.py`, `widget_chat.py:289-312`) — see L1 for the outage edge.
- **Reschedule tokens:** HMAC + TTL, legacy id-only path disabled by default (`booking_page.py:760-788`).
- **No SQL injection surface:** All DB access via the Supabase client / parameterized RPC; no raw f-string SQL found in `backend/`.
- **Mailers:** user-controlled values `html.escape`d before HTML email interpolation (`owner_alerts.py:36-49`, `documents.py`, `auth_password_reset.py:107`).
- **Frontend:** no hardcoded secrets/API keys in `frontend/src`; only runtime auth tokens passed as props.

---

## Quick wins (low effort, high value)
1. **H1:** Strip `customer_email`/`customer_phone`/`notes` from the iCal feed immediately (interim), then move to a dedicated revocable feed token. *(smallest change that stops the PII bleed)*
2. **M1:** Add `if is_production(): return ""` to `billing.py::_admin_secret()` and require `BILLING_SECRET` in `_enforce_production_secrets()`.
3. **L2:** Point `twilio_webhooks._verify_twilio_signature` at the forwarded-header URL reconstruction already used in `automations.py`.
4. **L3:** Default absent `role` to least-privilege in `require_role`.

## Architectural changes (larger, schedule post-launch)
1. Introduce a **calendar/PII feed token** type (revocable, per-tenant, distinct from the public widget key) and audit every `widget_configs.api_key`-gated endpoint for whether it should expose PII (H1 root cause: one credential conflating "public embed" with "read customer data").
2. Add a **circuit-breaker / global kill-switch** for the AI usage guard so a datastore outage degrades to a conservative static cap instead of uncapped spend (L1).
3. Consolidate admin/secret gating into **one shared, uniformly fail-closed dependency** so no future router re-introduces an inconsistent fallback (M1 class).

---

## Ship recommendation
**Ship with known risks — fix H1 (iCal PII feed) first (quick win #1 is a same-day change), and M1 before enabling production refunds.** Everything else (L1–L3, I1–I3) is monitorable/low and safe to follow up post-launch. The core auth, webhook, and tenant-isolation layers are launch-grade.
