# Improvement Backlog — Run 112 (2026-08-29-pm)

## Active
- **Step 9J rebase trigger**: Edit Step 9J block in `.claude/skills/nightly-commit-review/SKILL.md` to post `@dependabot rebase` on unknown-state PRs (dedup 48h, cap 5/run). **Implemented directly this run** (2nd carry-forward autonomous-executable).

## Parking Lot (survived debate — may be picked in future runs)
- **Step 9K: Stale subconscious PR report** (Idea 2) — Add Step 9K block to nightly SKILL.md: list open PRs with head branch "subconscious/*", report count + age, flag >30d as stale. Report-only, S-effort. Next run candidate if subconscious PRs still >=3.
- **Step 9L: Managed-agents telemetry step** (Idea 4) — Add managed-agents session health check to nightly (query /api/admin/loop-health, flag sessions with >5 errors/24h). Evidence: PR #677 fixed 7 managed-agents findings; no daily health signal exists. M-effort; revisit after Step 9K lands.
- **GH #684 SUPABASE_ACCESS_TOKEN setup** — Promoted to Bonus Action this run. Human-only: set token in Railway after receiving comment on #684.

## Rejected This Run
- **GH #669 middleware implementation sketch** (Idea 3) — Killed: insufficient rigor to claim "implementation-ready" without architectural review; premature middleware sketch could mislead implementer. Let issue-to-pr-loop handle when #399 resolved.

## Questions for Next Run (Run 113)
1. Did @dependabot rebase trigger fire on 2026-08-30? How many rebases triggered?
2. Did any Dependabot PRs become clean + merge within 24-48h of rebase trigger?
3. How many open subconscious PRs exist? (Step 9K threshold: >=3)
4. GH #684: SUPABASE_ACCESS_TOKEN set by human after bonus comment?
5. GH #669: any middleware fix PR from issue-to-pr-loop? (Day 10+ stalled, loop still blocked by #399)
