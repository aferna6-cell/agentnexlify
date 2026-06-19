# Nightly Commit Review — 2026-06-19

Generated: 2026-06-19 UTC  
Commits reviewed: 16 (last 24 hours)

---

## Commits Triaged

| SHA | Title | Risk |
|-----|-------|------|
| `3030583` | subconscious: run 2026-06-18-pm — Fix GH #308 webhook idempotency early-write | LOW |
| `871ba66` | Leadgen: add keyless OpenStreetMap source (Google fallback) | MEDIUM |
| `b0e11d0` | Leadgen: merge_leads.py (dedup across runs) + Instantly-ready export | MEDIUM |
| `48a747b` | Outreach runbook + onboarding email-gate check + mobile hours-row fix | LOW |
| `737f02a` | Security + activation: redirect-revalidating fetch + embed first-lead promise | HIGH |
| `3d2bd3e` | Audit: security pass on recent endpoints | LOW |
| `645b323` | Security: consolidate SSRF guard onto url_validation + harden + cover leadgen | HIGH |
| `acb4cb7` | Onboarding: apply migration 154 + demo-to-signup carry + talk-to-AI shortcut + Auto-KB empty fallback | MEDIUM |
| `d977341` | CI: throttle high-frequency scheduled crons to conserve Actions minutes | LOW |
| `01d72ed` | CI: local gate mirror + trim double-spending workflow trigger | LOW |
| `3732d52` | Audit: signup to first-value path (item #4) | LOW |
| `9bb63de` | Demo: personalize /demo per lead + attribution + wire lead-engine demo_url | MEDIUM |
| `4f18e09` | Alert: email the founder on every new signup | MEDIUM |
| `852ebe4` | ci: re-trigger PR Validation (GHA startup flake retry 2) | LOW |
| `519bd44` | ci: re-trigger PR Validation (prior run hit sub-5s GHA infra flake) | LOW |
| `ae382f5` | Lead engine + cold-email sequences for outreach | MEDIUM |

---

## CLAUDE.md Compliance

- **No `from __future__ import annotations`** in any new Python files — PASS
- **No `tenant_id` on leads/conversations** tables in new code — PASS
- **Widget byte-identical** — not touched this run, no change needed
- **Schema changes via migration files** — migration 154 applied via proper `apply_migration` — PASS
- **No secrets in commits** — PASS

---

## HIGH Risk — Security (reviewed, no issues found)

### `645b323` — SSRF guard consolidation (HIGH, SECURITY IMPROVEMENT)
**Status: CORRECT — no action needed**
- Consolidated two inline `_is_safe_url` copies (website_crawler, content_repurposer) that only blocked literal private IPs into the canonical `url_validation.py` DNS-resolving guard
- Added `_ip_is_blocked()` helper blocking multicast, unspecified, IPv6 scope ids, empty DNS resolution
- Covered `scripts/leadgen/enrich.py` which previously fetched arbitrary scraped URLs with no SSRF guard
- 12 dedicated tests for the canonical guard — good coverage
- All gates passed per commit message

### `737f02a` — Redirect re-validation (HIGH, SECURITY IMPROVEMENT)
**Status: CORRECT — no action needed**
- `content_repurposer.extract_source` and leadgen enricher followed redirects automatically, allowing a safe initial host to 302 to an internal/metadata address
- Both now follow redirects manually (max 5 hops) and re-validate every hop via `is_safe_url`
- Correct pattern: `follow_redirects=False` + manual hop loop + SSRF check per hop
- Tests cover the 302-to-169.254.169.254 case

---

## MEDIUM Risk — New Features (reviewed, no issues found)

### `4f18e09` — Founder signup alert
- New `backend/services/signup_alert.py` — best-effort, never raises, never blocks signup
- PII in email body is HTML-escaped. Logs only business_name (no email/phone in logs)
- `platform_mailer.py` recipient override is additive and backward-compatible
- Well-tested (5 tests)

### `871ba66` / `b0e11d0` / `ae382f5` — Leadgen scripts
- No backend/auth/schema changes — pure script additions under `scripts/leadgen/`
- OSM fallback correctly detects `GOOGLE_PLACES_API_KEY` presence
- No hardcoded credentials found
- `merge_leads.py` dedup logic is clean; 11 offline tests

### `acb4cb7` — Migration 154 + onboarding
- Migration 154 (conversation sentiment + intent) marked **APPLIED to prod 2026-06-18** — closes the half-shipped state
- Frontend onboarding changes are cosmetic/UX only (no API shape changes)
- Auto-KB empty fallback is defensive

---

## LOW Risk — Auto-fixed

None. No LOW-risk bugs found requiring auto-fix.

---

## OPEN ISSUES — Require Human Action

### 🔴 GH #308 — Webhook idempotency early-write drops payment events (STILL OPEN — 2 days)
- `check_and_record()` in `idempotency.py` inserts row BEFORE handler runs
- Handler throws → row persists with `response_body=NULL` → Stripe retry hits `is_new=False, in_flight=True` → returns 200 without processing → **event permanently dropped**
- Real blast radius: tenant fixes payment card, stays dunning-locked forever
- Fix sketched by subconscious runs #59 + #60: add `delete_key()` to `idempotency.py`, call it in `stripe_webhooks.py:105` exception handler before re-raise
- **CANNOT AUTO-FIX** — touches payments. Requires explicit human approval.
- Files: `backend/services/idempotency.py`, `backend/routers/stripe_webhooks.py`

### 🟡 GH #292 — SMS rate limiter + API key auth missing new plan names
- `sms_rate_limiter._UNLIMITED_PLANS` missing `chatbot`/`agent_os` → new tenants SMS-capped at 50/day
- `api_key_auth._ALLOWED_PLANS` missing `chatbot`/`agent_os` → Zapier returns 402
- **CANNOT AUTO-FIX** — product decision required (chatbot SMS cap: unlimited vs 200/day?)
- Open since 2026-06-16 (3 days)

### 🟡 GH #293 — orchestrator + billing_reconciliation stale plan names
- `orchestrator.py` + `billing_reconciliation.py` still reference old plan names
- `agent_os` tenants miss branded email; reconciliation caps wrong
- Blocked on same product decision as #292
- Open since 2026-06-16 (3 days)

---

## Summary

16 commits landed. Quality is high — active security hardening sprint (SSRF consolidation + redirect re-validation), solid leadgen pipeline, clean migration apply. No CLAUDE.md violations. No LOW-risk bugs found.

**The one persistent concern is GH #308 (payment revenue bug).** The idempotency early-write flaw means any transient handler failure during `invoice.payment_succeeded` permanently locks the tenant out of their account even after they fix their card. The fix is sketched, ~15 lines, but requires human approval because it touches Stripe webhooks and payment state. This has been open 2 days across 2 subconscious recommendation cycles.

No auto-fixes committed this run.
