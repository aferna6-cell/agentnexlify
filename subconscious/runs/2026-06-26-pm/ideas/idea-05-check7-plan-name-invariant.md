# Idea 05 — Add Check 7 (Plan-Name Invariant Guard) to check_project_invariants.py

**Category:** code_health  
**Autonomous:** true — AUTONOMOUS-EXECUTABLE  
**Confidence:** HIGH  
**Effort:** XS (~20 lines Python, sequencing-blocked)

## Summary
Plan-name invariant guard has been in the parking lot since run 65 (2026-06-24). The idea: add Check 7 to `scripts/check_project_invariants.py` that validates plan names referenced in plan-related code files (`ai_usage_guard.py`, `billing_reconciliation.py`, `sms_rate_limiter.py`, `api_key_auth.py`) match the canonical set (`chatbot`, `agent_os` plus grandfathered `growth`, `autopilot`, `professional`, `enterprise`). This would catch the exact class of bug from the repricing half-migration (GH #292/#293, fixed 2026-06-23) before it reaches production next time.

## Evidence
- `bug-patterns.md`: "Repricing half-migration (2026-06-23): plan names (#292/#293) — api_key_auth._ALLOWED_PLANS + sms_rate_limiter._UNLIMITED_PLANS and 4 other gates missing chatbot/agent_os. 2 weeks undetected."
- `check_project_invariants.py` already has 6 checks; adding Check 7 is ~20 lines following the same pattern
- `test_plan_gating_new_plans.py` exists as a test companion — runtime guard — but no static analysis guard at pre-commit

## Sequencing Blocker
**Cannot add Check 7 while check_project_invariants.py exits 1.** If Check 7 is added before the widget drift + em-dash failures are fixed (run 65 winner), the pre-commit block stays and Check 7 is never reached. Must be sequenced AFTER run 65 implementation.

## Status
Parking lot. Run 69/70 candidate after run 65 winner implemented. AUTONOMOUS-EXECUTABLE — same class as Checks 10/11/12/13 (all delivered autonomously by nightly review). Promote when check exits 0.
