# Nightly Commit Review — 2026-06-16

Run at: 2026-06-16 UTC (automated)

---

## Commits Reviewed (last 24h)

| SHA | Description | Risk |
|-----|-------------|------|
| `ff2ca28` | Gate signup behind payment; grandfather existing tenants (#291) | HIGH |
| `f67fd42` | Reprice competitor landing pages to two-plan model (#290) | LOW |
| `98a935f` | Security/drift follow-ups: admin-secret, XFF key, OAuth rate limits, audit_log (#289) | HIGH |
| `9bed342` | Reprice to two plans + usage caps + buy-more-usage (#288) | HIGH |
| `ded0c3d` | docs: auto-log bug fix from cc1bd4a | LOW |
| `cc1bd4a` | Launch hardening: sign support-chat sessions + cap cost (#287) | HIGH |
| `bec069d` | Platform support channels: Agent OS alerts, support form, widget (#285) | MEDIUM |
| `38f92c3` | chore(deps): bump dompurify 3.4.0→3.4.10 in frontend (#276) | LOW |
| `8bc9d98` | feat(frontend): integration-keys settings page (#139) | MEDIUM |
| `702379e` | chore(deps-dev): bump @playwright/test 1.59.1→1.60.0 (#164) | LOW |
| `42c7a43` | feat(integrations): tenant integration-keys API + health checker (#132) | MEDIUM |
| `87b5eb8` | ops: nightly-commit-review 2026-06-15 | LOW |

---

## Triage Results

### HIGH risk — reviewed, no action taken (human approval required)

**`ff2ca28` — Pay gate (auth + payments + tenant gating)**
- `backend/services/pay_gate.py`: fail-open design looks correct (DB error → allow)
- Migration 152 applied, all 10 existing tenants grandfathered
- 15 backend tests + E2E stubs pass
- `RequirePaid.jsx` fail-open: preserves `undefined` pay_gate_exempt from /me (fixed in same PR)
- No bugs found. Well-tested. Observe in prod.

**`98a935f` — Security follow-ups**
- XFF `ips[0]` → `ips[-1]` change: correct (right-most = trusted proxy IP)
- `widget_chat.py` table change `lead_field_definitions` → `custom_field_definitions`: CORRECT FIX — `custom_field_definitions` is the actual table (per `backend/routers/custom_fields.py`). Previous code was pointing at a nonexistent table.
- admin-secret no-fallback, OAuth callback rate limits: look correct
- 101-test coverage on changed lines per CI log

**`9bed342` — Two-plan repricing**
- Billing, Stripe webhook, usage caps all updated for new plan names
- AMOUNT_TO_PLAN, PLAN_KEYWORDS, _resolve_plan all updated
- ⚠️ Drift found in 4 other files — see MEDIUM issues below

**`cc1bd4a` — Support chat HMAC signing**
- `_sign()` and `_resolve_session()` use `hmac.new()` correctly
- Session cap `_MAX_SESSION_MESSAGES=40` added
- `settings.api_secret_key` used as HMAC key — appropriate

**`bec069d` — Platform support channels**
- New `platform_support.py` router, `os_failure_notify.py`, `platform_mailer.py`
- New support widget in `landing-page-v2/support-widget/`
- Migration 149 applied to prod
- 213 backend tests + full coverage on changed lines

### MEDIUM risk — GitHub issues filed

**Issue #292** — `sms_rate_limiter.py` + `api_key_auth.py` missing new plan names
- `_UNLIMITED_PLANS` doesn't include `chatbot` or `agent_os` → all new tenants capped at 50 SMS/day
- `_ALLOWED_PLANS` doesn't include `chatbot` or `agent_os` → Zapier blocked for new tenants
- Files: `backend/services/sms_rate_limiter.py:10`, `backend/services/api_key_auth.py:29`

**Issue #293** — `orchestrator.py` + `billing_reconciliation.py` stale plan names
- `orchestrator.py:238,319`: branded email wrapping gated to `professional`/`enterprise`, misses `agent_os`
- `billing_reconciliation.py:35–49`: plan caps don't map `chatbot`/`agent_os` → inaccurate audit reports
- Files: `backend/services/automation/orchestrator.py`, `backend/services/billing_reconciliation.py`

### LOW risk — fixed directly

**Landing page stale content (missed by `f67fd42` repricing commit):**

Payment is now required at signup (`ff2ca28`), but three comparison pages still claimed "No credit card required" or described a free tier.

Fixes applied:
1. `landing-page-v2/tidio-alternative.html`:
   - JSON-LD FAQ answer: "free tier" → "plans start at $19.99/mo"
   - HTML FAQ answer: same update
   - CTA subtitle: "No credit card required." → "Plans from $19.99/mo."
2. `landing-page-v2/intercom-alternative.html`:
   - CTA note: removed "No credit card." phrase
3. `landing-page-v2/livechat-alternative.html`:
   - CTA note: removed "No credit card." phrase

Note: CTA button text "Start Free" / "Try NexLiFy Free" in intercom/livechat pages was not changed — that requires product decision on whether "free" refers to a free trial or has been retired. Left for human review.

---

## Summary

- 12 commits reviewed, 836+ lines inserted in HIGH-risk areas (auth, payments, tenant gating, security)
- All HIGH-risk commits appear well-tested (CI green, migration applied, fail-open patterns present)
- 2 MEDIUM issues filed (#292, #293) for plan-name drift that blocks SMS, Zapier, and branding for new plan tenants
- 3 LOW-risk landing page content fixes committed directly
- No schema violations found (client_id usage correct, no `from __future__ import annotations` in new FastAPI files, no `__future__` in pay_gate.py)
