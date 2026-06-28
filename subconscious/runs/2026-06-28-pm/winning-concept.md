# Winning Concept — Run 70 (2026-06-28-pm)

**Winner:** SMS Compliance Dashboard  
**Score:** 12/12 (debate-log.md)  
**Effort:** S (~3-4 hours)  
**Confidence:** HIGH  
**Requires human approval:** YES — subconscious recommends, does not implement.

---

## Run 70 Mandate — EXECUTED

`check_project_invariants.py` exits 1 (widget drift, 6th consecutive run — runs 65-70).

Actions taken per `governance.json:run_70_mandate`:
1. ✅ `docs/reminders/widget-drift-URGENT.md` written with exact fix command
2. ✅ URGENT push notification sent
3. ✅ Widget drift topic retired from subconscious permanently in `governance.json`

The fix is a single command:
```bash
cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js
python3 scripts/check_project_invariants.py
git add landing-page-v2/widget/agentnexlify-widget.js
git commit -m "fix: sync widget to landing-page-v2 (pre-commit unblocked)"
```

The subconscious loop cannot execute this (landing-page-v2/ is on FORBIDDEN paths in nightly-commit-review SKILL.md). The reminder file + push notification are the final escalation. After this, it is a human-maintained checklist item.

---

## The Recommendation: SMS Compliance Dashboard

### Background

Council fix #1 shipped 2026-06-24:
- `backend/services/sms_compliance.py` — TCPA opt-in/opt-out tracking
- Migration 160 — `sms_compliance_log` table
- All SMS sends now gated behind compliance check

The backend is complete. No visibility page exists.

Business owners sending SMS campaigns have no way to:
- See opt-in rates across their list
- View recent opt-outs and reasons
- Audit TCPA compliance before a campaign
- Export opted-out contacts (required for suppression lists)

This is a legal liability: TCPA violations carry $500-$1,500 per message. The data exists to prevent them; it is just invisible.

---

## Implementation Sketch

### Step 1: Backend endpoint

**File:** `backend/routers/sms.py` (create if not exists, or add to `backend/routers/channels_sms.py`)

```python
@router.get("/sms/compliance-summary")
async def get_sms_compliance_summary(client_id: str = Depends(get_client_id)):
    """TCPA compliance summary for business owner dashboard."""
    # Query sms_compliance_log WHERE client_id = :client_id
    # Return: opt_in_count, opt_out_count, send_count_30d, 
    #         compliance_rate, recent_opt_outs (last 10)
    pass
```

Note: use `client_id` not `tenant_id` (CLAUDE.md Critical Invariant #1).

### Step 2: Register endpoint in main.py

Add router include near line 800 in `backend/main.py`:
```python
from backend.routers.sms import router as sms_router
app.include_router(sms_router, prefix="/api")
```

### Step 3: Frontend page

**File:** `frontend/src/pages/SMSCompliancePage.jsx`

Components:
- Compliance health card (green: rate > 95%, yellow: 90-95%, red: < 90%)
- Opt-in / opt-out count cards
- 30-day trend chart (Recharts LineChart)
- Recent opt-out event table (contact name/email, reason, timestamp)
- CSV export button

### Step 4: Route + nav

**`frontend/src/App.jsx`:**
```jsx
<Route path="/sms-compliance" element={<SMSCompliancePage />} />
```

**`frontend/src/components/Sidebar.jsx`:**
Add "SMS Compliance" under "Channels" section.

### Step 5: Test

**File:** `backend/tests/test_sms_compliance_summary.py`
- Mock `sms_compliance_log` with 3 rows (1 opt-in, 2 opt-outs)
- Assert endpoint returns correct summary
- Assert compliance_rate calculation

---

## What This Does NOT Touch

- No schema changes
- No widget changes
- No existing endpoint modifications
- Widget copy rule: not relevant (no widget JS changes)
- No `from __future__ import annotations` risk (Python file only adds endpoint)

---

## Moratorium Interaction

Adds 1 pending_approval. True pending estimate ~6, max = 2. Moratorium remains active. This does not require moratorium override — it is a new item queued for human approval and execution at their discretion.

---

## Bonus Actions (post-winner, if time allows)

**Bonus A:** Fix KB autopopulate
- Read `knowledge-base/log.md` → find root cause → fix broken script
- 53 days stale, quality degradation

**Bonus B:** Create GH issue for AI-to-Human Handoff v1
- Document implementation sketch as GH issue for sprint planning
- 74 days pending, Critical gap

**Bonus C:** Email sequences split
- Invoke `/god-class-splitter` on `backend/routers/email_sequences.py` (1143L → 3 files)
- Prerequisites all met: god-class-splitter SKILL.md, post-split-test-repair SKILL.md

---

## Next Run Forecast

Run 71 will evaluate:
1. SMS Dashboard status (implemented or still pending?)
2. Widget drift fixed (pre-commit unblocked?) — topic retired, but status tracked
3. KB autopopulate fix as primary candidate if SMS Dashboard is done
4. AI-to-Human Handoff v1 if moratorium trajectory improves

---

*Subconscious run 70. Recommendation only. Human approval required before any implementation.*
