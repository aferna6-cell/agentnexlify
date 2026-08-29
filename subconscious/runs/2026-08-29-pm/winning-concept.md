# Winning Concept — Run 112 (2026-08-29-pm)

## Recommendation
Edit the Step 9J block in `.claude/skills/nightly-commit-review/SKILL.md` to add `@dependabot rebase` trigger logic for Dependabot PRs in `mergeable_state: unknown` — **implemented directly this run** (2nd carry-forward, autonomous-executable mandate).

## Why This, Why Now
Step 9J (Dependabot auto-merge) has had 0% effectiveness across two consecutive nightlies (2026-08-28, 2026-08-29) because GitHub returns `mergeable_state: unknown` for PRs whose base has diverged. The only trigger for mergeability recomputation is a `@dependabot rebase` command. Run 110 was the 1st carry-forward recommendation; run 111 was designated "1st carry-forward autonomous-executable" but remained a recommendation. Run 112 is the 2nd consecutive carry-forward — governance mandates direct implementation per established precedent (Steps 9I and 9J initial add were both implemented at 1st carry-forward; Step 9F at 3rd). 20+ Dependabot PRs are aging including potential CVE patches; the CVE window stays at 2-3 weeks indefinitely without this fix.

## Implementation Sketch

Edit `.claude/skills/nightly-commit-review/SKILL.md` — Step 9J block (lines 392-411).

**Current Step 9J.2.a:**
```
a. CI status: `mcp__github__pull_request_read` for PR number — check `mergeable_state`.
   If `mergeable_state != "clean"`: log "Step 9J: PR #{N} — CI not green ({state}) — skip" and skip.
```

**Replace with:**
```
a. CI status: `mcp__github__pull_request_read` for PR number — check `mergeable_state`.
   b2. If `mergeable_state == "unknown"` (stale base — mergeability not yet computed):
       - Call `mcp__github__list_issue_comments` (owner, repo, pr_number)
       - Check comments where (author == "dependabot[bot]" OR body contains "@dependabot rebase")
         AND created_at > (now minus 48 hours)
       - If any such comment found: log "Step 9J: PR #{N} — rebase already triggered <48h — skip" and skip.
       - If none found (or all older than 48h):
           * Post comment via `mcp__github__add_issue_comment`: body = "@dependabot rebase"
           * Increment rebase_trigger_count
           * Log: "Step 9J: triggered rebase on PR #{N} ({title})"
           * If rebase_trigger_count >= 5: break (flood cap — stop checking remaining PRs)
       - Note: this PR will not merge this run; after rebase + CI passes it becomes 'clean'
         and merges on the next nightly execution.
   If `mergeable_state != "clean"` AND `mergeable_state != "unknown"`:
       log "Step 9J: PR #{N} — CI not green ({state}) — skip" and skip.
```

**Update Step 9J.4 log line:**
```
Add to nightly report: "Step 9J: {N} Dependabot PRs checked, {M} merged, {K} skipped
(CI/review/label), {R} rebase-triggered (unknown state)"
```

**Initialize rebase_trigger_count = 0 before the loop (Step 9J.2).**

## What This Replaces
The prior Step 9J block (from run 109) only handled `mergeable_state: clean` PRs. This adds the `unknown` state branch without removing the clean-state merge path. No prior active direction is superseded.

## Confidence
**HIGH** — two nightlies confirm `unknown` state; GitHub documentation confirms `@dependabot rebase` is the documented trigger for mergeability recomputation; dedup/cap guards address all identified failure modes; same autonomous-executable SKILL.md channel as 6 prior Step 9x implementations; 0 architectural risk (Dependabot-only filter, no production code changes).

## Bonus Action
Post a comment on GH #684 with exact SUPABASE_ACCESS_TOKEN setup path:
- Railway → Project → Variables → add `SUPABASE_ACCESS_TOKEN`
- Get value from: Supabase dashboard → Settings → Access Tokens → Create new token
- This unblocks brain connector + Step 9E tracking

## Run 113 Mandate
1. Verify `@dependabot rebase` trigger fires in nightly-2026-08-30: `grep 'triggered rebase' ops/routines/logs/nightly-commit-review-2026-08-30.md`
2. Count: how many rebases triggered (≤5)? How many PRs checked?
3. 24-48h after: did any Dependabot PRs become `clean` + merge on next nightly?
4. GH #684: SUPABASE_ACCESS_TOKEN set after bonus comment?
5. Step 9K (stale PR report) readiness: count open subconscious PRs — if >=3, Step 9K is run 113 winner.
6. GH #669 middleware PR: any progress? (Day 10+ stalled)
