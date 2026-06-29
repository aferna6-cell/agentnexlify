# Improvement Backlog — Run 72 (2026-06-29-pm)

## Winner (This Run)
| # | Title | Status | Effort |
|---|-------|--------|--------|
| 72 | KB autopopulate fix — mandate nightly 2026-06-30, human fallback if Step 9B misses | pending_approval (conditional autonomous) | XS |

## Active Pending (Human-Required)
| Run | Title | Age | Effort | Blocking |
|-----|-------|-----|--------|---------|
| 70 | SMS Compliance Dashboard (SMSCompliancePage.jsx + endpoint) | 1 day | M | human frontend |
| 38 | AI-to-Human Handoff v1 (widget escalation flow) | 75+ days | M | widget change → human |
| 41 | email_sequences.py god-class split | 30+ days | M | multi-file refactor → human |
| 71 | KB autopopulate fix (run 71, Step 9B autonomous attempt) | 0 days | XS | nightly 2026-06-30 |

## Parking Lot (Deferred)
| Title | Reason |
|-------|--------|
| SMS Compliance Dashboard | No urgency change since run 70 (1 day old). Re-evaluate run 73+. |
| Widget drift (landing-page-v2) | Retired at run 70 after 6 delivery failures. Human-only. See docs/reminders/widget-drift-URGENT.md. |
| morning-auto.sh cloud-detection | Bonus action on KB fix edit. Don't escalate separately until run 71 fix is verified working. |

## Frozen / Rejected
See governance.json frozen_ideas and rejected_paths for full list.

## Implementation Lag Warning
True pending approval items: ~6 (estimated). Moratorium active (max 2 autonomous items). Human attention needed on:
1. Widget drift (docs/reminders/widget-drift-URGENT.md — 1 command)
2. AI-to-Human Handoff v1 (75+ days, Critical customer gap)
3. SMS Compliance Dashboard (1 day, compliance liability)
4. email_sequences.py split (30+ days, Code Health)
