# Improvement Backlog

Running list of subconscious winners. Most recent first.

| Cycle | Date | Winner | Category | Status |
|-------|------|--------|----------|--------|
| 79 | 2026-07-05 | Fix brain connector credentials (GitHub 403 + SUPABASE_ACCESS_TOKEN) | operational | pending_human |
| 78 | 2026-07-03 | Add Step 9B to nightly SKILL.md — healthz monitor maintenance | operational | implemented |
| 77 | 2026-07-02-pm | Wire Railway healthz monitoring alert (ops/monitoring/healthz-alert.sh) | operational | escalated_to_p0_gh_issue |
| 76 | 2026-07-01-pm | Zapier plan_status enforcement — DE-SCOPED | code_health | implemented |
| 75 | 2026-07-01 | Zapier API key plan_status enforcement (GH #107) | code_health | implemented |
| 74 | 2026-06-30-pm | SMS Compliance Dashboard — full code delivery | customer_value | pending_autonomous |
| 73 | 2026-06-30 | SMS Compliance Dashboard — 1 endpoint + 1 page | customer_value | pending_autonomous |
| 72 | 2026-06-29-pm | Fix KB autopopulate — timing mandate | code_health | implemented |
| 71 | 2026-06-29 | Fix KB autopopulate discover step | code_health | implemented |
| 70 | 2026-06-28 | Widget drift mandate execution + docs/reminders/widget-drift-URGENT.md | workflow | mandate_executed |
| 1 | 2026-04-04-pm | AI-to-Human Handoff (Explicit Trigger, v1) | growth / ux | frozen |

---

## Frozen Ideas

- `ai_human_handoff` — 7 consecutive debate kills. Never propose again.

## Retired Topics

- **Widget drift** — permanently retired after 6-run delivery failure chain (runs 65-70). Human-only task.
  Fix command: `cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js`

---

## Near-Miss Parking Lot

| Idea | Parked | Reconsider |
|------|--------|------------|
| Brain connector health check Step 9C | Run 79 | After brain credentials fixed (run 80 mandate if still failing) |
| Plan-name guard pre-commit Check 7 | Run 76 | Low urgency, AUTONOMOUS-EXECUTABLE |
| email_sequences.py god-class split | Run 76 | M-effort, moratorium active |
| Diagnose /healthz handler root cause | Run 78 | After 2+ incidents (not 1) |
| Merge Dependabot PRs #381-383 | Run 78 | Low urgency, nightly bonus |
