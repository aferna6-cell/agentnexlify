# Improvement Backlog — Run 121 (2026-09-12)

## Active

- **Step 9G MCP fix**: Replace `gh workflow run` with `mcp__github__actions_run_trigger` in nightly-commit-review SKILL.md Step 9G block. KB 17d stale; gh CLI unavailable in cloud CCR sessions. XS effort, HIGH confidence.

## Parking Lot (survived debate but not chosen)

- **Step 9E unknown-date credentials**: Extend Step 9E to file a GH issue immediately when `last_rotated = "unknown"` regardless of days threshold. SUPABASE_ACCESS_TOKEN rotation date still unknown. (Run 122 if human still hasn't set it)
- **Step 9M — os_tool_executions.py god-class monitor**: Add `wc -l` check + alert at 500L in nightly SKILL.md. File at 436L after 2 rapid fixes; monitor when hitting 480L+.
- **Step 9N — credential countdown log**: Always log all credentials' days_since/days_remaining in Step 9E output (not just when threshold fires). Zero overhead; improves observability.

## Rejected This Run

- None explicitly killed — Idea 3 and 4 weakened to parking lot, not killed.

## Questions for Next Run (Run 122)

1. Did Step 9G trigger kb-autopopulate.yml successfully after implementation? Is knowledge-base/log.md updated?
2. Did Step 9E fire for AUTOPILOT_GH_TOKEN (now at ~76d threshold range)? GH #399 comment added?
3. SUPABASE_ACCESS_TOKEN: still unknown date? If yes → park to active (file GH issue).
4. os_tool_executions.py line count trending up? If ≥480L → promote Step 9M.
5. Any new nightly-commit-review SKILL.md issues introduced by Step 9G rewrite?
