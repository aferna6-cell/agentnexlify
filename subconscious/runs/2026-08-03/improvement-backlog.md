# Improvement Backlog — Run 102 Update (2026-08-03)

## Active — In Progress

| # | Idea | Status | Since |
|---|------|--------|-------|
| 1 | **Step 9G: KB self-healing trigger** | PENDING (PR #626 open, 3rd cycle) | Run 100 (2026-07-23) |

## Parking Lot — Deferred

| # | Idea | Blocker | Promote when |
|---|------|---------|-------------|
| 2 | Connector token expiry alerting (Step 9H candidate) | Migration 176 blocked by GH #536 | #536 resolved + migration 176 applied |
| 3 | Inbox triage AI cost guard | No prod data yet | After 2026-08-16 with real tenant inbox_triage.py data |
| 4 | Social publisher post-delivery receipt | Service baking since b67710c (2026-08-02) | After 2026-08-09 minimum |
| 5 | PWA install prompt in dashboard | M effort | Route through compound-engineering when capacity exists |

## Killed This Run

| # | Idea | Reason |
|---|------|--------|
| — | Dependabot batch-merge | Redundant with morning digest — no subconscious novelty |

## Done (implemented)

| # | Idea | Done | Run |
|---|------|------|-----|
| Step 9A | Stale nightly log cleanup | ✓ | 2026-07-15 |
| Step 9B | Widget invariant check | ✓ | 2026-07-16 |
| Step 9C | Pre-push hook coverage | ✓ | 2026-07-16-pm |
| Step 9D | Secrets scan in nightly | ✓ | 2026-07-17 |
| Step 9E | Credential rotation reminder | ✓ | 2026-07-17-pm |
| Step 9F | KB staleness alert | ✓ | Run 99 (2026-07-20) |

## Escalation Flag

Step 9G has now been the subconscious winner for 3 consecutive runs (100→101→102). Staleness: 11 days and growing. PR #626 open. Human merge or nightly self-apply recommended before run 103.
