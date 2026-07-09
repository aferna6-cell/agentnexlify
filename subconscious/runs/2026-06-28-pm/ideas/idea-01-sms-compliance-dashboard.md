# Idea 01 — SMS Compliance Dashboard

**Category:** Customer Value / Operational  
**Effort:** S (1 endpoint + 1 React page, ~3-4 hours)  
**Confidence:** HIGH  
**Prior debate score:** 12/12 (run 69)  
**Moratorium interaction:** Adds 1 pending_approval — net change within limit if run 69 widget direction resolves.

---

## The Gap

Council fix #1 (sms_compliance.py + migration 160) shipped 2026-06-24. Backend:
- `sms_compliance_log` table exists
- TCPA-compliant opt-in/opt-out tracking implemented
- SMS sending gated behind compliance check
- Audit trail written on every send

No visibility page exists. Business owners cannot:
- See opt-in rates across their subscriber list
- Identify contacts who opted out (and why)
- Verify TCPA compliance status before a campaign
- Audit SMS send history

This is a legal and operational risk: the data exists, but it is invisible.

---

## What to Build

### Backend (1 endpoint)
`GET /api/sms/compliance-summary` → returns:
- Total contacts with SMS opt-in
- Total opted-out (with reason breakdown: STOP/UNSUBSCRIBE/manual)
- Messages sent last 30 days
- Compliance rate (opt-ins / total SMS-enabled leads)
- Last 10 opt-out events (contact, reason, timestamp)

```python
@router.get("/sms/compliance-summary")
async def sms_compliance_summary(client_id: str = Depends(get_client_id)):
    # Query sms_compliance_log table
    # Group by status, reason, date
    # Return summary + recent events
```

### Frontend (1 page)
`frontend/src/pages/SMSCompliancePage.jsx`
- Compliance health card (green/yellow/red based on opt-out rate)
- Opt-in/opt-out counts with trend chart (last 30 days)
- Recent opt-out event log (table: contact, reason, timestamp)
- Export button (CSV of opted-out contacts)
- "How TCPA works" explainer tooltip

### Sidebar entry
`SMS Compliance` under the `Channels` section in `Sidebar.jsx`.

---

## Why This Wins

1. **Backend is ready** — migration 160 + sms_compliance.py already exist. No schema changes.
2. **Legal liability** — business owners need to prove compliance. Invisible data = unenforceable protection.
3. **S-effort** — 1 endpoint + 1 page. Independent of all other work.
4. **Immediate customer value** — any business sending SMS needs this before a campaign.
5. **Council sprint coherence** — natural deliverable of fix #1. Closes the loop.

---

## Implementation Sketch

Files:
- `backend/routers/sms.py` — add `GET /compliance-summary` endpoint
- `frontend/src/pages/SMSCompliancePage.jsx` — new page
- `frontend/src/App.jsx` — add route
- `frontend/src/components/Sidebar.jsx` — add nav entry

No migrations needed. No schema changes. Uses existing `sms_compliance_log` table.

Test: `backend/tests/test_sms_compliance_summary.py` — mock compliance log, assert endpoint returns correct summary.

---

## Risks

- None significant. Read-only endpoint + new page. No existing behavior modified.
