# Improvement Backlog — 2026-05-26 (Run 34)

## Active

- **Fix GH #181** — Add `15000: "autopilot"` and `25000: "professional"` to `AMOUNT_TO_PLAN` in `backend/routers/billing.py:264`; update `test_billing_amount_to_plan.py` (remove backwards issue-#81-era asserts, add current-price asserts). S-effort ~15 min. Governance mandate run 34. File locations: billing.py:264 + test_billing_amount_to_plan.py:38-44.

## Parking Lot (survived debate but not chosen this run)

- **/moratorium-sprint** — Items A (check_project_invariants pre-commit ~5 min) + B (widget sync guard ~15 min) + D (CI eval workflow ~20 min). SKILL.md ready (7985fbb). Moratorium day 21+. Strong bonus action after GH #181. If done: pending → moratorium exit.
- **Split email_sequences.py** — 1255L, 2 concerns (CRUD vs sending), god-class-splitter SKILL.md ready. First production use of the new skill. GH #112 (N+1) + GH #113 (duplication) both point here. Post-moratorium candidate. ROI 1.8.
- **Zapier plan_status enforcement** — GH #107, ROI 2.5, cancelled tenants bypass tier gate. S-effort ~20 min + test. Post-moratorium first security fix. `backend/services/zapier_auth.py::_get_api_key_client`.
- **AI-to-Human Handoff v1 GH issue** — 3x recommended without action, demoted per run 30 governance. Revisit post-moratorium. Critical gap 40+ days. customer-gaps.md all industries. Spec in `subconscious/runs/2026-05-21-pm/winning-concept.md`.
- **billing-constant-guard skill** — parking lot ROI 2.1. Unblocked after GH #181 fix. 10-step checklist for any billing constant change.

## Rejected This Run

*(none — all ideas survived to parking lot or winner)*

## Questions for Next Run (Run 35)

1. Has GH #181 been implemented? (4-consecutive-run mandate fire — confirm fix or governance log the non-implementation)
2. Was /moratorium-sprint invoked as bonus action? If yes: has pending dropped to ≤2 (moratorium exit)?
3. Has `test_billing_amount_to_plan.py` CI run successfully with the new positive assertions?
4. Is email_sequences.py (1255L) ready as the first /god-class-splitter target post-moratorium?
5. What is the Zapier plan_status fix status (GH #107)? If moratorium exits, this is the first security fix.
