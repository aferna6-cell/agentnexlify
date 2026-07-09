# Improvement Backlog — Run 77 (2026-07-02-pm)

Status as of run 77. Previous backlog entries from run 76 updated with corrections.

---

## ACTIVE

### B-003: Wire Railway Healthz Monitoring Alert (run 77 winner)
- **Status:** pending_autonomous (script write) + human_advisory (env var)
- **Evidence:** GH #388, /healthz timeout 10:27 UTC, SLACK_ALERT_WEBHOOK_URL not set
- **Effort:** S (script ~30 min, env var 2 min human)
- **Owner:** nightly-commit-review (script), human (env var)
- **Run 78 mandate:** if script not created → escalate to SKILL.md Step 9C

### B-002: SMS Compliance Dashboard (runs 73+74 winner)
- **Status:** pending_autonomous — GH #385 filed, issue-to-pr-loop active
- **Evidence:** Backend + migration 160 shipped; endpoint + page outstanding
- **Effort:** S
- **Owner:** issue-to-pr-loop autonomous
- **No further mandate:** autonomous pathway active

---

## IMPLEMENTED

### B-001: Zapier plan_status enforcement (runs 75+76 winner)
- **Status:** IMPLEMENTED — `backend/routers/zapier.py:121-128`
- **Evidence:** GH #107 closed 2026-06-13, `test_cancelled_subscription_blocked` at `backend/tests/test_zapier_auth.py:339`
- **Correction:** Runs 75+76 tracked wrong file path (`backend/services/zapier_auth.py` does not exist). Fix was always at `backend/routers/zapier.py`. Nightly 2026-07-02 corrected.

---

## PARKING LOT (no current trigger)

### P-001: Plan-Name Guard Check 7 (pre-commit)
- XS effort, AUTONOMOUS-EXECUTABLE, no urgency
- Already guarded by `check_project_invariants.py` Check 5 at runtime
- Re-evaluate if a retired plan name causes a production incident

### P-002: email_sequences.py god-class split
- 1143L, M-effort
- Moratorium active, no imminent edit planned
- Re-evaluate when moratorium exits or next edit touches the file

### P-003: AI-to-Human Handoff v1
- **FROZEN** — 7 consecutive debate kills. Added to `frozen_ideas` in governance.json run 77.
- Not subconscious cycle material at current effort/readiness level
- Unfreeze trigger: M-effort implementation, no moratorium active

### P-004: Healthz handler root cause
- Diagnose `/healthz` handler hang (partial fix to B-003)
- Bonus action for nightly: `grep -n healthz backend/main.py` → read handler → bug-patterns.md
- Low urgency while monitoring alert covers detection

---

## RETIRED

### Widget drift — topic permanently retired
- `widget_drift_topic_retired: true` in governance.json
- Fix: `cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js`
- PR #387 (open 1d) fixes this — human merge recommended by morning digest
