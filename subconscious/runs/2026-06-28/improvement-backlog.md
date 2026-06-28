# Improvement Backlog — Run 70 (2026-06-28)

## Active (pending human approval)

### SMS-COMPLIANCE-DASHBOARD
- **Status:** pending_approval (run 70 winner)
- **Effort:** ~1 day
- **Gate:** agent_os
- **Backend:** `backend/routers/sms_compliance.py` — `/api/sms-compliance/summary` + `/opted-out-leads`
- **Frontend:** `frontend/src/pages/SMSCompliance.jsx` + sidebar entry
- **Tests:** `backend/tests/test_sms_compliance.py`
- **Blocking:** nothing
- **Evidence:** council fix #1 (`9ddfd0e`) landed backend enforcement; Recharts installed; no migration needed; GoHighLevel competitive gap

### ZAPIER-PLAN-STATUS (Bonus A)
- **Status:** pending_approval (bundle with SMS Dashboard)
- **Effort:** ~2 hours
- **File:** `backend/services/zapier_auth.py` + `backend/tests/test_plan_gating_new_plans.py`
- **GH Issue:** #107 (open 60+ days)
- **Blocking:** nothing

---

## Ready (sequencing-blocked)

### PLAN-NAME-GUARD
- **Status:** ready, blocked by widget-drift resolution
- **Effort:** ~30 minutes
- **File:** `scripts/check_project_invariants.py` — extend Invariant #3 to include `free` + frontend scan
- **Blocking:** widget-drift must be fixed first (invariant script exits 1 until then)

### PRE-COMMIT-AUTOSYNC
- **Status:** ready, blocked by widget-drift resolution
- **Description:** add `cp widget/agentnexlify-widget.js frontend/public/widget/agentnexlify-widget.js` as pre-commit hook step when widget source changes
- **Effort:** ~1 hour
- **Blocking:** widget-drift resolution + PLAN-NAME-GUARD (sequencing)

---

## Parking Lot (human precondition required)

### AI-HUMAN-HANDOFF
- **Status:** parking lot — 73 days old, 8+ recommendations, 0 implementations
- **Precondition:** human audits `backend/services/os_outbound_mirror.py` (PR #188, state unknown)
- **Resurfaced:** run 72+ after precondition confirmed
- **Note:** Most-cited cross-industry gap. Critical priority. Bandwidth was absorbed by council sprint Jun 24–27.

---

## WIDGET-DRIFT (RETIRED from subconscious)

- **Status:** RETIRED — run 70 mandate fired
- **Human task:** `docs/reminders/widget-drift-URGENT.md`
- **Fix:** `cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js`
- **Subconscious will NOT regenerate ideas for this topic**

---

## Future Backlog

### LEAD-SOURCE-ANALYTICS
- Low effort (~1 day). Track which widget embeds produce the highest-quality leads.
- Waiting: SMS Dashboard shipped first (compliance before analytics)

### TRIAL-TO-MEMBER-TRACKING (Fitness Vertical)
- Migration required. Fitness-vertical only. Defer to vertical sprint.

### CUSTOM-AUTOMATION-TEMPLATES
- Agent OS feature. Medium effort. Post AI-to-Human Handoff.
