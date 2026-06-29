# Idea 02 — Record Audit Dashboard

**Category:** customer_value  
**Effort:** S (~3-4 hours, mirrors SMS Compliance Dashboard pattern)  
**Moratorium-safe:** NO — human-required, adds to pending queue  
**AUTONOMOUS-EXECUTABLE:** NO  

## Evidence

- `backend/services/record_audit.py` exists (council sprint fix, 2026-06-24)
- No frontend page, no operator UI for record audit trail
- Nightly 2026-06-29 backlog: "Record Audit Dashboard (run 72 candidate)"
- SMS Compliance Dashboard (run 70 winner) is same pattern: backend exists → add endpoint + React page
- agent_os plan tier tenants need visibility into AI-generated records

## What It Would Build

- `GET /api/record-audit/summary` endpoint in `backend/routers/record_audit.py`
- `frontend/src/pages/RecordAuditPage.jsx` — summary cards, recent AI-generated records table, date-range filter
- Route in `frontend/src/App.jsx`
- Sidebar entry in `frontend/src/components/Sidebar.jsx`

## Moratorium Constraint

Run 70 winner (SMS Compliance Dashboard) is still pending_approval. Adding a second human-required dashboard item while first is unimplemented worsens the queue. Nightly's own forecast was "run 72 candidate" — meaning it expects SMS Dashboard to be implemented first. Moratorium still active (true_pending ~6 > max_pending_approvals: 2).

## Assessment

Valid idea, wrong timing. Blocked behind SMS Compliance Dashboard. Re-evaluate when run 70 is implemented.
