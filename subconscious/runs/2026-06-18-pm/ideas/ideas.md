# Ideas — Run 2026-06-18-pm

## Evidence Digest

**What changed (last 3 days):** 20+ commits — leadgen pipeline (OSM source, merge, enrich, tests), SSRF hardening consolidated onto url_validation.py, CI improved (local gate mirror, cron throttle), activation sprint (signup email alert, demo personalization, first-value audit). Security audit of recent endpoints: no CRITICAL/HIGH/MEDIUM findings.

**What's broken:** (1) GH #308 CONFIRMED: idempotency.py inserts key BEFORE handler; no `delete` method exists; handler failure → row persists with `response_body=NULL` → Stripe retry skips processing → payment event permanently dropped → tenant stays dunning-locked after card fix. (2) GH #292/#293 CONFIRMED: `sms_rate_limiter._UNLIMITED_PLANS` and `api_key_auth._ALLOWED_PLANS` still reference old 4-plan names (growth/autopilot/professional/enterprise). New `chatbot`/`agent_os` tenants can't use Zapier, get wrong SMS limits.

**What's moot:** Billing repriced to 2-plan ($19.99 chatbot / $99.99 agent_os). AMOUNT_TO_PLAN in billing.py confirmed updated. Runs 30/31/32/34/51 (old AMOUNT_TO_PLAN fixes) are now moot. PR #183 is moot.

**What's healthy:** check_project_invariants PASSES all 6 checks. email_sequences.py down to 1143L from 1255L (slight progress). Home.jsx at 1006L — new god-class candidate.

---

### Idea 1: Fix GH #308 — Webhook Idempotency Early-Write Drops Payment Events
**Evidence:** `backend/services/idempotency.py` has no `delete` method. `stripe_webhooks.py:105` catches all exceptions and raises HTTPException(500) — BUT `check_and_record()` already inserted the idempotency row before the handler ran. On Stripe retry, `check_and_record` finds the row with `response_body=NULL`, sets `in_flight=True`, returns `(False, cached)` → webhook returns 200 without processing → payment event permanently dropped. Run 59 winner (2026-06-17-pm), moratorium override (payment revenue bug). Implementation sketch complete in runs/2026-06-17-pm/winning-concept.md.
**Action:** Add `delete_key(key: str)` to `idempotency.py`. In `stripe_webhooks.py` exception handler: call `await delete_key(db, idempotency_key)` before re-raising. Same pattern in `billing.py` if it has its own handler wrapper. Add regression test that fails on HEAD, passes after fix.
**Impact:** Closes payment event loss loop. Tenants who fix their card recover correctly. Prevents dunning-lock after card fix.
**Category:** code_health

---

### Idea 2: Fix GH #292/#293 — chatbot/agent_os Missing from Plan-Name Dicts
**Evidence:** Direct grep of `sms_rate_limiter.py:10` confirms `_UNLIMITED_PLANS = {"growth", "professional", "autopilot", "enterprise"}` — no `chatbot`/`agent_os`. `api_key_auth.py:29`: `_ALLOWED_PLANS = {"growth", "autopilot", "professional", "enterprise"}` — no `chatbot`/`agent_os`. `billing_reconciliation.py` references `growth`, `autopilot`, `professional`. Platform repriced to `chatbot`/`agent_os` 3+ days ago. New paid tenants silently get wrong behavior.
**Action:** Add `chatbot` and `agent_os` to `_UNLIMITED_PLANS` (sms_rate_limiter), `_ALLOWED_PLANS` (api_key_auth), and the billing_reconciliation plan caps. Product decision: chatbot SMS = 200/day (legacy growth), agent_os SMS = 500/day (legacy autopilot). No migration needed.
**Impact:** New paid tenants get correct Zapier access and SMS limits. Billing reconciliation shows accurate per-plan caps.
**Category:** code_health

---

### Idea 3: Add Plan-Name Guard (check_project_invariants Check 7)
**Evidence:** GH #292/#293 shows plan-name dicts drift silently after repricing. billing.py repriced 3+ days before sms_rate_limiter/api_key_auth were updated — no automated detection. Bonus B from run 59 winning-concept.md. check_project_invariants has 6 checks, all passing. AUTONOMOUS-EXECUTABLE pattern established (runs 37, 52, 58 all implemented autonomously by nightly review).
**Action:** Append check to `scripts/check_project_invariants.py`: scan `sms_rate_limiter.py`, `api_key_auth.py`, `billing_reconciliation.py` for current plan names (`chatbot`, `agent_os`). FAIL if any missing. ~15 lines Python. AUTONOMOUS-EXECUTABLE.
**Impact:** Prevents next repricing from silently breaking plan-name dicts. Catches drift within 24h via nightly review.
**Category:** code_health

---

### Idea 4: Wire leadgen Import Path — Enrich → Backend Leads Table
**Evidence:** `scripts/leadgen/` (5 files, 851 lines) built today: OSM business discovery, Google Places enrichment, dedup/merge, Instantly-ready CSV export. 447 tests passing. No integration with `backend/routers/` or `leads` table. Cold-outreach leads never enter AgentNexLiFy CRM.
**Action:** Add `scripts/leadgen/import_to_crm.py` that reads merged CSV output and POSTs to `POST /api/leads/bulk` (or writes directly to `leads` table via Supabase client). Requires `client_id` not `tenant_id`.
**Impact:** Closes the cold-outreach loop: discovered leads → widget → conversation → booked → CRM. Enables automated follow-up from widget on cold leads who later visit the site.
**Category:** customer_value

---

### Idea 5: Split Home.jsx God-Class (1006L)
**Evidence:** `Home.jsx` is 1006L, confirmed today. Recent commits (demo personalization, first-value path) are landing inside it — velocity growing. god-class-splitter SKILL.md available. User Rule 9: stop at 600L and split. No split plan exists for this component.
**Action:** Invoke `/god-class-splitter` on `frontend/src/pages/Home.jsx`. Identify ≥3 clean concerns (e.g. HeroSection, LeadCaptureSection, TestimonialsSection). Split into separate components under `frontend/src/pages/home/`.
**Impact:** Reduced merge conflict surface. New feature additions no longer bloat one file. Each section independently testable.
**Category:** code_health
