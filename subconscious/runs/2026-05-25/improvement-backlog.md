# Improvement Backlog — 2026-05-25 (Run 33)

## Active

- Fix GH #181: add `15000→autopilot` + `25000→professional` to `AMOUNT_TO_PLAN`, remove contradictory CI-blocking test assertions. S-effort, ~15 min. Closes GH #181. (Run 33 winner)

## Standing Action (invoke any session)

- Invoke `/moratorium-sprint` — Items A/B/D (~40 min). moratorium-sprint SKILL.md ready. After sprint + governance audit: pending 8→2 = moratorium exits. Unlocks: Zapier security (GH #107, ROI 2.5) + AI-to-Human Handoff (Critical, 39d+).

## Parking Lot (survived debate but not chosen)

- **auth.py god-class refactor** (HIGH priority, post-moratorium) — 1590 lines, 36 functions, PR #180 as template. Extract: stripe_webhook_service.py, tenant_provisioning_service.py, session_service.py. M-effort. First recommendation after moratorium exits + GH #181 closed.
- **test_billing_constants.py** (run 30 winner, still unimplemented) — complement to GH #181 fix. Parametric billing contract tests. Wire into pr-check.yml. Can be done alongside or after GH #181.
- **Zapier API key plan_status enforcement** (GH #107, ROI 2.5, HIGH security) — add `plan_status IN ('active','trialing')` filter to `_get_api_key_client`. 25+ days open. Post-moratorium first security winner.
- **AI-to-Human Handoff v1** (run 4, 39 days, Critical, all 7 industries) — explicit trigger, Twilio SMS to owner, fallback email. Infrastructure exists. Post-moratorium first customer-value winner.
- **email_sequences N+1 fix** (GH #112, ROI 2.3) — bulk `.in_()` query fix. 1001 queries per 1000 enrollments. M-effort.
- **onboarding V2 characterization tests** — write before onboarding sprint resumption.

## Rejected This Run

- **Idea 3 (/moratorium-sprint) as winner** — WEAKENED: commitment bottleneck confirmed after 10+ recommendations. Not killed (action still valid); demoted from winner slot. If not invoked by run 34: escalate to nightly review sprint-execution request.
- **Idea 2 (auth.py refactor) as winner** — WEAKENED: M-effort + moratorium protocol + stabilization period needed after PR #180. Post-moratorium parking lot.

## RUN 34 MANDATE

If GH #181 still unimplemented after run 33 (would be FOURTH consecutive same-winner):
- Governance precedent fires (runs 15/16/17 → run 18 mechanism change)
- Run 34 MUST recommend: authorize nightly review to apply `15000→autopilot` + `25000→professional` as LOW-risk additive dict entries + remove contradictory test assertions as LOW-risk test hygiene
- Nightly review is the execution path — billing.py dict addition is additive, no logic change, verifiable by grep

## Questions for Next Run

1. Has GH #181 been implemented? (grep `15000` in billing.py)
2. Has any moratorium sprint item (A/B/D) been completed?
3. Has auth.py been reduced below 1200 lines? (next refactor target verification)
4. Are the email_sequences N+1 queries (GH #112) still open or fixed?
