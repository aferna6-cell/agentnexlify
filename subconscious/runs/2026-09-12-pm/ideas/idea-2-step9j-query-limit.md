# Idea 2: Step 9J — Cap search_pull_requests to limit=5

**Category:** workflow_efficiency
**Effort:** XS
**Confidence:** HIGH

## Evidence
- Step 9J (Dependabot auto-merge) finds 19 PRs but processes only 2 per run.
- Reason: 17/19 skipped "due to token budget" — nightly session budget exhausted before Step 9J gets to most PRs.
- Run 115 confirmed: "Step 9J: 19 Dependabot PRs, triggered rebase on 2; 17/19 skipped due to token budget."
- Same pattern on nightly-2026-09-06, nightly-2026-09-10 (confirmed by runs 116-117).
- CVE window: 2-3 weeks average for Dependabot PRs that can't get processed.

## Action
Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9J block:
1. Add `limit=5` to the `search_pull_requests` query (oldest 5 by created_at asc).
2. Log: "Step 9J: {TOTAL_FOUND} found, checked oldest 5, {M} merged, {R} rebase-triggered, {K} skipped."
3. This ensures all 5 checked PRs get processed within token budget, vs 2/19 currently.

## Impact
- Dependabot PR merge rate: 2/19 = 10% → 5/5 = 100% (within checked batch).
- Security patches land within 24h of CI passing (next nightly cycle).
- No net slowdown: oldest 5 PRs get processed first each run; over 4 runs, all 19 PRs get a turn.
