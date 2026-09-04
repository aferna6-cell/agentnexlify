# Improvement Backlog — Run 115 (2026-09-04)

## Winner (this run)
- **Step 9J merge loop** — implement per-PR mergeable_state check + squash-merge (cap 10/run)

## Deferred (not ready)
- **os_tool_executions.py god-class split** — 783L, last commit 2026-09-02 (2 days old). Mandate: 4d+ stability. Revisit run 116 (Sep 5+).
- **M9 planner bakeoff CI gate** — system still being hardened (5 commits in 3 days). Revisit when velocity <2 commits/week for 2 weeks.

## Parking Lot (valid, not urgent)
- **Step 9E 60-day early warning** — AUTOPILOT_GH_TOKEN at 62 days (14 from 76d threshold). Add secondary 60-day threshold to Step 9E. Low urgency this run; mandate for run 116.
- **GH #787 website_connect.py block_demo_role** — already tracked, labeled `ai-ready`, issue-to-pr-loop is the correct execution path. Monitor.

## Frozen Ideas (do not propose)
- ai_human_handoff — rejected 3+ times

## Operational Alerts (not improvement ideas — action needed by human)
- SUPABASE_ACCESS_TOKEN: 43 days stale in Railway → brain connector down (GH #684)
- AUTOPILOT_GH_TOKEN: 62 days old, 14 days from expiry threshold → rotate soon
- KB staleness: 9 days (Step 9F alerted)
