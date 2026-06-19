# Candidate Ideas — Run 62 (2026-06-19-pm)

## Evidence Digest

18 commits landed in last 24h: leadgen pipeline (OSM source, merge_leads, enrich SSRF hardening),
onboarding activation (migration 154 applied), CI throttling, security consolidation (SSRF
guard centralized to url_validation.py). GH #308 (webhook idempotency) unimplemented 4 cycles —
run 62 mandate fires. GH #292/#293 plan-name gaps confirmed live in 3 files. GH #263 (24
pending migrations) flagged CRITICAL for 5 days. PR #333 (51 commits) pending review.

---

### Idea 1: Fix GH #292/#293 — Wire chatbot/agent_os into Plan-Name Dicts (RUN 62 MANDATE)

**Evidence:** Run 62 mandate fires: GH #308 unimplemented 4th consecutive cycle (delete_key
absent confirmed by grep). GH #292/#293 plan-name gaps live in 3 files, confirmed by direct
inspection:
- `sms_rate_limiter.py:10`: `_UNLIMITED_PLANS = {"growth", "professional", "autopilot", "enterprise"}` — missing chatbot/agent_os
- `api_key_auth.py:29`: `_ALLOWED_PLANS = {"growth", "autopilot", "professional", "enterprise"}` — missing chatbot/agent_os
- `billing_reconciliation.py:33-48`: `_PLAN_AGENT_RUN_CAPS` + `_PLAN_BASELINE_AI_TOKENS` — old plan names only
Morning digest Priority #3: "chatbot/agent_os plan names missing, new paid tenants broken."
Billing repriced 2026-06-16 (PRs #285-291), 3 days stale in plan-name dicts.

**Action:** Add `"chatbot"` and `"agent_os"` to:
1. `sms_rate_limiter._UNLIMITED_PLANS` set
2. `api_key_auth._ALLOWED_PLANS` set
3. `billing_reconciliation._PLAN_AGENT_RUN_CAPS` dict (with appropriate caps)
4. `billing_reconciliation._PLAN_BASELINE_AI_TOKENS` dict (with appropriate baselines)

**Impact:** All new paid tenants (chatbot $19.99, agent_os $99.99) get correct SMS limits
and Zapier access. Fixes active product breakage for every new signup since 2026-06-16.

**Category:** code_health

---

### Idea 2: Fix GH #308 — Webhook Idempotency Early-Write (4th carry-over)

**Evidence:** delete_key absent from idempotency.py confirmed. Revenue bug — dunning-lock
after card fix. Bug introduced 2026-06-16 (47c7f8b). 3 prior subconscious runs with same
winner, nightly review did not implement (medium-risk payment code).

**Action:** Add `delete_key()` to `idempotency.py`; call in `stripe_webhooks.py` exception
handler before re-raising.

**Impact:** Stripe retries succeed after transient handler failures. Prevents dunning-lock.

**Category:** code_health

*Note: Run 62 mandate says switch to GH #292/#293. GH #308 demoted to Bonus A.*

---

### Idea 3: Investigate GH #263 — 24 Pending Migrations (CRITICAL, 5 days)

**Evidence:** Morning digest flags GH #263 as CRITICAL: "24 pending migrations — flagged
2026-06-14, still open." Migration 154 just applied in acb4cb7. If 24 migrations are pending,
it signals either (a) schema drift accumulation or (b) inflated count from stale tracking.

**Action:** Audit the 24 pending migrations: determine which are safe to apply, which
are already applied but not tracked, and file the fix plan as a GH issue.

**Impact:** Resolves CRITICAL infrastructure flag; prevents hidden schema drift.

**Category:** operational

---

### Idea 4: Review + Merge PR #333 (51-commit batch)

**Evidence:** Morning digest Priority #2: PR #333 has 51 commits — billing repricing,
AI Workforce, Conversation Insights, checkout hardening. 51 commits drifting further
each day. Includes PRs #325 (checkout UX), #328 (retention save-offer), #327 (upgrade
prompt fix).

**Action:** Human review of PR #333 and merge if CI passes.

**Impact:** Unblocks 51 accumulated commits. Ships billing repricing + checkout UX.

**Category:** operational

---

### Idea 5: Add Plan-Name Guard Check 7 to check_project_invariants.py (AUTONOMOUS-EXECUTABLE)

**Evidence:** Bonus B from runs 59/60/61. After GH #292/#293 fix lands, plan-name guard
becomes autonomous-executable. check_project_invariants.py currently has no plan-name
coverage. The 2-plan repricing (chatbot/agent_os) introduced this gap — future repricing
will reproduce it without a guard.

**Action:** Add check 7 to `scripts/check_project_invariants.py` — scan `sms_rate_limiter.py`,
`api_key_auth.py`, `billing_reconciliation.py` for "chatbot" and "agent_os"; FAIL if absent.
~15 lines Python. AUTONOMOUS-EXECUTABLE by nightly review after Idea 1 lands.

**Impact:** Systemic guard against plan-name drift at commit time. Self-maintaining.

**Category:** code_health
