# Security Audit — Recent Endpoints

Date: 2026-06-18
Scope: endpoints/services added in recent work — `signup_alert`, `lead_alerts`,
`front_desk_health`, the `os_*` routers (`os_threads`, `os_inbound`),
`instant_kb`, and the `onboarding` auto-kb path. Checks: tenant isolation,
auth/role gates, webhook signature verification, unsigned OAuth state, XSS,
SSRF, secret handling, SQL injection, wrong-column (client_id vs tenant_id).

This is a findings report. Fixes (if any) belong in a separate session per the
"don't fix and audit in the same session" rule. SSRF consolidation (items 1/3/4
of the security pass) was already shipped this session — see commit 645b3238.

## Result: no CRITICAL, HIGH, or MEDIUM findings in scope.

The recently-added surface is well-isolated and consistently gated. Details below.

## What was verified clean

### Tenant isolation
- `front_desk_health.py:55` — `verify_tenant(claims, tenant_id)` before any read;
  queries scoped via `tenant_table(db, "conversations", tenant_id)` +
  `.eq("client_id", tenant_id)` (correct column for conversations).
- `instant_kb.py` draft + confirm — `require_role("owner","admin")` +
  `_verify_tenant(claims, tenant_id)` on both endpoints.
- `os_threads.py` — never trusts a path/body tenant value: every handler reads
  `client_id = claims["tenant_id"]`, and `_load_thread(db, client_id, thread_id)`
  enforces thread ownership before listing messages/runs. Model-grade isolation.
- `onboarding.py` auto-kb (`:735`) — `require_role("owner","admin")` +
  `require_active_plan` + `_verify_tenant`.

### Webhook signature verification (fail-closed)
- `os_inbound.py` inbound email (`:138`) — verifies Postmark HMAC / Mailgun
  signature against the RAW body BEFORE `request.json()`; 401 on mismatch.
  Missing secret → `_verify_postmark_request` returns False → 401 (fail-closed,
  not fail-open).
- `os_inbound.py` inbound SMS (`:283`) — Twilio signature verified against raw
  body before branching on form fields; 403 on mismatch.

### XSS (HTML email)
- `signup_alert.py:32-36` — all five interpolated fields run through
  `html.escape()` before f-string assembly.
- `lead_alerts.py:112-120` — interpolated values are the `safe_*` escaped
  variants.

### SSRF
- All tenant/user-supplied fetch URLs now route through the canonical
  DNS-resolving guard `backend/services/url_validation.py` (consolidated this
  session): website crawler, content repurposer, leadgen enricher,
  webhook_dispatcher, instant_kb, onboarding auto-kb.

### Other
- No f-string SQL in scope (Supabase query builder only; no raw SQL).
- No wrong-column usage — `front_desk_health` correctly uses `client_id` for
  conversations via `tenant_table`.
- No secret values logged — `platform_mailer.py:52` logs only the
  "not configured" condition, never the key.
- Rate limiting present on abuse-prone endpoints: auto-kb `5/hour`,
  forgot-password `3/minute`.

## LOW / informational (no action required now)

### LOW-1 — redirect re-validation on direct httpx fetchers
`content_repurposer.py:155` and `scripts/leadgen/enrich.py` fetch with
`follow_redirects=True`. The SSRF guard validates the initial URL but not the
final URL after a 30x. A safe-looking host could 302 to an internal address.
- Impact: bounded — `content_repurposer` is behind auth; `enrich.py` is an
  operator-run CLI today. The website crawler is unaffected (it proxies through
  Cloudflare's rendering API, so the fetch never originates from our network).
- Documented as a known limitation in `url_validation.py`. A full fix needs an
  httpx redirect hook or manual redirect loop that re-validates each hop.
  Worth doing before `enrich.py` is ever wired into a server endpoint (the
  "v2 live demo bot" idea).

### LOW-2 — OAuth state
No new OAuth callbacks were added in the focus set, so the signed-JWT-state
requirement was not re-exercised. Existing integrations follow the
`integrations.py` signed-state pattern. No action.

## Recommended sequence (separate session)
1. LOW-1 redirect re-validation — fold into `url_validation` as a
   `fetch_safely()` helper that re-checks each redirect hop, then use it in
   `content_repurposer` and `enrich.py`. Do this before any server-exposed
   scrape feature ships.

## Note
Findings are grounded in source reads + targeted greps, not a live pen test. A
runtime check (RLS policy presence via `pg_policies` for the `os_*` tables,
plus a real cross-tenant request against `front_desk_health` and `os_threads`)
would confirm the isolation holds end-to-end before a security-sensitive
release.
