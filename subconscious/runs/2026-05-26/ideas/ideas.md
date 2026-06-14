# Ideas — Run 34 (2026-05-26)

## Context

- Run 33 winner (god-class-splitter skill) IMPLEMENTED autonomously by nightly review e848b87 (2026-05-26)
- GH #181 billing fix: 4th consecutive recommendation → governance mandate fires this run
- Moratorium items A/B/D all MISSING — day 21+
- AMOUNT_TO_PLAN confirmed: 15000 and 25000 absent; CI actively certifies broken state via issue-#81-era tests
- email_sequences.py: 1255L (god-class candidate with new skill ready)

---

### Idea 1: Fix GH #181 — Add 15000→autopilot + 25000→professional to AMOUNT_TO_PLAN + fix contradictory CI tests

**Evidence:**
- Direct read of `backend/routers/billing.py:263-290`: `AMOUNT_TO_PLAN` has 9900 (growth) and 89900 (enterprise), but 15000 ($150/mo autopilot) and 25000 ($250/mo professional) are absent.
- `backend/tests/test_billing_amount_to_plan.py:38-44`: `test_no_wrong_15000_mapping` asserts `15000 not in AMOUNT_TO_PLAN`; `test_no_wrong_25000_mapping` asserts `25000 not in AMOUNT_TO_PLAN`. These are issue-#81-era tests (a past bug where wrong mappings existed) now backwards — CI certifies the gap as correct behavior.
- Three prior runs (31, 32, 33) all recommended this fix. Run 33 governance signal explicitly set 4-consecutive-run threshold. Run 34 mandate fires.
- `c72b535` (billing fix attempt 2026-05-22) removed wrong legacy entries but omitted current-price entries.
- `1eaaeec` (second fix attempt 2026-05-23) still missed 15000 and 25000 — confirms the fix is non-obvious without the failing tests guiding it.
- `1553bf7` (nightly review 2026-05-23) wired `test_billing_amount_to_plan.py` into CI — the contradictory tests now block any correct fix from turning CI green.

**Action:**
1. `backend/routers/billing.py`: add `15000: "autopilot"` and `25000: "professional"` to `AMOUNT_TO_PLAN` dict (line ~264).
2. `backend/tests/test_billing_amount_to_plan.py`: remove `test_no_wrong_15000_mapping` (line 38-41) and `test_no_wrong_25000_mapping` (line 42-44). Add `test_current_autopilot_pricing_150` and `test_current_professional_pricing_250` asserting keys DO exist with correct values. Update `test_all_four_current_tiers_present` to assert `{9900, 15000, 25000, 89900}`.

**Impact:** Stripe webhook amounts of 15000 and 25000 correctly resolve to autopilot/professional. CI stops certifying the broken state. Closes GH #181. Unblocks `billing-constant-guard` skill (parking lot). Prevents a third failed fix attempt.

**Category:** code_health

---

### Idea 2: Invoke /moratorium-sprint — Items A (check_project_invariants pre-commit) + B (widget sync guard) + D (CI eval workflow)

**Evidence:**
- `scripts/check-widget-sync.sh` MISSING (confirmed today). `lead-qualifier-eval.yml` MISSING (confirmed today).
- `check_project_invariants.py` not wired into pre-commit (grep returned 0 results).
- moratorium-sprint SKILL.md exists (7985fbb, validated). Items A+B+D unchanged from run 25 description.
- Moratorium day 21+. pending ≥ 8.

**Action:** Invoke `/moratorium-sprint` in this interactive session (~40 min).

**Impact:** After PR merge: pending 8→4→2, moratorium exits. Unblocks all future free-choice subconscious runs.

**Category:** workflow

---

### Idea 3: Split email_sequences.py (1255L) — first production use of god-class-splitter

**Evidence:**
- `wc -l backend/routers/email_sequences.py` = 1255 (2x the 600-line Rule 9 threshold).
- god-class-splitter SKILL.md created 12h ago (e848b87). Immediate first use validates the skill.
- GH #112 (N+1 query in `list_enrollments`) and GH #113 (duplicated `_process_pending_sends` loop) both point to this file — two independent bugs in one god class.
- Parking lot entry (ROI 1.8) explicitly notes this as a split candidate.
- Two clear concerns: (1) sequence + enrollment CRUD, (2) email sending + scheduling execution.

**Action:** Invoke `/god-class-splitter` on `email_sequences.py` → extract `email_sequences_service.py` (CRUD/enrollments) and `email_sender.py` (sending/scheduling) → update all importers → smoke tests.

**Impact:** GH #112 N+1 fix becomes isolated. GH #113 duplication resolvable. Validates god-class-splitter skill. 20-40 min.

**Category:** code_health

---

### Idea 4: AI-to-Human Handoff v1 — create GH issue with full implementation sketch

**Evidence:**
- `customer-gaps.md`: "Critical for complex queries" across all industries. Oldest pending item (run 4, 40+ days).
- conversations.py at 50L — minimal. Infrastructure exists (conversations table, Twilio, Resend, lead status column).
- Run 21 + run 29 both recommended creating a GH issue. Neither was implemented.

**Action:** Create GH issue `feat(widget): AI-to-Human Handoff v1 — explicit trigger` with implementation sketch: trigger strings, Twilio SMS to owner, fallback email, lead status `needs_follow_up`. Labels: customer-value, widget, backend, ai-ready.

**Impact:** Oldest pending item gets a structured GH issue. Closes run 4 + run 21 + run 29 via one document. 5 min.

**Category:** customer_value

---

### Idea 5: Zapier plan_status enforcement — add active/trialing filter to zapier_auth.py

**Evidence:**
- GH #107 open 26+ days. `backend/services/zapier_auth.py::_get_api_key_client` resolves API keys without checking `plan_status`.
- Cancelled tenants with un-revoked Zapier keys bypass the plan tier gate.
- ROI 2.5 — highest-ROI item in parking lot after god-class work.
- Security classification: cancelled user maintains integration access indefinitely until key manually revoked.

**Action:** Add `plan_status IN ('active', 'trialing')` filter to `_get_api_key_client` query + regression test asserting cancelled tenant's key is rejected.

**Impact:** Security gap closes. GH #107 resolved. S-effort ~20 min.

**Category:** code_health / security
