# Ideas — Run 33 (2026-05-24)

## Evidence Digest

- **GH #181 still open** — AMOUNT_TO_PLAN confirmed missing `15000` ($150/mo autopilot) and `25000` ($250/mo professional). Three commits since issue filed (c72b535, 1eaaeec, 2174732) without fixing. CI booby-trap confirmed: `test_no_wrong_15000_mapping` and `test_no_wrong_25000_mapping` still assert these keys should NOT exist.
- **2174732 god-class refactor landed** — 5,038+/2,064- lines, 13 new service files, 5 new test files. Coverage pattern confirmed for dashboard_service + conversations_service (26 matches in test_extracted_services.py). But faq_service.py (74L), industry_faqs.py (415L), and widget_config_service.py (62L) have no confirmed test coverage.
- **Moratorium sprint Items A/B/D still MISSING** — day 19+. check-widget-sync.sh MISSING, lead-qualifier-eval.yml MISSING, check_project_invariants.py NOT in pre-commit. Pending = 8 (after governance audit).
- **Run 32 questions answered**: (1) test_extracted_services.py DOES cover dashboard_service + conversations_service — strike from parking lot; (2) GH #181 NOT implemented; (3) Sprint items A/B/D all MISSING.

---

### Idea 1: Fix GH #181 — Add 15000→autopilot + 25000→professional to AMOUNT_TO_PLAN and fix CI-blocking tests

**Evidence:** Direct inspection confirms AMOUNT_TO_PLAN has {9900, 89900} only under "current pricing" comment. test_billing_amount_to_plan.py lines 38 and 42 assert these keys MUST NOT exist. Nightly review 1553bf7 wired these contradictory tests into CI on 2026-05-23 — now a daily trap. Three commits since GH #181 filed without applying the fix, confirming it needs explicit guidance.

**Action:** billing.py add `15000: "autopilot"` and `25000: "professional"`. test file: remove test_no_wrong_15000_mapping + test_no_wrong_25000_mapping, add test_current_autopilot_pricing_150 + test_current_professional_pricing_250, update test_all_four_current_tiers_present to use {9900,15000,25000,89900}. ~15 min.

**Impact:** CI green on correct billing code. Stripe webhook `_resolve_plan()` correctly resolves $150/$250 tenants. Closes GH #181. Pre-commit billing sentinel (Check 11) can follow.

**Category:** code_health

---

### Idea 2: Invoke /moratorium-sprint — Items A+B+D (~40 min), draft PR, moratorium exits

**Evidence:** Items A (check_project_invariants pre-commit), B (widget sync guard), D (CI eval workflow) all MISSING for 19+ days. moratorium-sprint SKILL.md ready (7985fbb). Pending = 8 (runs 4, 20, 21, 28, 29, 30, 31, 32). After sprint + governance: pending 8→4→2 = moratorium exits.

**Action:** Run /moratorium-sprint in interactive session. Three sequential items (~40 min total). Opens draft PR.

**Impact:** Moratorium exits. Pre-commit Check 10 live. Widget sync guard enforced. CI eval workflow running weekly.

**Category:** workflow

---

### Idea 3: faq_service.py + industry_faqs.py smoke tests — coverage gap from 2174732 refactor

**Evidence:** 2174732 added 13 new service files. Five test files cover 10 of them (confirmed). faq_service.py (74L) and industry_faqs.py (415L) have no dedicated coverage. Other services from same refactor (dashboard, conversations, facebook, pipeline, social_media) all have explicit test files. industry_faqs.py drives tenant FAQ content in widget AI responses — silent regression means wrong FAQ answers to customers.

**Action:** Add backend/tests/test_faq_service.py covering faq_service.py function calls + industry_faqs.py content generation. Or extend test_extracted_services.py. ~30 min.

**Impact:** Completes 2174732 coverage pattern. Guards widget AI FAQ quality. Prevents silent regression in customer-facing FAQ delivery.

**Category:** code_health

---

### Idea 4: widget_config_service.py smoke test — small but widget-critical service uncovered

**Evidence:** 2174732 created widget_config_service.py (62 lines). No test file. widget_config_service extracts configuration for the embedded chat widget. A config extraction bug silently breaks widget behavior for tenants (wrong colors, branding, etc.) — no test = no signal.

**Action:** Add 3-5 smoke tests for widget_config_service.py to test_extracted_services.py. ~15 min.

**Impact:** Guards tenant widget configuration. Fits the established test pattern from 2174732.

**Category:** code_health

---

### Idea 5: Add AMOUNT_TO_PLAN price mapping to CLAUDE.md §"Plan names + prices" section

**Evidence:** Three commits (c72b535, 1eaaeec, pending GH #181) have missed the same dict entries. The current CLAUDE.md §"Plan names + prices" shows "$150/mo autopilot" but does NOT mention AMOUNT_TO_PLAN or the fact that 15000 must be present. The disconnect between the pricing table and the billing constant is the root cause of three failed fixes.

**Action:** Add a one-sentence note under the plan-prices section: "AMOUNT_TO_PLAN in billing.py must contain {9900, 15000, 25000, 89900} — these are the canonical current-price keys for Stripe webhook resolution." ~5 min.

**Impact:** Prevents fourth billing regression. Future developers reading CLAUDE.md will know to check AMOUNT_TO_PLAN. Root cause fix for the pattern.

**Category:** code_health / workflow
