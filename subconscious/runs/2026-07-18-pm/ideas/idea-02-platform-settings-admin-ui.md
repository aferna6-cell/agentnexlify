# Idea 02 — Platform Settings Admin UI

**Category:** Customer Value / Operational
**Effort:** M (new backend endpoint + new dashboard page)
**Confidence:** MEDIUM
**ROI:** 1.9

## The Idea

PR #476 shipped `platform_flags.py` + migration 175 (`platform_settings` table) with 3 prod rows seeded.
No admin UI exists. Operators must use raw Supabase SQL to toggle flags.

Build: `GET/POST /api/v1/admin/platform-settings` + `PlatformSettingsPage.jsx` in dashboard.

## Evidence

- PR #476 (2026-07-18): `platform_settings` table live. 3 rows: `referral_reward_enabled=1`,
  `widget_kb_hybrid_enabled=1`, `widget_kb_rerank_enabled=1`.
- `flag_enabled(key, env_default)` in `backend/services/platform_flags.py`: reads DB row first,
  60s cache, fail-open.
- No admin interface to toggle. Only path: Supabase dashboard SQL editor.
- Risk: if `widget_kb_rerank_enabled` needs disabling (e.g., Haiku latency spike causing widget
  timeouts), operator has no UI path. Must write SQL.

## Why It's WEAKENED

- GH #399 blocks issue-to-pr-loop. Filing a GH issue adds to blocked queue (30+ ai-ready issues).
- Flags currently set correctly — no immediate operational risk.
- M-effort: requires new endpoint + new page. Too large for one subconscious cycle recommendation.
- Better framing: file as ai-ready GH issue for post-GH-#399 resolution.

## Verdict

WEAKENED → parking lot. File GH issue after GH #399 resolves (or manually implement if urgent).
