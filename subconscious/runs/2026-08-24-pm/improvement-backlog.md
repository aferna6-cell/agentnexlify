# Improvement Backlog — 2026-08-24-pm (Run 110)

## Active (this run)
- **Step 9J major-version gate** — add check 2d to nightly-commit-review SKILL.md; CRITICAL urgency, first nightly fire 2026-08-25 02:37 AM

## Parking Lot (future runs)
- **Step 9K: Stale subconscious PR report** (run 111 candidate) — list open draft PRs with subconscious/run- branches, log count, comment on oldest >21d. Mandate condition met (≥3 open), low urgency vs today's winner.
- **Step 9L: Replacement substrate health monitor** (run 112+ candidate) — scan ops/routines/logs/ for expected daily routine logs; alert if any older than 48h. Substrate too new (migrated 2026-08-24); needs 2+ days baseline before monitoring adds value.
- **middleware-level block_demo_role FastAPI guard** (M-effort, human-approval required) — GH #669 tracks 95+ routers missing Depends(block_demo_role). PR #653 (12d draft) has per-router proposal. Architectural decision needed (middleware vs per-router).

## Human-action required (blocked — not subconscious scope)
- **GH #399**: AUTOPILOT_GH_TOKEN expired Day 46+. Rotate in Railway → GitHub Secrets. Unblocks 30 ai-ready issues.
- **GH #403**: KB autopopulate 32+ days dark. Add ANTHROPIC_API_KEY + SUPABASE_URL + SUPABASE_ANON_KEY to GitHub Actions secrets.
- **GH #669**: 95+ routers missing block_demo_role — human architecture decision required.

## Killed / retired
- GH #403 escalation comment (run 110) — 4+ prior comments with no human action. Diminishing returns. Same mechanism won't change outcome.
- GH #669 architecture comment — non-structural; subconscious recommends, doesn't redesign router guards.
- widget_drift_topic — retired run 70, widget-only human task.
- ai_human_handoff — frozen idea, 3+ rejections.

## Open questions for human
1. React 18→19 migration: when planned? (Step 9J will hold these PRs until manually merged)
2. Stripe v11→v15: same question — deliberate migration needed, Step 9J will hold
3. GH #399 / #403: ETA on credential rotation? Unblocks 30 ai-ready issues + KB autopopulate
