# Winning Concept — Run 111 (2026-08-29)

## Recommendation
Edit the Step 9J block in `.claude/skills/nightly-commit-review/SKILL.md` to add `@dependabot rebase` trigger logic for Dependabot PRs in `mergeable_state: unknown`.

## Why This, Why Now
Step 9J (Dependabot auto-merge) was added in run 109 but has had 0% effectiveness for two consecutive nightlies because GitHub returns `mergeable_state: unknown` for Dependabot PRs whose base has diverged. The fix — trigger `@dependabot rebase` when state is unknown — was the run 110 winner and is now the 1st carry-forward, autonomous-executable mandate. Without this fix, 20+ security dependency bumps accumulate indefinitely while the CVE window stays at 2-3 weeks. The implementation sketch is fully specified (10-15 lines), the mechanism is proven (same SKILL.md channel as Steps 9C/9F/9G/9I/9J), and the dedup/cap guards prevent abuse. No new dependencies, no code changes, no migrations.

## Implementation Sketch

Edit `.claude/skills/nightly-commit-review/SKILL.md` — Step 9J block. After the line `mergeable_state != "clean" → skip (not ready to merge)`, add:

```
   b2. If mergeable_state == "unknown" (stale base — mergeability not yet computed):
       - Call mcp__github__list_issue_comments on this PR (owner, repo, pr_number)
       - Filter comments where author == "dependabot[bot]" OR body contains "@dependabot rebase"
         AND created_at > (now - 48h)
       - If any such comment found within 48h: skip (dedup guard — already triggered recently)
       - If no such comment (or all older than 48h):
         * Post comment via mcp__github__add_issue_comment: body = "@dependabot rebase"
         * Increment rebase_trigger_count
         * Log: "Step 9J: triggered rebase on PR #N (state: unknown, title: T)"
       - If rebase_trigger_count >= 5: stop checking remaining PRs (flood cap)
       - Note: this PR will not merge this run; after rebase + CI it will become 'clean'
             and merge on the next nightly execution
```

Updated log line format:
```
Step 9J: {N_checked} checked, {M_merged} merged, {K_skipped} skipped (CI/review/label), {R_triggered} rebase-triggered (unknown state)
```

## What This Replaces
Run 110's recommendation was identical — this is the carry-forward implementation. The prior Step 9J block (from run 109) only handled `mergeable_state: clean` PRs. No prior active direction is superseded.

## Confidence
**HIGH** — two consecutive nightlies confirm `unknown` state; GitHub documentation confirms `@dependabot rebase` is the documented trigger for remergeability recomputation; dedup/cap guards address all identified failure modes; same mechanism proven by 6 prior Step 9x implementations.

## Bonus Action (low-cost, not mandated)
Post a comment on GH #684 with exact SUPABASE_ACCESS_TOKEN setup path:
- Railway → Project → Variables → add `SUPABASE_ACCESS_TOKEN`
- Get value from: Supabase dashboard → Settings → Access Tokens → create new token
- This unblocks brain connector + Step 9E tracking. Different from ANTHROPIC_API_KEY (which resolved KB stale).

## Run 112 Mandate
1. Verify `@dependabot rebase` trigger in nightly post-2026-08-29: `grep 'triggered rebase' ops/routines/logs/nightly-commit-review-*.md`
2. Count: how many rebases triggered (should be ≤5 per run)?
3. After 24-48h: did any Dependabot PRs become `clean` + merge on next nightly?
4. Final Step 9J log line format: `N checked, M merged, K skipped, R rebase-triggered`
5. GH #684 (brain connector): SUPABASE_ACCESS_TOKEN set after bonus comment?
6. GH #669: any middleware PR from loop? (Day 10+ stalled)
7. Step 9K (stale PR report) is run 112 candidate if subconscious PRs still ≥3 open.
