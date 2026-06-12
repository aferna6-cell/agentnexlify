# Improvement Backlog — 2026-06-12

## Active
- Add pre-commit Check 13: `from __future__ import annotations` guard in FastAPI files (FAIL mode, ~10 lines bash, AUTONOMOUS-EXECUTABLE) — run 56 winner

## Also Pending Autonomous (run 55)
- Fix `from __future__ import annotations` in all 4 files (channels_instagram.py, auth_password_reset.py, auth_billing.py, auth_google.py) + fix 10 em-dash violations → exits 0 → Check 10 auto-wires (run 55, pending_autonomous, NOT superseded)

## Parking Lot (survived debate but not chosen)
- Fix `from __future__` in 4 files + 10 em-dashes as run 56 winner — WEAKENED (mechanism uncertain for Python edits via nightly; remains valid as bonus action or human-execute)
- Cross-tenant isolation tests for os_graph_memory.py — ROI 2.1 (security, AUTONOMOUS-EXECUTABLE)
- Fix kb-autopopulate.sh agent-browser → WebFetch fallback — ROI 1.8 (operational, 35+ days broken)
- Home.jsx god-class split (1171L → HeroSection + FeaturesSection + CTASection) — HUMAN-REQUIRED, M-effort
- email_sequences.py god-class split (1255L → email_crud + email_enrollment + email_processor) — run 41 winner, pending_approval
- Widget 3-Copy Sync Guard (check-widget-sync.sh + pre-push) — run 7/50, pending_autonomous, 50+ days

## Critical Standing Actions (human-required, not subconscious winners)
- GH #181: Add 15000→autopilot + 25000→professional to AMOUNT_TO_PLAN in backend/routers/billing.py (~15 min, rejected_paths governance, human required)
- AI-to-Human Handoff v1 (explicit trigger, Twilio SMS, ~1 day) — run 4, 57+ days, Critical across all industries

## Rejected This Run
- Idea 2 (fix 4 files + em-dashes as run 56 winner) — WEAKENED: mechanism uncertain for nightly Python edits; superseded by Check 13 as systemic fix; run 55 pending_autonomous already covers this
- Idea 3 (cross-tenant isolation tests) — WEAKENED: lower urgency than active 422 violations; parking lot ROI 2.1 stands

## Questions for Next Run
1. Was Check 13 added by nightly tonight? Grep `scripts/hooks/pre-commit` for "Check 13"
2. Was run 55 winner (fix from __future__ + em-dashes) implemented? Run check_project_invariants.py
3. Did Check 10 auto-wire after invariants exited 0?
4. Any new router splits introduced additional `from __future__` violations?
