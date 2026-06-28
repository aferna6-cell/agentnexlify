# Winning Concept — Run 70 (2026-06-28)

## SMS Compliance Dashboard

**Confidence:** HIGH  
**Effort:** ~1 day  
**Category:** Customer Value + Operational  
**Plan Gate:** `agent_os`

---

## Why This Won

Council fix #1 (`9ddfd0e`, Jun 27) landed TCPA opt-out suppression. The backend enforces it. The database records it (`leads.sms_opted_out`). Tenants cannot see it.

TCPA exposure: $500–$1,500 per unsolicited message. A tenant sending 50 SMS to opted-out leads = $25k–$75k liability. Visibility before the first audit notice is the product value.

GoHighLevel ships SMS compliance reporting. We do not. This run closes that gap.

---

## What to Build

### Backend (new file: `backend/routers/sms_compliance.py`)

```python
# GET /api/sms-compliance/summary
# Returns: opted_out_count, opted_out_rate, sms_blocked_count, trend_by_week[]
# Scoped by client_id (NOT tenant_id)
# Gate: agent_os plan required

# GET /api/sms-compliance/opted-out-leads  
# Returns: paginated lead list with opt-out timestamps
# Scoped by client_id
```

Register in `backend/main.py` (lines 746–813 per CLAUDE.md).

### Frontend (new file: `frontend/src/pages/SMSCompliance.jsx`)

```
Page: /dashboard/sms-compliance
Gate: agent_os plan check (redirect if chatbot)

Layout:
- Stat row: [Total Opt-outs] [Opt-out Rate] [SMS Blocked This Month]
- AreaChart (Recharts): opt-outs per week, last 12 weeks
- DataTable: opted-out leads, name + phone (masked) + opt-out date
```

Add sidebar entry in `frontend/src/components/Sidebar.jsx` under "Compliance" section.

### Tests

```
backend/tests/test_sms_compliance.py:
- agent_os tenant → 200 + data
- chatbot tenant → 403
- client_id scoping — tenant A cannot see tenant B data
- opted-out leads excluded from summary (not double-counted)
```

---

## Constraints

- `client_id` not `tenant_id` — hard invariant, 3+ past production bugs
- No `from __future__ import annotations` in router file
- No new migration — all data already in `leads.sms_opted_out`
- Pydantic models for request/response shapes
- Recharts `<AreaChart>` component (already installed)
- Dark theme consistent with existing dashboard pages

---

## Bonus A (Bundle This Week)

**Zapier plan_status enforcement — GH #107**  
File: `backend/services/zapier_auth.py`  
Change: add `plan_status in ("active", "trialing")` check after API key validation  
Test: `backend/tests/test_plan_gating_new_plans.py` — expired → 403, active → 200  
Effort: 2 hours  
Risk: LOW

---

## Run 70 Mandate: Widget Drift Retired

Per `governance.json.run_70_mandate`: `check_project_invariants.py` exits 1 at run 70.

Actions taken this run:
1. `docs/reminders/widget-drift-URGENT.md` written — human task documented
2. URGENT push notification sent
3. Widget drift retired from subconscious — no further ideas, no further debate

Fix remains: `cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js`

---

## Human Approval Required

**DO NOT implement without human approval.**

To approve: respond to push notification or next session with "approve run 70 winner" or equivalent.

Approving unlocks:
1. SMS Compliance Dashboard build (backend + frontend + tests)
2. Zapier #107 plan_status fix (bonus)
