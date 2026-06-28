# Idea 01: SMS Compliance Dashboard

**Category:** Customer Value + Operational  
**Effort:** ~1 day  
**Priority:** HIGH

---

## The Opportunity

Council fix #1 (commit `9ddfd0e`, Jun 27) landed TCPA opt-out suppression in the backend. `leads.sms_opted_out` is populated. The enforcement exists. The visibility does not.

Tenants currently have no way to see:
- How many leads have opted out
- When opt-outs occurred
- Which campaigns triggered opt-outs
- Whether their send volume is within safe TCPA thresholds

TCPA penalty exposure: **$500–$1,500 per unsolicited message**. A tenant sending 50 SMS to opted-out leads = $25k–$75k liability. They cannot manage risk they cannot see.

---

## Evidence

- `9ddfd0e` — TCPA opt-out suppression, Jun 27 (backend enforcement exists)
- `docs/dev-knowledge/customer-gaps.md` — SMS compliance visibility listed as open gap
- `knowledge-base/wiki/regulations/tcpa-compliance.md` — TCPA penalties documented
- GoHighLevel: has SMS compliance reporting in their Reporting tab (competitive gap)
- Recharts already installed in frontend (`package.json`)
- No migration needed — all data already in `leads.sms_opted_out` + message logs

---

## Recommended Implementation

**Backend** (`backend/routers/sms_compliance.py` — new file):
- `GET /api/sms-compliance/summary` — opt-out count, opted-out %, trend (7/30/90 days)
- `GET /api/sms-compliance/opted-out-leads` — paginated list, `client_id` scoped

**Frontend** (`frontend/src/pages/SMSCompliance.jsx` — new file):
- Recharts `<AreaChart>` — opt-out trend by week
- `<StatCard>` row — total opt-outs, rate, sends blocked
- `<DataTable>` — opted-out leads with timestamp
- Route: `/dashboard/sms-compliance`
- Sidebar entry under "Compliance"

---

## Constraints

- `client_id` not `tenant_id` on all queries
- No `from __future__ import annotations` in new router
- Feature gated to `agent_os` plan (SMS is agent_os gate)
- New Pydantic models for response shapes

---

## Why Now

Backend enforcement landed 24 hours ago. Adding visibility now completes the feature. Without visibility, tenants can't prove compliance during audits. GoHighLevel has this. We don't. Gap is documented.
