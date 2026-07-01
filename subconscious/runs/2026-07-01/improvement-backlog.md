# Improvement Backlog — Run 75 (2026-07-01)

## Active

| Priority | Item | Source | Effort | Path | Status |
|----------|------|--------|--------|------|--------|
| 1 | Zapier plan_status enforcement in `_get_api_key_client` | run 75 winner | S (30 min) | AUTONOMOUS-EXECUTABLE | pending_approval |
| 2 | SMS Compliance Dashboard (full) | runs 73+74, GH issue | S | issue-to-pr-loop | pending_autonomous |

## Parking Lot

| Item | Parked Since | Effort | Unblock Condition |
|------|-------------|--------|-------------------|
| AI-to-Human Handoff widget escalation | run 4 (76 days) | M | SMS ships + true_pending ≤ 2 + new activation-energy reduction |
| Plan-Name Guard Check 7 | run 73 | S | true_pending ≤ 2 (human-required) |
| Home.jsx god-class split (1006L) | run 74 | M | SMS ships + Zapier ships |
| email_sequences.py god-class split (1143L) | run 41 | M | Home.jsx done first |

## Retired / Resolved

| Item | Status | Note |
|------|--------|------|
| Widget drift (landing-page-v2) | RETIRED run 70 | Human-only. See docs/reminders/widget-drift-URGENT.md |
| KB autopopulate fix | IMPLEMENTED 65284cc | WebFetch + DISCOVER_PROMPT fixed |
| Run 76 mandate (GH issue for SMS) | SATISFIED by nightly 2026-07-01 | GH issue filed before run 75 |

## Questions for Next Run (Run 76)

1. Did nightly implement Zapier plan_status enforcement (AUTONOMOUS-EXECUTABLE)?
2. Did issue-to-pr-loop pick up the SMS Dashboard GH issue and open a PR?
3. Has `knowledge-base/log.md` received a new entry since 65284cc fix (kb-autopopulate cron)?
4. What is true_pending count after governance corrections?
