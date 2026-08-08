# Improvement Backlog — Run 102
**Date:** 2026-08-08-pm

Items carried from prior runs + new candidates from this run. Ranked by urgency × effort ratio.

---

## PROPOSED (this run)

| ID | Title | Category | Effort | Status |
|----|-------|----------|--------|--------|
| R102-1 | Orchestrator grandfathered plan gap (growth/autopilot) | code_health | XS | proposed |

---

## QUEUED (strong candidates for next runs)

| ID | Title | Category | Effort | Run discovered | Notes |
|----|-------|----------|--------|----------------|-------|
| R102-2 | Nightly detached-HEAD branch guard | operational | XS | 102 | Two consecutive orphaned-commit incidents. Bash-only, autonomous_executable. |
| R102-3 | KB autopopulate continue-on-error silent-failure fix | operational | S | 102 | Refine: keep continue-on-error on article steps, remove from secret-check step. Needs CI config edit. |
| R101-5H | Step 9H: subconscious PR pile alerter (>3 open → alert) | workflow_efficiency | S | 101 | PR count still >3. Defer until pile clears or threshold debate resolves. |
| R101-4 | Per-tenant conversation zero-alert heartbeat | customer_value | M | 102 | New script needed (not autonomous_executable). Prevents Keys Koffee class of churn. High value. |

---

## PARKING LOT (valid but not urgent)

| Title | Reason deferred |
|-------|----------------|
| Nexlify Score token-burn guard | response_score.py has no AI calls — deterministic. Concern invalidated. |
| Step 9G redesign | Step 9G correctly triggers autopopulate. Root issue is the workflow silent-failure (R102-3 above). |
| orchestrator.py god class refactor | >600 lines. Scope too large for subconscious channel. Needs compound-engineering. |

---

## REJECTED / FROZEN

| Title | Reason |
|-------|--------|
| AI-to-human handoff | governance.json frozen_ideas. Rejected 3+ times. Do not propose. |
| Widget drift alerting | governance.json: widget_drift_topic_retired = true |
