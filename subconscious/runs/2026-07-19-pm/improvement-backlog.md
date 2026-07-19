# Improvement Backlog — Run 99 (2026-07-19-pm)

## Active (pending implementation)

| Priority | Item | Channel | Blocked by |
|---|---|---|---|
| P0 | Step 9F: KB Autopopulate Staleness Check in SKILL.md | Interactive session (human approval) | Nothing — mechanism change confirmed |
| P1 | GH #399: Rotate AUTOPILOT_GH_TOKEN | Human action (Railway secret) | Nothing (human action) |
| P1 | GH #413: Set REFERRAL_REWARD_ENABLED=1 | Human action (Railway secret) | Nothing (human action) |

## Parking Lot

| Item | Why Parked | Re-evaluate when |
|---|---|---|
| conversation_enrichment_job.py scheduling | Needs Supabase MCP for queue depth check; GH #399 blocks issue-to-pr | GH #399 resolves |
| kb_hybrid_retrieval enable (Keys Koffee) | Needs settings UI toggle OR GH #399 | GH #399 resolves or settings UI built |
| Step 9G (GH #399 queue depth alert in nightly) | Proactive trigger — same structural problem as Step 9F; Step 9F must ship first | Step 9F implemented |
| platform_flags.py safety registry | No current production risk (all rows = "1"); premature for 2 keys | 3+ platform_settings keys with diverse types |
| kb_hybrid settings toggle (frontend) | Needs new settings page section | Post GH #399 |

## Shipped / Cleared (Run 99)

| Item | PR | Commit | Notes |
|---|---|---|---|
| appointment_completion.py | #475 | 23b1da5 | as appointment_jobs.py in backend/services/automation/scheduled/ |
| BotHealthPage.jsx | #475 | 23b1da5 | Loop health dashboard, no localStorage, admin-secret gated |
| AttributionPage.jsx | #475 | 23b1da5 | Attribution breakdown, client_id correct, 5k-lead ceiling noted |
| platform_flags.py + admin_voice_test.py | #476 | 6b0b0bc | migration 175, fail-open, tested |
| 970 stale file deletion | #477 | 6aa9ba4 | verified zero inbound refs, clean |

## Frozen Ideas (governance)

| Idea | Reason frozen |
|---|---|
| AI-to-human handoff | Rejected 3+ times; conflicts with widget-first model |

## Notes

KB staleness check (Step 9F) is the only remaining P0 in the SKILL.md-edit backlog. Steps 9B/9C/9D/9E shipped in 1 nightly cycle each. Step 9F requires the interactive channel — document this explicitly so future runs don't repeat the delivery mechanism error.

GH #399 and GH #413 are purely human-action items. The subconscious has surfaced them for 17+ and 28+ days respectively. No further ideation value — they appear in PushNotification only until resolved.
