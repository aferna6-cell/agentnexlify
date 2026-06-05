# Improvement Backlog — 2026-06-05-pm (Run 51)

## Active

- **Verify and merge PR #183** — close GH #181 (backend/routers/billing.py AMOUNT_TO_PLAN missing 15000→autopilot + 25000→professional). ~10 min review + merge. CI gate prevents bad merge. Morning digest confirmed "merge — confirmed path." Implementation sketch: subconscious/runs/2026-06-05-pm/winning-concept.md.

## Parking Lot

- **AI-to-Human Handoff v1 GH issue** (50 days, oldest pending, run 4) — os_outbound_mirror.py merged, infrastructure ready. Promote post-moratorium exit when pending ≤ 2. Implementation sketch: subconscious/runs/2026-05-28-pm/winning-concept.md.
- **Zapier plan_status security fix** (GH #107, 36+ days, ROI 2.5) — ai-ready label, 2 min to create issue. Route via issue-to-pr-loop, not subconscious winner queue. Fix: add `plan_status IN ('active','trialing')` filter to `_get_api_key_client` in backend/services/zapier_auth.py.
- **email_sequences.py god-class split** (run 41 active_direction, 1255L) — unblocked after PR #183 merge. Invoke /god-class-splitter on backend/routers/email_sequences.py → email_crud.py + email_enrollment.py + email_processor.py. ~2h execution.

## Rejected This Run

- **Merge PR #200 as winner** — WEAKENED → Bonus A. 5-min standing action, not improvement idea. Still required before 2:37 AM tonight for Item B to fire.
- **AI-to-Human Handoff as winner** — WEAKENED → parking lot. 4/4 prior recommendations without implementation. Mechanism bottleneck unclear. Adding GH issue adds to pending, works against moratorium exit.

## Questions for Next Run

1. Was PR #183 verified and merged? Did Check 11 WARNING become PASS?
2. Was PR #200 merged before 2:37 AM tonight? Did Items A+B both fire in nightly cycle?
3. Did check-widget-sync.sh get created (Item B)? Does pre-push hook now guard widget sync?
4. Is email_sequences.py split now unblocked and scheduled for next session?
5. What is moratorium pending count after Items A+B close tonight + PR #183 merge?
