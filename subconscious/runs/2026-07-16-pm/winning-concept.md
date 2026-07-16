# Winning Concept — 2026-07-16-pm (Run 96)

## Recommendation

Implement `backend/services/appointment_completion.py` — the cron job that transitions past-`confirmed` appointments to `completed` and fires the `appointment_completed` event, unlocking review requests, rebook prompts, and aftercare automations for every booking.

## Why This, Why Now

Run 95 selected this as its winner on 2026-07-16 (commit `01705bc`). The nightly review on 2026-07-16 did not implement it — the file is confirmed absent from `backend/services/`. The full implementation sketch was published in `subconscious/runs/2026-07-16/winning-concept.md`. Two root-cause fixes that were blocking first real bookings both landed on 2026-07-16: `6cc3419` injected the booking URL into the AI prompt (MTOptions had 21 leads, 0 bookings because the AI never had a URL to share), and `f143de5` fixed the appointment reminder status filter (filtered on `'booked'` which never exists — all appointments are `'confirmed'`). Without `appointment_completion.py`, every appointment sits `confirmed` forever: no review requests fire, no rebook prompts send, no aftercare automations trigger. The booking chain is 90% unblocked — this is the last piece.

## Implementation Sketch

**New file:** `backend/services/appointment_completion.py`

```python
"""
Auto-complete past-confirmed appointments.
Called by scheduler every 15 min.
Appointments must end >30 min ago to guard against in-progress overruns.
"""
from datetime import datetime, timezone, timedelta
from backend.models.database import get_service_supabase
from backend.services.rule_engine import trigger_event
import logging

logger = logging.getLogger(__name__)

GRACE_PERIOD = timedelta(minutes=30)


async def auto_complete_past_appointments() -> int:
    """Mark past-confirmed appointments completed; fire appointment_completed event.
    Returns count of appointments completed."""
    cutoff = (datetime.now(timezone.utc) - GRACE_PERIOD).isoformat()
    db = get_service_supabase()

    rows = (
        db.table("appointments")
        .select("id, client_id, tenant_id, scheduled_at, end_time")
        .eq("status", "confirmed")
        .lt("end_time", cutoff)
        .is_("completed_at", "null")
        .execute()
        .data
    )

    completed = 0
    for appt in rows:
        try:
            db.table("appointments").update(
                {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}
            ).eq("id", appt["id"]).execute()
            await trigger_event("appointment_completed", appt["tenant_id"], appt)
            completed += 1
        except Exception as exc:
            logger.warning("appointment_completion: failed to complete %s: %s", appt["id"], exc)

    if completed:
        logger.info("appointment_completion: completed %d appointments", completed)
    return completed
```

**Pre-implementation verification:**
```sql
-- Verify completed_at column and 'completed' status exist:
SELECT column_name FROM information_schema.columns
WHERE table_name = 'appointments' AND column_name IN ('completed_at', 'status');
-- If missing: file migration before implementing
```

**Wire into scheduler** (`backend/services/appointment_reminders.py` or `backend/services/scheduling.py`):
```python
from backend.services.appointment_completion import auto_complete_past_appointments
# In the 15-minute scheduler loop:
await auto_complete_past_appointments()
```

**Regression tests:** `backend/tests/test_appointment_completion.py`
- Test 1: Past-confirmed appointment (end_time 1h ago) → status `completed`, `completed_at` set, `appointment_completed` event fires.
- Test 2: In-progress appointment (end_time 20min ago, within 30-min grace period) → NOT completed.
- Test 3: Already-completed appointment → NOT re-processed (idempotency check via `completed_at IS NULL`).

**Commit message:** `feat(booking): auto-complete past-confirmed appointments — unlocks review requests + aftercare automations`

**Schema note:** `appointments` table uses `tenant_id` (correct per schema-discipline.md — client_id restriction applies to leads+conversations only). Verify `completed_at` column existence before writing — see pre-implementation SQL above.

## What This Replaces

Previous active direction: run 95 winning-concept.md (same recommendation, unimplemented). This is a direct carry-forward.

## Mandate Check (Run 96 — from Run 95 Mandate)

| Mandate Item | Status |
|---|---|
| appointment_completion.py committed by nightly? | ❌ ABSENT — backend/services/ confirmed (appointment_booker, appointment_customer_notify, appointment_reminders only) |
| Regression tests pass? | ❌ test_appointment_completion.py ABSENT |
| First real booking in AdminFunnelPage? | UNKNOWN — check AdminFunnelPage manually (booking URL fix landed 2026-07-16) |
| GH #413 REFERRAL_REWARD_ENABLED=1 set? | ❌ NOT SET — Day 25+, 0 human responses |
| GH #399 resolved? | ❌ OPEN Day 14+ — 30 ai-ready issues blocked |
| Parking lot: Step 9F or BotHealthPage.jsx | → Step 9F: Parking Lot (propose run 97). BotHealthPage: Bonus Action (file GH issue). |

## Bonus Actions (Autonomous)

**Bonus A:** Post Day-14+ escalation comment on GH #399 with opportunity-cost framing:
> "Day 14+: 30 ai-ready issues blocked. Estimated 60 engineering-hours queued behind one Railway env-var rotation (AUTOPILOT_GH_TOKEN). Top blocked: Lead Source Analytics, SMS Compliance Dashboard. The new admin_loop_health endpoint (22710b3) now monitors loop vitals — it will show stalled-autopilot signal going forward. Single action: Railway → Variables → rotate AUTOPILOT_GH_TOKEN."

**Bonus B:** File GH issue for BotHealthPage.jsx with ai-ready label:
- Title: "feat(admin): BotHealthPage.jsx — frontend dashboard for admin_loop_health endpoint"
- Labels: frontend, admin, medium-risk
- Body: "admin_loop_health.py (22710b3) ships /api/admin/loop-health with 5 vitals (pending drafts, opportunity suggestions queue, Agent OS usage, inbound bridge status, error accumulation). No frontend page exists. Build AdminLoopHealth.jsx or BotHealthPage.jsx consuming this endpoint. Pattern: AdminFunnelPage (PR #417). Protected by admin secret — add to Admin sidebar."
- Note: Do NOT add ai-ready until GH #399 resolved (issue-to-pr-loop stalled)

## Confidence: HIGH

Evidence direct: file confirmed absent. Run 95 winner confirmed (commit 01705bc, memory.jsonl line 93). Booking chain newly unblocked — first bookings imminent. Debate rounds 1-3 all defended. No new dependencies, no migration risk (verify completed_at exists first).

## Run 97 Mandate

1. appointment_completion.py committed by nightly? Check nightly-2026-07-17 log.
2. Regression tests pass? (3 test cases confirmed)
3. First real booking visible in AdminFunnelPage or Supabase? (booking URL fix + auto-complete now both in place)
4. GH #399 resolved? (Day 15+)
5. GH #413 REFERRAL_REWARD_ENABLED=1 set? (Day 26+)
6. Parking lot: Step 9F KB staleness check in nightly SKILL.md, BotHealthPage.jsx GH issue.
