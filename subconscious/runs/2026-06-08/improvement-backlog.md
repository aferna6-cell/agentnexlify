# Improvement Backlog — 2026-06-08 (Run 52)

## Active

- Verify and merge PR #183 (GH #181 billing fix: AMOUNT_TO_PLAN missing 15000→autopilot + 25000→professional, backwards test assertions) — ~10 min, developer is now active

## Parking Lot (survived debate but not chosen)

- **Item A — Check 10 wire** (run 8, 41 days): Add check_project_invariants.py to pre-commit. 3 lines bash, 5 min. Bonus A for this run. Autonomous path broken — human only.
- **email_sequences.py god-class split** (run 41): 1255L → 3×420L. Blocked until PR #183 merges. /god-class-splitter + /post-split-test-repair both ready.
- **Agent OS widget isolation test** (new, run 52): Read test_os_inbound_bridge.py to confirm parametric os_enabled=False coverage. If absent, add it. 2287f6b proved this bug class is real.
- **Agent OS orchestrator test coverage** (new, run 52): _orchestrator.ts is 414 lines + 20 specialist agents. 236 lines of tests. Verify end-to-end booking → slot → deliverable path is covered.
- **Zapier plan_status enforcement** (run 16, GH #107): backend/services/zapier_auth.py::_get_api_key_client needs plan_status IN ('active','trialing') filter. Route via issue-to-pr-loop.

## Rejected This Run

- **Agent OS widget isolation test as winner** — KILLED round 2: confidence below 80% without reading test_os_inbound_bridge.py; insufficient evidence of coverage gap.

## Questions for Next Run

1. Was PR #183 merged? (grep billing.py for 15000+25000 entries)
2. Was Item A Check 10 wired? (grep pre-commit for check_project_invariants)
3. Was email_sequences.py split invoked? (wc -l backend/routers/email_sequences.py)
4. Agent OS orchestrator — what are the test coverage numbers? Read orchestrate.test.ts.
5. Did the developer switch focus post-Agent-OS-sprint, or are more Agent OS commits landing?
