# Improvement Backlog — Run 99 (2026-07-18-pm)

## Active (pending or in-flight)

| Item | Status | Blocker | Run |
|------|--------|---------|-----|
| Step 9F: KB staleness check in SKILL.md | **IMPLEMENTED THIS RUN** | was: CLEAN-night mechanism | 97-99 |
| GH #399: AUTOPILOT_GH_TOKEN rotation | pending_human_action | human must rotate in Railway | 83+ |
| Lead Source Analytics Dashboard GH issue | pending_autonomous | GH #399 blocks issue-to-pr-loop | 85 |
| Keys Koffee business hours (GH #415) | pending_human_action | tenant must respond | 91 |
| conversation_enrichment_job.py schedule | parking_lot | GH #399 blocks; pending count unknown | 98 |

## Implemented This Run / Today

| Item | Source | Commit |
|------|--------|--------|
| appointment_jobs.py (auto-complete past appts) | GH #454 → PR #475 | 23b1da5 |
| BotHealthPage.jsx (/admin/loop-health) | GH #465 → PR #475 | 23b1da5 |
| AttributionPage (GET analytics/attribution) | GH #453 → PR #475 | 23b1da5 |
| platform_flags.py + platform_settings migration 175 | PR #476 | 6b0b0bc |
| referral_reward_enabled=1 (via platform_settings) | GH #413 → PR #476 | 6b0b0bc |
| widget_kb_hybrid_enabled=1 + widget_kb_rerank_enabled=1 | PR #476 | 6b0b0bc |
| Repo cleanup (970 stale files) | PR #477 | 6aa9ba4 |

## Parking Lot (post-GH-#399)

| Item | Effort | Notes |
|------|--------|-------|
| Platform Settings Admin UI | M | No toggle UI for platform_settings rows. File ai-ready GH issue after GH #399 resolved. |
| Step 9G: KB hybrid smoke test | S | Validate FTS results actually firing in prod. Run 100+ candidate once Step 9F confirmed. |
| conversation_enrichment_job.py nightly schedule | S | Need Supabase MCP to check pending count first. |
| BotHealthPage.jsx GH issue follow-up | XS | IMPLEMENTED — closed. |

## Retired / Closed

| Item | Reason | Run |
|------|--------|-----|
| widget_guard LRU fix | IMPLEMENTED nightly d73072a | 94 |
| Step 9E credential rotation | IMPLEMENTED 4d30930 | 84 |
| Step 9D issue-to-pr-loop health check | IMPLEMENTED nightly | 83 |
| Step 9C brain connector health check | IMPLEMENTED nightly | 80 |
| Step 9B KB autopopulate health check | IMPLEMENTED nightly | 82 |
| notify_common.py failure-mode tests | CLOSED: safe_send_email swallows by design | 98 |
| ai_human_handoff | FROZEN: mechanism mismatch | 4 |
| widget_drift_topic | RETIRED: human-only task | 70 |
