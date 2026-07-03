# Improvement Backlog — Run 78 (2026-07-03)

Status as of run 78. Previous backlog entries from run 77 updated with corrections.

---

## ACTIVE

### B-003: Add Step 9B to Nightly SKILL.md + healthz-alert.sh (run 78 winner)
- **Status:** pending_autonomous — AUTONOMOUS-EXECUTABLE (SKILL.md edit + script write)
- **Evidence:** Run 78 mandate fires, ops/monitoring/healthz-alert.sh missing, healthz timeout 10:27 UTC 2026-07-02, SLACK_ALERT_WEBHOOK_URL not set
- **Effort:** XS (SKILL.md edit ~10 min)
- **Owner:** nightly-commit-review (SKILL.md edit + script write), human (SLACK_ALERT_WEBHOOK_URL)
- **Run 79 mandate:** if script still missing → P0 GH issue with `critical` + `blocker` labels, tag human

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
- **Note:** Runs 75+76 tracked wrong file path. Corrected 2026-07-02.

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
- Diagnose `/healthz` handler hang (bonus action from run 77, weakened in run 78 debate)
- Re-evaluate when healthz-alert.sh is live and has caught 2+ incidents
- One data point insufficient for confirmed pattern

### P-005: Dependabot PRs #381-383 merge
- Patch bumps, `npm audit fix` safe
- Killed in run 78 debate (no urgency, no mandate)
- Bonus action for next nightly: verify still open, merge if patch-only

---

## RETIRED

### Widget drift — topic permanently retired
- `widget_drift_topic_retired: true` in governance.json
- Fix: `cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js`
- PR #387 (open as of 2026-07-02) fixes this — human merge recommended

---

## Questions for Run 79

1. Did nightly's Step 9B successfully write `ops/monitoring/healthz-alert.sh`?
2. Has the human set `SLACK_ALERT_WEBHOOK_URL` in Railway?
3. Any new production incidents or commits in the 24h window?
4. Is GH #385 (SMS Dashboard) still open or has issue-to-pr-loop produced a PR?
