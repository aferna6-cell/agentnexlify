# Ideas — Run 2026-06-16-pm (Run 59)

## Evidence Summary

3 days / 8 commits / 990+ lines. Massive retention sprint: 7-day trial system (379b230), trial-end access contract + dunning fix (34b9d0f), conversion funnel analytics + security hardening (47c7f8b), 2-plan pricing reconciliation (3123da0), pay_gate.py signup gate (ff2ca28, PR #291). New billing surface: pay_gate.py, PaymentRecoveryGate.jsx, StripeTrialBanner.jsx, admin_analytics.py, owner_alerts.py.

Run 58 winner (Check 13 wire) is pending_autonomous — nightly 2:37 AM hasn't run since run 58 committed this morning. check_project_invariants.py passes all 6 checks clean. Expected to auto-execute tonight.

KEY GAP: pay_gate.py gates web signup behind payment plan_status. But `backend/services/zapier_auth.py::_get_api_key_client` has NEVER checked plan_status (bug-patterns.md issue #107, filed 2026-04-30, unfixed 47+ days). With 7-day trials NOW live: expired-trial tenant keeps their Zapier API key working indefinitely — pay_gate bypassed via API layer.

---

### Idea 1: Fix Zapier plan_status enforcement (issue #107)
**Evidence:** 7-day trial system launched (379b230 + 34b9d0f, 2026-06-14/15). pay_gate.py gates web access by plan_status. bug-patterns.md documents exact fix: `plan_status IN ('active','trialing')` filter in `_get_api_key_client`. Parking lot ROI 2.5 since run 16 (2026-05-11). Pre-trial, risk was low (only active/cancelled tenants). Post-trial, risk is active: trial expires → tenant retains Zapier access indefinitely.
**Action:** Add `plan_status IN ('active','trialing')` check in `backend/services/zapier_auth.py::_get_api_key_client` (~2-3 lines) + regression test: seed cancelled tenant + valid key, assert 402/403.
**Impact:** Closes revenue leak, aligns Zapier auth with pay_gate, prevents billing bypass for expired-trial tenants. S-effort ~15 min.
**Category:** code_health

---

### Idea 2: Add unit tests for admin_analytics.py (new uncovered endpoint)
**Evidence:** Commit 47c7f8b added `backend/routers/admin_analytics.py` (77 lines, new file). Test files added in same commit: test_conversion_funnel.py (395 lines), test_security_hardening.py (85 lines), test_trial_end_capture.py (106 lines) — but NO `test_admin_analytics.py`. admin_analytics.py provides admin-level billing/conversion metrics; wrong data would cause product decisions based on bad numbers.
**Action:** Create `backend/tests/test_admin_analytics.py` — parametric assertions for each endpoint, mock Supabase returns, verify metric calculations.
**Impact:** Prevents silent regressions in admin billing views; admin analytics are high-stakes for fundraising/investor reporting.
**Category:** code_health

---

### Idea 3: AI-to-Human Handoff v1 (promote from parking lot)
**Evidence:** customer-gaps.md Critical, all 7 industries. os_outbound_mirror.py exists (152 tests, PR #188). pay_gate means real paying customers now exist — when AI fails a paying customer, churn cost is real. Scope reduced to ~1 day (run 38). 62+ days since run 4 filed this.
**Action:** Add explicit trigger detection in widget_chat.py ("speak to a human", "talk to someone", "not helpful"), write to handoff_requests table (new migration), notify owner via os_outbound_mirror.send_sms().
**Impact:** Closes Critical cross-industry gap; directly reduces paying-customer churn.
**Category:** customer_value

---

### Idea 4: Wire check-widget-sync.sh (run 7/50 pending_autonomous, 55+ days MISSING)
**Evidence:** scripts/check-widget-sync.sh MISSING 55+ days. Run 50 extended nightly scope to cover it. Widget copies were synced by 3234597 (run 57 win). But no automated guard — next PR touching widget will create drift again. Check 13 (auto-wiring tonight) already guards widget byte-sync via check_project_invariants.py.
**Action:** Create scripts/check-widget-sync.sh (diff widget/, frontend/public/widget/, landing-page-v2/widget/ → FAIL on diverge), wire into scripts/hooks/pre-push.
**Impact:** Prevents widget drift recurrence; belt-and-suspenders with Check 13.
**Category:** code_health

---

### Idea 5: RequirePaid.jsx multi-PR consistency audit
**Evidence:** RequirePaid.jsx touched in 3 separate PRs in 3 days (#295, #301; also StripeTrialBanner touched by #299 + #300 + #301). Multiple overlapping edits to billing gate components = inconsistency risk. Edge: trial → expired → recovery → reactivation flow through 3 components.
**Action:** Read RequirePaid.jsx, PaymentRecoveryGate.jsx, StripeTrialBanner.jsx; verify consistent handling of: active, trialing, past_due, cancelled, unpaid states.
**Impact:** Prevents edge-case billing leaks from component state divergence.
**Category:** code_health
