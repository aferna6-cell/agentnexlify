# Winning Concept — Run 114 (2026-08-30-pm)

## Recommendation
Direct implementation (autonomous-executable carry-forward): Add Step 9K to `.claude/skills/nightly-commit-review/SKILL.md` + fix Step 9J detection in same commit.

## Why This, Why Now
Governance mandate fires: Step 9K was run 113 winner with `autonomous_executable: true` and escalation condition "Autonomous-executable if not approved by run 114 (1st carry-forward mandate)." Condition confirmed in run 113 (≥3 open subconscious PRs). Precedent: Step 9G, 9I, 9J fix all implemented directly at carry-forward. Step 9J detection failure documented in consecutive nightly logs — same-file fix costs nothing extra.

## Implementation

### Step 9K — insert after Step 9J block (after line 424 of SKILL.md, before "10.")

```markdown
9K. **(Subconscious PR Audit)** Audit open subconscious draft PRs for staleness:
    1. Call `mcp__github__list_pull_requests` with `state: "open"`, `per_page: 50`.
    2. Filter: keep only PRs where `head.ref` starts with `"subconscious/"`.
    3. For each, compute `age_days = (now - created_at).days`.
    4. Compute:
       - `total_count` = total open subconscious PRs
       - `stale_count` = PRs where age_days > 30
       - `critical_count` = PRs where age_days > 60
    5. If `stale_count < 3`:
         Log: "Step 9K: {total_count} open subconscious PRs — {stale_count} stale — under threshold"
         Skip remaining steps.
       If `stale_count >= 3` OR `critical_count >= 1`:
         Log to nightly report: "⚠ Step 9K: {total_count} open subconscious PRs, {stale_count} stale (>30d), {critical_count} critical (>60d)"
         List each stale PR: "  - #{number} {title} ({age_days}d)"
       If `stale_count >= 5` OR `critical_count >= 1`:
         Find oldest open subconscious PR (max age_days).
         Post comment via `mcp__github__add_issue_comment` on that PR:
           "Subconscious PR audit (Step 9K): This PR is {age_days} days old. There are currently {stale_count} stale subconscious draft PRs (>30 days). Please review, merge, or close to prevent backlog accumulation."
    6. Add to nightly report summary: "Step 9K: {total_count} subconscious PRs open ({stale_count} stale, {critical_count} critical)"
```

### Step 9J detection fix — same SKILL.md edit (Step 9J.1)
- FROM: `mcp__github__list_pull_requests` with state="open", filter `user.login == "dependabot[bot]"`
- TO: `mcp__github__search_pull_requests` with query `"repo:aferna6-cell/agentnexlify is:pr is:open author:app/dependabot"`

## What This Replaces
Step 9J: detection method replaced (more reliable). Step 9K: new, additive. No other behavior changes.

## Run 115 Mandate
1. Verify Step 9K fires in nightly-2026-08-31: `grep 'Step 9K' ops/routines/logs/nightly-commit-review-2026-08-31.md`
2. Count: how many open subconscious PRs? How many stale (>30d)?
3. Step 9J: did `search_pull_requests` find Dependabot PRs on 2026-08-31?
4. GH #684 SUPABASE_ACCESS_TOKEN: set in Railway? Brain connector age reset?
5. os_tool_executions.py: stable 3+ days? If yes, run 115 candidate for god class split.
6. M8 eval harness: stable? If eval pass_rate data exists for 3+ runs, revisit CI gate idea.

## Confidence
HIGH — governance mandate binding, condition confirmed, implementation is additive SKILL.md edit only.
