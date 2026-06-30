# Idea 1: SMS Compliance Dashboard

**Run:** 73 | **Date:** 2026-06-30 | **Score:** 12/12 (from run 70 council)

## One-line
Ship the SMS Compliance Dashboard — 1 endpoint + 1 page — using the backend already merged in council sprint.

## Background
- Run 70 winner with 12/12 council score. `sms_compliance.py` + migration 160 merged.
- Backend: `backend/services/sms_compliance.py` (opt-out tracking, TCPA window enforcement, consent logging) — DONE.
- Frontend + API: NOT DONE. 1 endpoint + 1 dashboard page outstanding.
- Sits at `pending_approval` since run 70 (~10+ days idle).
- Zero production SMS code shipped in 7+ days.

## Evidence
- `docs/dev-knowledge/customer-gaps.md`: AI-to-Human Handoff listed Critical; SMS compliance not listed (assumed covered by backend) — confirms urgency to complete the loop.
- `docs/dev-knowledge/bug-patterns.md`: CAN-SPAM unsubscribe swallowed silently — opt-out list not visible without a UI. Pattern confirmed.
- Regulatory: TCPA fines $500–$1500 per message. Any tenant sending SMS without visible compliance tooling is a liability.
- Competitive: GoHighLevel surfaces opt-out counts in sub-account dashboard. We have the data — not surfaced yet.

## What it involves
1. **1 backend endpoint**: `GET /api/sms/compliance/summary` — return opt-out count, consent logs, TCPA-window violations for the authenticated tenant.
2. **1 frontend page**: `frontend/src/pages/SmsCompliance.jsx` — dark theme, shows opt-out rate, blocked sends, consent log table. Sidebar entry under Settings or Contacts.

## Effort
- S (Small) — 2–4 hours. Backend logic done. Standard CRUD endpoint + standard dashboard page pattern.
- Files: `backend/routers/sms.py` or new `sms_compliance_router.py` + `frontend/src/pages/SmsCompliance.jsx` + `frontend/src/App.jsx` route + `frontend/src/components/Sidebar.jsx`

## Risk
- LOW. All new files. No existing behavior changed. No migration needed (migration 160 done).
- Widget zero-touch. Plan names zero-touch.

## Why now
- Backend shipped and cooling → technical debt if left incomplete.
- TCPA exposure grows each day without visible compliance tooling.
- S-effort: fits one session without compound-engineering overhead.
- Moratorium concern minimal: S-effort, NOT adding new items to human approval queue (this IS the pending item).

## Score (12/12 from run 70 — reconfirmed)
| Criterion | Score |
|-----------|-------|
| Customer value | 4/4 — TCPA protection, op-out visibility |
| Implementation risk | 3/3 — backend done, standard UI |
| Ops alignment | 3/3 — completes a shipped backend |
| Effort ratio | 2/2 — S (2–4h) |
| **Total** | **12/12** |
