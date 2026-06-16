# Ideas — Run 58 — 2026-06-16

## Evidence Digest
- PRs #285-291 (+~3000 lines) shipped in 3 days: billing repriced to 2-plan ($19.99/$99.99), pay_gate signup gate, audit_log, integrations encryption, platform support hardening
- check_project_invariants.py PASSES all 6 checks for first time since 2026-06-13 — all historic blockers cleared
- pre-commit has Check 2 (from __future__), Check 11 (billing guard), Check 12 (timing-safe); Check 13 slot open
- run 56 winner (Check 13 from __future__ guard) superseded — Check 2 already covers from __future__ in routers
- run 55 + run 57 (em-dash + from __future__ + widget cp) both IMPLEMENTED by 3234597 (2026-06-13)
- GH #181 billing fix (AMOUNT_TO_PLAN) now MOOT — billing repriced, old plan codes retired
- RequirePaid.jsx (330L) wraps all dashboard routes — 14 backend + 68 frontend unit tests, no E2E
- JWT stale plan claims (M3) deferred from launch audit — 24h window where plan could be wrong post-upgrade
- email_sequences.py at 1143L (reduced from 1255L by cfdd6e3 email-sequence perf, still >600L)
- AI-to-Human Handoff: Critical, 61 days, still no implementation
- Moratorium: active, max_pending_approvals=2, but after governance corrections pending drops significantly

---

### Idea 1: Wire check_project_invariants.py into pre-commit as Check 13
**Evidence:** check_project_invariants.py PASSES all 6 invariant checks as of 3234597 (2026-06-13). All historic blockers gone. Run 42 set this up as pending_autonomous on 2026-05-31 (46 days ago). Launch sprint added 5 new services (pay_gate.py, billing_usage.py, integration_key_vault.py, platform_support.py) without invariant protection at commit time. Check 11 (061582c) and Check 12 (ca3ce68) both landed autonomously — same mechanism.
**Action:** Add 6-line bash block to scripts/hooks/pre-commit after Check 12 (~line 295). Runs `python3 scripts/check_project_invariants.py`, FAIL on non-zero exit. AUTONOMOUS-EXECUTABLE via nightly review.
**Impact:** Prevents future em-dash regressions, widget drift, from __future__ recurrence, retired plan names, retired field names from reaching commits. Turns one-time manual fixes into automatic enforcement.
**Category:** code_health

---

### Idea 2: E2E integration test for RequirePaid.jsx payment gate
**Evidence:** ff2ca28 (PR #291, 2026-06-16) gated ALL dashboard routes behind RequirePaid.jsx (330L). Existing coverage: 14 backend unit tests (test_pay_gate.py), 68 frontend unit tests (RequirePaid.test.jsx). No E2E test verifies: (a) unpaid tenant sees gate, (b) paid tenant passes through, (c) exempt tenant passes through, (d) grandfathered tenant passes through. This component wraps the entire app — a logic error locks out paying customers.
**Action:** Write e2e/pay-gate.spec.ts covering 4 scenarios: unpaid redirect, paid access, exempt bypass, grandfather pass-through. Wire to pr-check.yml.
**Impact:** Catches regression on the revenue gate before it reaches production. One E2E replaces manual QA on every billing/auth change.
**Category:** code_health / operational

---

### Idea 3: Fix JWT stale plan claims (M3 from launch audit)
**Evidence:** audit-launch-readiness-2026-06-15.md §M3: JWT tokens carry plan_name for 24h. After billing repricing (2 new plan codes: chatbot/agent_os replacing 5-plan model), any tenant token issued before the repricing carries stale plan_name. ai_usage_guard.py enforces per-plan AI caps — a tenant on "agent_os" ($99.99) carrying old "professional" plan claim could hit wrong cap.
**Action:** Add token version field (or force re-issue on plan change) in auth.py. Per-request DB read on /api/* to validate plan against DB. Plan change webhook invalidates cached claims.
**Impact:** Closes window where billing tier mismatch causes wrong AI cap enforcement.
**Category:** code_health / security

---

### Idea 4: Mark GH #181 billing items as moot + apply governance corrections (batch correction)
**Evidence:** billing.py AMOUNT_TO_PLAN completely replaced in 9bed342 (PR #288). Old plan codes (9900/15000/25000/89900) replaced with (1999/9999). Runs 30/31/32/34 all recommended fixing AMOUNT_TO_PLAN — now moot. Runs 55/57 implemented by 3234597. Run 56 superseded by Check 2 in pre-commit. Governance state is significantly inflated vs reality.
**Action:** Apply governance corrections in Phase 6: mark runs 55/57 as implemented, run 56 as superseded, billing runs (30/31/32/34/51) as moot. True pending after corrections: ~6. Moratorium exit closer than governance reflects.
**Impact:** Accurate governance state prevents moratorium from blocking high-value recommendations that should now be freed.
**Category:** workflow

---

### Idea 5: AI-to-Human Handoff v1 — route explicit trigger to owner SMS via os_outbound_mirror
**Evidence:** customer-gaps.md: Critical, all industries, 61 days pending. os_outbound_mirror.py (PR #188, merged 2026-05-27) has SMS/email delivery with 152 tests. widget_chat.py handles chat flow. Trigger strings ("talk to a person", "speak to someone", "call me") could route to os_outbound_mirror.send_sms(). No prior implementation attempt.
**Action:** Add explicit-trigger detection in widget_chat.py (~10-line change) + os_outbound_mirror.route("handoff", tenant_id, lead_context). Update conversations table to track handoff state.
**Impact:** Closes most-requested feature gap across all 7 verticals. Converts lost leads (complex queries) to owner-handled conversations.
**Category:** customer_value
