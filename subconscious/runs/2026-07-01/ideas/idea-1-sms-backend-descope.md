# Idea 1: De-scoped SMS Compliance Backend (Run 74 Mandate)

**Evidence:** `backend/routers/sms_compliance.py` MISSING 11+ days. `frontend/src/pages/SmsCompliance.jsx` MISSING. Run 74 mandate fires: "if SMS not shipped: de-scope to backend endpoint only." Nightly 2026-07-01 independently filed a GH issue for full scope SMS Dashboard. Issue-to-pr-loop path now exists.

**Action:** Update recommendation to backend-only: `backend/routers/sms_compliance.py` + 2-line `main.py` edit. Drop JSX page. Paste-ready code already in `subconscious/runs/2026-06-30-pm/winning-concept.md §1+§2`. ~15 min human execution (down from 30 min).

**Impact:** Clears 2 stale active_direction entries (runs 73+74). Ships the API layer — unblocks mobile clients, future integrations, and the issue-to-pr-loop GH issue can handle the JSX page autonomously. Reduces activation energy by 50%.

**Category:** customer_value

**Mandate:** Run 74 mandate fires this run. Binding governance condition.

**Note:** Nightly filed GH issue with full scope → issue-to-pr-loop may implement JSX page autonomously. If so, de-scope is moot and the two paths converge.
