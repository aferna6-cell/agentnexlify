# Winning Concept — Run 113 (2026-08-30)

## Recommendation
Add Step 9K to `.claude/skills/nightly-commit-review/SKILL.md` — a stale subconscious draft PR audit that counts open `subconscious/*` PRs nightly, warns when ≥3 are stale (>30 days), and escalates when ≥5 or any PR exceeds 60 days.

## Why This, Why Now
Governance mandated this at 1st carry-forward (run 106 proposed, deferred pending ≥3 open subconscious PRs condition). Run 112 mandate explicitly states: "if >=3, Step 9K is run 113 winner." Condition is confirmed: 23 historical run directories exist, governance tracked 5+ open subconscious draft PRs since run 102. Without this audit, approved improvements accumulate as unmerged draft PRs indefinitely — the subconscious loop generates work faster than it can be reviewed. Step 9K closes this loop, compounding permanently once added.

## Implementation

Edit `.claude/skills/nightly-commit-review/SKILL.md` — add Step 9K block after the Step 9J block.

**Add after the Step 9J closing section:**

```markdown
### Step 9K — Stale Subconscious Draft PR Audit

1. Call `mcp__github__list_pull_requests` with `state: "open"`, `per_page: 50`.
2. Filter results: keep only PRs where `head.ref` starts with `"subconscious/"`.
3. For each matching PR, compute `age_days = (now - created_at).days`.
4. Compute:
   - `total_count` = total open subconscious PRs
   - `stale_count` = PRs where `age_days > 30`
   - `critical_count` = PRs where `age_days > 60`
5. Threshold logic:
   a. If `stale_count < 3`:
      - Log: "Step 9K: {total_count} open subconscious PRs — {stale_count} stale (>30d) — under threshold"
      - Skip remaining steps.
   b. If `stale_count >= 3` OR `critical_count >= 1`:
      - Log to nightly report: "Step 9K: {total_count} open subconscious PRs, {stale_count} stale (>30d), {critical_count} critical (>60d)"
      - List each stale PR: "  - #{number} {title} ({age_days}d)"
      - Add warning banner to nightly report: "⚠ Step 9K: Stale subconscious PRs need review"
   c. Additionally, if `stale_count >= 5` OR `critical_count >= 1`:
      - Find the oldest open subconscious PR (max `age_days`).
      - Post comment via `mcp__github__add_issue_comment` on that PR:
        Body: "Subconscious PR audit (Step 9K): This PR is {age_days} days old. There are currently {stale_count} stale subconscious draft PRs (>30 days). Please review, merge, or close this PR to prevent backlog accumulation."
6. Add to nightly report summary line:
   "Step 9K: {total_count} subconscious PRs open ({stale_count} stale, {critical_count} critical)"
```

**Initialize before loop:** No loop state needed — each nightly is independent.

**Place in SKILL.md:** Immediately after the Step 9J closing block (search for `Step 9J` section end).

## What This Replaces
No prior step covered this. Step 9K is additive — does not modify or remove any prior behavior.

## Confidence
**HIGH** — governance mandate binding; condition ≥3 confirmed; same autonomous-executable SKILL.md channel as 6 prior Step 9x implementations; GitHub list_pull_requests already used in Step 9J; filter by `head.ref` startswith `subconscious/` is exact; escalation comment adds no new tool not already used in Step 9C/Step 9I; 0 production code changes; 0 architectural risk.

## Bonus Actions

### 1. Fix Step 9J Detection (bonus for implementing agent)
Step 9J "No Dependabot PRs detected" on 2026-08-30 is a detection failure (new, separate from the unknown-state issue fixed in run 112). The fix: change Step 9J.1 from `mcp__github__list_pull_requests(creator="dependabot[bot]")` to `mcp__github__search_pull_requests` with query `"is:pr is:open author:app/dependabot"`. The search API is more reliable for bot-authored PRs in headless sessions.

Implement this fix at the same time as Step 9K (same SKILL.md edit, same commit).

### 2. Post Comment on GH #684 (SUPABASE_ACCESS_TOKEN)
Verify whether a SUPABASE_ACCESS_TOKEN setup comment was posted by the nightly-2026-08-30 session. If not already posted:

Post on GH #684:
```
SUPABASE_ACCESS_TOKEN setup — required to unblock brain connector and Step 9E tracking:

1. Supabase dashboard → Settings → Access Tokens → Create new token (name: "agentnexlify-brain")
2. Railway → Project → Variables → Add: SUPABASE_ACCESS_TOKEN = <value from step 1>
3. Redeploy backend service after saving

Once set, Step 9E will track its 90-day rotation schedule automatically.

The brain connector has been stalled since 2026-07-23 (38+ days, threshold: 14 days).
```

## Run 114 Mandate
1. Verify Step 9K fires in nightly-2026-08-31: check `grep 'Step 9K' ops/routines/logs/nightly-commit-review-2026-08-31.md`
2. Count: how many open subconscious PRs? How many stale (>30d)?
3. Step 9J detection fix (bonus): was it implemented? Did Step 9J find Dependabot PRs on 2026-08-31?
4. GH #704 block_demo_role: merged or still open?
5. GH #684 SUPABASE_ACCESS_TOKEN: set in Railway after bonus comment?
6. os_tool_executions.py: stable now (3+ days no commits)? If yes, run 114 candidate for god class split.
