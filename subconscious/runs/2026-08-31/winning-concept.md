# Winning Concept — Run 114 (2026-08-31)

## Recommendation
Add Step 9K to `.claude/skills/nightly-commit-review/SKILL.md` — a stale subconscious draft PR audit that counts open `subconscious/*` branch PRs nightly, warns when ≥3 are stale (>30d), and escalates with a comment on the oldest when ≥5 stale or any exceeds 60 days.

## Why This, Why Now
Governance mandated Step 9K in run 113 on condition ≥3 open subconscious PRs. That condition is confirmed (23 historical run directories, 5+ open PRs tracked since run 102). The run 113 mandate is binding: "if >=3, Step 9K is run 113 winner." Step 9K is absent from SKILL.md (grep returns 0), making this the 1st carry-forward, which triggers the autonomous-executable escalation per the established governance precedent (Steps 9F/9G/9I/9J initial add all implemented at 1st or 3rd carry-forward). Without Step 9K, the subconscious generates approved recommendations faster than they are reviewed — the PR backlog grows silently forever.

## Implementation Sketch

Edit `.claude/skills/nightly-commit-review/SKILL.md` — add Step 9K block immediately after the Step 9J closing section:

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
      - Add warning to nightly report: "⚠ Step 9K: Stale subconscious PRs need review"
   c. Additionally, if `stale_count >= 5` OR `critical_count >= 1`:
      - Find the oldest open subconscious PR (max `age_days`).
      - Post comment via `mcp__github__add_issue_comment` on that PR:
        Body: "Subconscious PR audit (Step 9K): This PR is {age_days} days old. {stale_count} stale subconscious draft PRs (>30d) open. Please review, merge, or close to prevent backlog accumulation."
6. Add to nightly summary line:
   "Step 9K: {total_count} subconscious PRs open ({stale_count} stale, {critical_count} critical)"
```

## Bonus Action (same SKILL.md commit)
Fix Step 9J detection: in Step 9J.1, replace `mcp__github__list_pull_requests(creator="dependabot[bot]")` with `mcp__github__search_pull_requests(query="is:pr is:open author:app/dependabot")`. The list API fails to detect bot-authored PRs in headless sessions (confirmed: nightly-2026-08-30 "No Dependabot PRs detected", nightly-2026-08-31 "not scoped in this run").

## What This Replaces
No prior step covered subconscious PR backlog health. Step 9K is purely additive. The previous active direction was Step 9K (run 113 recommendation) — this run implements it.

## Confidence
**HIGH** — governance mandate binding; 1st carry-forward autonomous-executable fires; same SKILL.md channel as Steps 9F/9G/9I/9J (all successful); GitHub list_pull_requests already used in Step 9J; filter by head.ref is exact and deterministic; escalation comment adds no new tool not already used in Step 9C/9I; 0 production code changes; 0 architectural risk.

## Run 115 Mandate
1. Verify Step 9K fires in nightly-2026-09-01: `grep 'Step 9K' ops/routines/logs/nightly-commit-review-2026-09-01.md`
2. Count: how many open subconscious PRs? How many stale (>30d)? How many critical (>60d)?
3. Step 9J detection fix: did Step 9J find Dependabot PRs on 2026-09-01? Were any rebases triggered?
4. os_tool_executions.py: stable now (3+ days no commits)? If yes: run 115 candidate for god class split.
5. GH #684 SUPABASE_ACCESS_TOKEN: set in Railway after bonus comment?
6. Brain connector: still 39d+ stale, or resolved?
