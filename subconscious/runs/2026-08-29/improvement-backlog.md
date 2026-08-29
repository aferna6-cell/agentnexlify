# Improvement Backlog — Run 111 (2026-08-29)

## Active
- **Fix Step 9J: add `@dependabot rebase` trigger for `mergeable_state: unknown` Dependabot PRs** — edit Step 9J block in `.claude/skills/nightly-commit-review/SKILL.md` (10-15 lines). Run 110 1st carry-forward autonomous-executable. HIGH confidence.

## Parking Lot (survived debate, not chosen)

- **Step 9K: Stale subconscious draft PR report** — add Step 9K block to nightly after Step 9J. List open PRs with `subconscious/` head branch, flag those draft + >14d stale. Run 109 mandate named this. Run 112 candidate if ≥3 subconscious PRs still open.
- **Step 9D loop-health API diagnostic** — add curl to `/api/admin/loop-health` in Step 9D to replace "UNKNOWN/STALLED" with specific vitals. WEAKENED: URL + auth availability in headless CCR session unverified. Defer until GH #399 resolved.
- **Bonus: GH #684 escalation comment** — post exact Railway + Supabase path for SUPABASE_ACCESS_TOKEN. Low-cost, addresses brain connector 37d stale. Not a subconscious winner but recommended as bonus action.

## Rejected This Run
- **AUTOPILOT_GH_TOKEN GH #399 escalation comment** — KILLED. Same mechanism rejected in run 108 ("non-structural, 4+ prior escalations"). Day 56 provides no new evidence. Pattern: repeated comments without new information have zero marginal effect.

## Questions for Next Run (Run 112)
1. Did `@dependabot rebase` trigger fire? How many rebases? How many became `clean` + merged?
2. GH #684 SUPABASE_ACCESS_TOKEN: set in Railway after bonus comment?
3. GH #669 (class-wide block_demo_role, 10d+): any middleware fix PR?
4. Is subconscious PR count still ≥3 open? (Step 9K readiness condition)
5. Any new production commits after 3-day dry spell?
