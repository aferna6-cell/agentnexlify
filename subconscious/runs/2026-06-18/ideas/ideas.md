# Candidate Ideas — Run 2026-06-18

## Evidence Digest

Sixteen commits since run 59 (2026-06-17-pm), heavy on billing/checkout/UX. Plan repricing (chatbot $19.99 / agent_os $99.99) landed 3 days ago but left 4 backend files with stale plan-name dicts — all confirmed broken for new paid tenants. GH #308 (idempotency early-write) still open: `idempotency.py` has no `delete` method. `check_project_invariants.py` passes 6 checks but doesn't guard plan-name access dicts. `email_sequences.py` still 1143L (run 41, day 29+). Positive: `61947b9` correctly gated AI Workforce to `agent_os` plan; 14 checkout/billing UX commits landed cleanly.

---

### Idea 1: Fix plan-name access dicts — sms_rate_limiter.py + api_key_auth.py
**Evidence:** `sms_rate_limiter.py:10` — `_UNLIMITED_PLANS = {"growth", "professional", "autopilot", "enterprise"}` — `agent_os` missing. New agent_os ($99.99/mo) tenants capped at 50 SMS/day (FREE limit). `api_key_auth.py:29` — `_ALLOWED_PLANS = {"growth", "autopilot", "professional", "enterprise"}` — `chatbot` and `agent_os` both missing. All new paid tenants can't create API keys → Zapier integration broken. Repricing landed 2026-06-15 (3 days ago); no test caught this.
**Action:** Replace old plan names with `chatbot`/`agent_os` in both files. For sms_rate_limiter: add `agent_os` to unlimited; give `chatbot` 200/day limit. For api_key_auth: add both `chatbot` and `agent_os` to allowed set.
**Impact:** Restores core features (SMS, Zapier) for 100% of new paid tenants. Directly prevents churn from tenants who can't use what they paid for.
**Category:** code_health

---

### Idea 2: Fix GH #308 — idempotency row delete on handler exception
**Evidence:** Run 59 winner, still open. `idempotency.py` (112 lines) has no `delete` method. `billing.py:282` raises `HTTPException(500)` on handler failure (correct — Stripe retries), but idempotency row persists with `response_body=None`. Stripe retry sees row → `is_new=False` → billing.py returns 200 without processing → event permanently dropped. Tenants who fix their payment card stay dunning-locked.
**Action:** Add `delete(event_id)` to `idempotency.py`. Wrap handler in billing.py try/except/delete-on-exception. Add regression test (spec in run 59 winning-concept.md).
**Impact:** Fixes payment recovery. Dunning-locked tenants who fix their card will recover automatically.
**Category:** code_health

---

### Idea 3: Add Check 7 to check_project_invariants.py — plan-name guard
**Evidence:** Invariant checker passes 6 checks but has no guard on plan-name access dicts. 4 files missed the June repricing despite 50 commits/6 days velocity. If Check 7 existed, `sms_rate_limiter.py` and `api_key_auth.py` would have failed pre-commit. Every future repricing risks the same class of bugs.
**Action:** Add Check 7: scan `sms_rate_limiter.py`, `api_key_auth.py`, `billing_reconciliation.py` for current plan names (`chatbot`, `agent_os`). FAIL if any missing. AUTONOMOUS-EXECUTABLE (sequenced after Idea 1).
**Impact:** Prevents every future repricing from silently breaking SMS/Zapier/AI-token access.
**Category:** code_health / workflow

---

### Idea 4: Fix billing_reconciliation.py + orchestrator.py plan-name dicts (complete GH #292/#293)
**Evidence:** `billing_reconciliation.py:33-49` — `_PLAN_AGENT_RUN_CAPS` and `_PLAN_BASELINE_AI_TOKENS` have only old plan names. New `chatbot`/`agent_os` tenants get no match → wrong agent-run caps and AI token baselines. `orchestrator.py:238/319` — branded emails gated to `("professional", "enterprise")` — `agent_os` ($99.99/mo) doesn't get branded emails.
**Action:** Update both dicts with `chatbot`/`agent_os` entries (caps and baselines require product decision on values).
**Impact:** Correct AI token limits and agent-run caps for all new paid tenants. Agent_os tenants get branded emails.
**Category:** code_health

---

### Idea 5: Invoke /god-class-splitter on email_sequences.py
**Evidence:** email_sequences.py is 1143L (run 41 winner, day 29+). god-class-splitter SKILL.md ready (e848b87). post-split-test-repair SKILL.md ready (d481799). GH #112/#113 N+1 queries easier post-split.
**Action:** Invoke `/god-class-splitter` on email_sequences.py — split into email_crud + email_enrollment + email_processor.
**Impact:** Removes largest god-class in backend. Unblocks N+1 fixes. Reduces blast radius on email automation bugs.
**Category:** code_health
