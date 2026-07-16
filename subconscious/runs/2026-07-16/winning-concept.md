# Winning Concept — 2026-07-16 (Run 95)

## Recommendation

Implement the appointment auto-complete cron job to transition past-`confirmed` appointments to `completed`, unlocking review requests, rebook prompts, and aftercare automations for every booking.

## Why This, Why Now

Two root-cause fixes landed in the last 24 hours that together make first real bookings possible for the first time: `6cc3419` injected the booking URL into the AI widget prompt (MTOptions had 21 leads and 0 bookings because the AI never had a URL to share), and `f143de5` fixed the appointment reminder status filter (filtered on `'booked'` which never exists — all appointments are `'confirmed'`). The booking-to-automation chain is now almost complete. The only missing link is the `confirmed → completed` status transition: without it, every appointment sits `confirmed` forever and post-booking automations — review requests, rebook prompts, aftercare — produce zero output. GH #454 was filed today by the nightly review with a full implementation proposal. Implementing now means the first bookings that come in over the coming days will immediately generate review requests and retention automations.

## Implementation Sketch

**New file:** `backend/services/appointment_completion.py`

```python
"""
Auto-complete past-confirmed appointments.
Called by scheduler every 15 min.
Appointments must end >30 min ago to guard against in-progress overruns.
"""
from datetime import datetime, timezone, timedelta
from backend.database import get_supabase_client
from backend.services.rule_engine import trigger_event
import logging

logger = logging.getLogger(__name__)

GRACE_PERIOD = timedelta(minutes=30)


async def auto_complete_past_appointments() -> int:
    """Mark past-confirmed appointments completed; fire appointment_completed event.
    Returns count of appointments completed."""
    cutoff = (datetime.now(timezone.utc) - GRACE_PERIOD).isoformat()
    db = get_supabase_client()

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

**Wire into scheduler:**
In `backend/services/appointment_reminders.py` (or `backend/services/scheduling.py`), add to the 15-minute scheduler loop:
```python
from backend.services.appointment_completion import auto_complete_past_appointments
# ...
await auto_complete_past_appointments()
```

**Add regression test:** `backend/tests/test_appointment_completion.py`
- Test: past-confirmed appointment (end_time 1h ago) → gets completed, `appointment_completed` event fires.
- Test: in-progress appointment (end_time 20min ago, within grace period) → NOT completed.
- Test: already-completed appointment → NOT re-processed.

**Commit message:** `feat(booking): auto-complete past-confirmed appointments — unlocks review requests + aftercare automations`

**No migration required.** `completed_at` column and `completed` status already exist in the schema (check `migrations/` or `appointments` table definition before assuming — verify with `mcp__supabase__execute_sql` SELECT on `appointments` if needed).

## What This Replaces

Previous active direction: "Fix _SESSION_TURN_COUNTS unbounded dict in widget_guard.py:141" (run 94 winner) — **IMPLEMENTED** by `d73072a` (2026-07-16, confirmed in nightly log).

## Mandate Check (Run 95)

| Item | Status |
|------|--------|
| widget_guard LRU fix committed by nightly? | ✅ IMPLEMENTED — `d73072a` confirmed in nightly-2026-07-16 (line 51) |
| Regression test passes? | ✅ PR #435 (`d73072a`) ships test suite — 290 tests green |
| GH #413 REFERRAL_REWARD_ENABLED=1 set? | ❌ NOT SET — 0 human responses, Day 24 |
| Keys Koffee GH #415 actioned? First booking? | ❌ 0 human responses. Day 24. BUT: `6cc3419` just fixed the root cause (booking URL never in AI prompt). |
| GH #399 resolved? | ❌ OPEN Day 13 — 30 ai-ready issues blocked. Nightly deferred but did not escalate. |
| GH #403 resolved? | ❌ OPEN — KB 72+ days stale. |

**Critical new finding:** The 0-bookings problem for 21+ days had a code-level root cause: `booking_prompt.py` was missing (AI prompt never included the booking URL). Fixed by `6cc3419`. This means first real bookings are now possible today.

## Bonus Actions (Autonomous)

1. **Post Day-13 escalation comment on GH #399** — opportunity-cost framing: "Day 13: rotating AUTOPILOT_GH_TOKEN unlocks 30 ai-ready issues including Lead Source Analytics and SMS Compliance Dashboard. Single Railway secret update." Autonomous via `mcp__github__add_issue_comment`.

2. **Post Day-24 update on GH #413** — note that booking URL fix (#439) landed; if first bookings happen, referral program should be live to capture them as potential referrers. Short comment connecting the two revenue streams.

## Confidence: HIGH

Evidence direct: GH #454 filed today, implementation path clear, timing optimal (booking chain newly unblocked). Three debate rounds all defended. No new dependencies, no migration risk.

## Run 96 Mandate

1. Was `appointment_completion.py` committed by nightly? Check nightly-2026-07-17 log.
2. Regression tests pass? (3 test cases: past-confirmed → completed, grace-period → skip, already-completed → skip)
3. First real booking in AdminFunnelPage? (booking URL fix landed 2026-07-16)
4. GH #413 REFERRAL_REWARD_ENABLED=1 set? (Day 25+)
5. GH #399 resolved? (Day 14+ — autopilot loop stalled 30 issues)
6. Parking lot: Step 9F KB staleness check, BotHealthPage.jsx.
