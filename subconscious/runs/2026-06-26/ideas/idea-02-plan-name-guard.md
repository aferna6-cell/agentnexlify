# Idea 2: Plan-Name New-Gate Guard (Check 7 in check_project_invariants.py)

**Category:** code_health
**Impact:** HIGH (prevents GH #292/#293-class bugs)
**Effort:** S (~20 lines Python)
**Autonomous-executable:** YES (after check exits 0)

## Evidence
- bug-patterns.md (2026-06-23): GH #292/#293 half-migration left 6 gate dicts missing chatbot/agent_os for 7 days post-repricing — all new paid tenants broken
- check_project_invariants.py PASS "retired plan names do not appear" — but NO guard for "new plans appear in all gates"
- Pattern: repricing events are binary (all gates break simultaneously) — 1 guard prevents the whole class
- Run 67 winning-concept.md §Post-Implementation Cascade: "Run 68 candidate: Plan-name invariant guard (Check 7) — AUTONOMOUS-EXECUTABLE"

## Action
Add Check 7 to `scripts/check_project_invariants.py`:
- Scan `_ALLOWED_PLANS|_UNLIMITED_PLANS|_ELIGIBLE_PLANS|_BRANDING_PLAN_FIELDS` and tuple-style plan checks
- Assert both `chatbot` and `agent_os` appear in each discovered gate
- FAIL on violation with file:line hint

## Expected Impact
- Prevents next repricing from silently breaking paid features
- AUTONOMOUS-EXECUTABLE: same mechanism as Check 13 addition (nightly delivers in 1 cycle)
- Sequencing: BLOCKED until check exits 0 — cannot be winner before Idea 1 lands

## Status
**PARKING LOT / RUN 69 CANDIDATE** — sequencing-blocked on Idea 1.
