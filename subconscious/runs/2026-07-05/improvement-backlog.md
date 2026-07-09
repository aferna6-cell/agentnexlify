# Improvement Backlog — Snapshot Run 79 (2026-07-05)

| Cycle | Date | Winner | Category | Status |
|-------|------|--------|----------|--------|
| 79 | 2026-07-05 | Fix brain connector credentials (GitHub 403 + SUPABASE_ACCESS_TOKEN) | operational | pending_human |
| 78 | 2026-07-03 | Add Step 9B to nightly SKILL.md — healthz monitor maintenance | operational | **implemented** (this run) |
| 77 | 2026-07-02-pm | Wire Railway healthz monitoring alert (ops/monitoring/healthz-alert.sh) | operational | escalated_to_p0_gh_issue |
| 76 | 2026-07-01-pm | Zapier plan_status enforcement — DE-SCOPED | code_health | **implemented** (backend/routers/zapier.py:121-128) |
| 75 | 2026-07-01 | Zapier API key plan_status enforcement | code_health | **implemented** (GH #107 closed 2026-06-13) |
| 74 | 2026-06-30-pm | SMS Compliance Dashboard — full code delivery | customer_value | pending_autonomous |
| 73 | 2026-06-30 | SMS Compliance Dashboard — 1 endpoint + 1 page | customer_value | pending_autonomous |
| 72 | 2026-06-29-pm | KB autopopulate fix — timing mandate | code_health | **implemented** (65284cc) |
| 71 | 2026-06-29 | Fix KB autopopulate discover step | code_health | **implemented** (65284cc) |

---

## Frozen Ideas

- `ai_human_handoff` — 7 consecutive debate kills. Never propose again.

## Retired Topics

- **Widget drift** — permanently retired after 6-run delivery failure chain (runs 65-70). Human-only task.

---

## Pending Human Actions

| Action | Added | Source |
|--------|-------|--------|
| Rotate GitHub token for brain-refresh[bot] | 2026-07-05 | Run 79 winner |
| Set SUPABASE_ACCESS_TOKEN in cron environment | 2026-07-05 | Run 79 winner |
| Set SLACK_ALERT_WEBHOOK_URL in Railway Variables | 2026-07-02 | Run 77 winner (GH issue filed run 79) |
| Paste SMS Compliance Dashboard code | 2026-06-30-pm | Run 74 winner |

---

## Near-Miss Parking Lot

| Idea | Parked | Reconsider |
|------|--------|------------|
| Brain connector health check Step 9C | Run 79 | After brain credentials fixed (run 80) |
| Plan-name guard pre-commit Check 7 | Run 76 | Low urgency, AUTONOMOUS-EXECUTABLE |
| email_sequences.py god-class split | Run 76 | M-effort, moratorium active |
