# Ideas — Run 33 (2026-05-25)

**Evidence digest:**
- GH #181 still open: `AMOUNT_TO_PLAN` missing `15000→autopilot` + `25000→professional`. Two consecutive runs (31+32) recommended this fix. Test file (`test_billing_amount_to_plan.py`) has contradictory assertions (`test_no_wrong_15000_mapping`, `test_no_wrong_25000_mapping`) actively blocking any correct fix from CI green.
- PR #180 MERGED (2174732): god-class refactor — 13 new service files, 135 new tests, 31 files changed. auth.py at 1590 lines (next logical target per god-class-refactor_plan.md).
- Nightly review 2026-05-25 confirmed PR #180 clean on all invariants. No new bugs found.
- Sprint Items A/B/D: ALL MISSING — check_project_invariants.py not in pre-commit, check-widget-sync.sh missing, lead-qualifier-eval.yml missing. But check_project_invariants.py PASSES widget byte-identical check when run manually.
- test_billing_constants.py (run 30 winner): NOT created.
- Moratorium still active. True pending ≈ 4-5 (superseded items inflate raw count to 8).

---

### Idea 1: Fix GH #181 — Add 15000 + 25000 to AMOUNT_TO_PLAN and fix contradictory tests

**Evidence:** Runs 31 AND 32 both identified this as the highest-urgency item. AMOUNT_TO_PLAN confirmed missing 15000→autopilot and 25000→professional via direct inspection (grep of billing.py line 263-280). Two consecutive billing commits (1eaaeec, c72b535) missed these entries — confirming non-obvious without explicit guidance. 1553bf7 wired the contradictory tests into CI — now `test_no_wrong_15000_mapping` will cause CI to fail on any developer who correctly adds the missing entries. Nightly review 2026-05-25 explicitly deferred this to human approval (MEDIUM billing risk). GH #181 documents exact fix.

**Action:** Add `15000: "autopilot"` and `25000: "professional"` to `AMOUNT_TO_PLAN` in `backend/routers/billing.py:263`; remove `test_no_wrong_15000_mapping` and `test_no_wrong_25000_mapping` from `test_billing_amount_to_plan.py`; add positive correctness assertions; update docstring.

**Impact:** Fixes silent billing misclassification for tenants paying $150/mo (autopilot) and $250/mo (professional) who have no `metadata.plan`. CI returns to honest signal. GH #181 closes. Prevents future revert-by-mistake from confused developers seeing CI red on a correct fix.

**Category:** code_health

---

### Idea 2: auth.py god-class refactor — extract services from 1590-line routing file

**Evidence:** PR #180 (2174732) merged with 13 new service files as template. auth.py at 1590 lines post-refactor (nightly review noted: "Worth a dedicated refactor sprint per #180 follow-up"). god-class-refactor_plan.md created in run 30 timeframe with 54 targets. PR #180 proves the pattern: extract services → stub router calls → ship 135 new tests. auth.py has 36 functions — candidates include `_verify_stripe_webhook`, `_process_subscription_change`, `_create_tenant_record`, `_handle_onboarding`. Rule 9: >600 lines + adding new concern → split first.

**Action:** Create `backend/services/stripe_webhook_service.py`, `backend/services/tenant_provisioning_service.py`, `backend/services/session_service.py`. Move relevant functions. Update auth.py to delegate. Add tests for extracted services (mirror test_extracted_services.py pattern).

**Impact:** auth.py drops below 1000 lines. Each extracted service becomes independently testable. Reduces blast radius when Stripe webhook logic needs changing. Continues the god-class elimination sprint begun by #180.

**Category:** code_health

---

### Idea 3: Invoke /moratorium-sprint — execute Items A+B+D in one session

**Evidence:** moratorium-sprint SKILL.md created by nightly review (7985fbb, 2026-05-19). Item C completed autonomously (2ce31b2, 2026-05-20). Items A/B/D confirmed MISSING today. Item A (check_project_invariants pre-commit): 3-line addition, script already PASSES all 6 checks. Item B (check-widget-sync.sh): ~15 min, though check_project_invariants already catches widget divergence. Item D (lead-qualifier-eval.yml): ~20 min CI addition. Sprint has been recommended 10+ times interactively. moratorium-sprint tool exists and is ready.

**Action:** Invoke `/moratorium-sprint` in an interactive session — executes Items A+B+D (~40 min total), opens draft PR. After merge: pending 8→5→2 (with governance audit) = moratorium exits.

**Impact:** Moratorium exits. Unlocks free-choice runs: Zapier security (GH #107, ROI 2.5), AI-to-Human Handoff (run 4, 39 days, Critical). 40 minutes of committed time eliminates the recommendation loop that has lasted 33 runs.

**Category:** workflow

---

### Idea 4: Create test_billing_constants.py — billing contract tests as standalone deliverable

**Evidence:** Run 30 winner (2026-05-22-pm) recommended this. Still not created. c72b535 (run 30 trigger) fixed live billing bug but missed 15000+25000 — proves ad-hoc fixes without contract tests will miss entries. GH #181 is STILL open as proof. If test_billing_constants.py had existed before c72b535, the CI would have caught the omission. Current test_billing_amount_to_plan.py is misleading (contradictory assertions). A new contract test file would be immune to the issue-#81-era confusion.

**Action:** Create `backend/tests/test_billing_constants.py` with parametric assertions for all 5 current plans × documented CLAUDE.md prices. Wire into pr-check.yml. Complement (not replace) the GH #181 test fix.

**Impact:** Prevents future billing dict omissions. Parameterized over CLAUDE.md plan prices so it self-documents the source of truth. But: incomplete without GH #181 fix (contradictory tests would still block CI green).

**Category:** code_health

---

### Idea 5: Zapier API key plan_status enforcement — fix GH #107 security gap

**Evidence:** Parking lot ROI 2.5 since run 16. GH #107 has been open 25+ days. `backend/services/zapier_auth.py::_get_api_key_client` resolves keys without plan_status check. Cancelled tenants with un-revoked keys bypass tier gating. Test coverage exists (test_zapier_auth.py). Pattern is clear: add `plan_status IN ('active','trialing')` filter. Moratorium restricts winner slot but this item is independently valid security work. Run 30 freed to recommend this (post god-class sprint) — but moratorium still active.

**Action:** Add `plan_status` filter to `_get_api_key_client` query. Add regression test to test_zapier_auth.py. Close GH #107.

**Impact:** Prevents cancelled tenant API access. HIGH security ROI. Closes a known bypass. But moratorium protocol requires oldest-pending prioritization — this would leapfrog pending items from runs 7/8/14.

**Category:** code_health / security
