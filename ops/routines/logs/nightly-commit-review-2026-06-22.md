# Nightly Commit Review — 2026-06-22

**Run time:** 2026-06-22 UTC  
**Window:** Last 24 hours  
**Commits reviewed:** 4  
**Issues found:** 0 requiring action  
**LOW fixes applied:** 0  
**GitHub issues created:** 0

---

## Commit Triage

### 1. `3a958e5` — Fix #308: release idempotency row on webhook handler failure
**Risk:** HIGH (Stripe webhook / payments path)  
**Verdict:** CLEAN ✅

**What changed:**
- `backend/services/idempotency.py` — added `delete_key()` function that removes an idempotency row from `idempotency_keys` table
- `backend/routers/billing.py` + `backend/routers/stripe_webhooks.py` — both call `await delete_key(db, idempotency_key)` inside the `except Exception` block before re-raising as HTTP 500

**Assessment:**
- The fix is correct: without it, a handler failure left a NULL-response idempotency row that caused all Stripe retries to be acked 200 as "in-flight duplicates" — permanently dropping the event. This is a real production bug affecting payment recovery.
- `delete_key` is called ONLY in the except path. Happy path is unaffected.
- `delete_key` itself swallows its own exception (logs at ERROR level), so if the delete fails the 500 still propagates to Stripe correctly.
- No `from __future__ import annotations` in any changed file (verified by AST walk).
- Regression test in `test_security_hardening.py` asserts 500 response + key deleted (29 tests added).
- Commit states "ci-local ALL GATES PASSED; security + fraud suites 20 passed."

**No action required.** Prior issue note: a `subconscious-bot` commit `60fcebf1` planned this but committed only artifacts — this commit ships the actual fix.

---

### 2. `29ed1d4` — Reconciliation new-plan caps (#293) + refresh stale CLAUDE.md plan section
**Risk:** MEDIUM (billing reconciliation + CLAUDE.md update)  
**Verdict:** CLEAN ✅

**What changed:**
- `backend/services/billing_reconciliation.py` — added `chatbot: 800_000` and `agent_os: 5_000_000` to `_PLAN_BASELINE_AI_TOKENS`, mirroring `ai_usage_guard.PLAN_BASELINE_TOKENS`
- `CLAUDE.md` — rewrote stale "Plan names + prices" section; demoted retired plan names to legacy/grandfathered
- `backend/tests/test_plan_gating_new_plans.py` — 10 additional tests

**Assessment:**
- Token caps match canonical source (`ai_usage_guard.PLAN_BASELINE_TOKENS`): chatbot 800k, agent_os 5M. Correct.
- Agent-run caps for new plans left at `_DEFAULT_AGENT_RUN_CAP` with an explanatory comment pointing to GH #293 — explicitly noted as a product TBD. Acceptable.
- CLAUDE.md update is accurate per current `stripe_service.py` and plan gate constants.
- `os_tenant_usage` queried with `client_id` (correct), `tenant_ai_usage_monthly` with `tenant_id` (correct for that table).
- No CLAUDE.md critical invariant violations.

**No action required.**

---

### 3. `57f2bb4` — Fix plan-gating for repriced plans (chatbot/agent_os) — addresses #292
**Risk:** HIGH (feature gating / tenant entitlements)  
**Verdict:** CLEAN ✅

**What changed (6 service files):**
- `api_key_auth.py` — `_ALLOWED_PLANS` adds `"agent_os"` (Zapier/API keys)
- `sms_rate_limiter.py` — `_UNLIMITED_PLANS` adds `"agent_os"` (unlimited SMS)
- `document_drafting.py` — `_ELIGIBLE_PLANS` adds `"agent_os"` (doc drafting)
- `lead_qualification.py` — `_ELIGIBLE_PLANS` adds `"agent_os"` (AI lead qual)
- `automation/orchestrator.py` — branded email wrapping adds `"agent_os"`
- `branding_helpers.py` — adds `chatbot` (growth-tier fields, no `hide_powered_by`) and `agent_os` (enterprise-tier fields including `hide_powered_by`, `logo_url`, etc.)

**Assessment:**
- All gating additions follow documented intent: `agent_os` = full platform, `chatbot` = widget/chat entry tier.
- Legacy names (`growth`, `autopilot`, `professional`, `enterprise`) retained in all sets — grandfathered tenants unaffected.
- `chatbot` correctly excluded from `hide_powered_by` via the `if plan in ("free", "growth", "chatbot")` guard in `_filter_branding_for_plan`. White-label is `agent_os`-only.
- False positive on `from __future__` check: the warning in `branding_helpers.py` docstring contains the string but no actual import. AST walk confirmed clean.
- 90-line test suite added in `test_plan_gating_new_plans.py` locking all gate mappings.

**No action required.** This was a HIGH-urgency production regression: `agent_os` tenants paying $99.99/mo had NO premium features since the 2026-06-15 repricing.

---

### 4. `b3279b0` — Fix 7 failing tests: stale MRR plan names + widget patch-leak
**Risk:** LOW (test files only — no product code changed)  
**Verdict:** CLEAN ✅

**What changed:**
- `backend/tests/test_admin_analytics_mrr.py` — updated assertions from retired plan names to `chatbot`/`agent_os`; contract changed by the repricing (Rule 10 met: evidence cited in commit)
- `tests/test_widget_api.py` — removed duplicate `mock.patch` call that created a leaked mock affecting later tests

**Assessment:**
- Test change follows Rule 10 (never change tests to fit assumed intent): commit explicitly cites `stripe_service.py`, `config.py`, `plan_gate.MARKETING_PLANS`, and `admin_analytics.PLAN_PRICE_CENTS` as evidence the contract changed.
- Widget patch removal is a genuine test isolation fix (balanced start/stop).
- Full suite reported as 2163 passed, 36 skipped, 0 failed post-fix.

**No action required.**

---

## Summary

All 4 commits are well-formed, correctly targeted, and include regression tests. No LOW-risk bugs were found requiring autonomous fixes. All CLAUDE.md critical invariants (client_id, no `__future__`, schema discipline) were respected. The session that produced these commits (claude.ai session `01RxfRZfbp6n8oA265s65nLG`) addressed a significant cluster of production regressions from the 2026-06-15 repricing:

- **#292** — agent_os tenants locked out of all premium features (resolved: `57f2bb4`)
- **#293** — reconciliation audit mis-stating caps for new plans (resolved: `29ed1d4`)
- **#308** — Stripe webhook retries permanently dropping events after handler failure (resolved: `3a958e5`)

No issues to escalate. No human action required.

---

*Generated by nightly-commit-review agent | 2026-06-22*
