# Winning Concept — Run 114 (2026-08-31-pm)

## Recommendation
Add Step 9K to `.claude/skills/nightly-commit-review/SKILL.md` — a nightly stale subconscious draft PR audit that counts open `subconscious/*` PRs, warns when ≥3 are stale (>30 days), and escalates with a PR comment when ≥5 are stale or any exceeds 60 days.

## Why This, Why Now
Run 113 recommended Step 9K as the governance-mandated winner with `autonomous_executable_run_114_if_not_approved`. Step 9K is absent from SKILL.md (confirmed: grep returns 0). The carry-forward mandate fires this run. The 23 existing run directories and 5+ open draft subconscious PRs tracked since run 102 confirm the condition. Nightly-2026-08-31 ran but did not fire Step 9K — the only execution path for this class of improvement is direct implementation in this run. The same autonomous-executable SKILL.md channel has successfully delivered Steps 9C, 9E, 9F, 9G, 9I, and 9J; Step 9K follows exactly the same pattern.

## Implementation Sketch
1. Edit `.claude/skills/nightly-commit-review/SKILL.md` — insert Step 9K block after Step 9J's summary log line (line 424) and before the "10. Commit report" step.

**Step 9K block to insert:**
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
        Body: "Subconscious PR audit (Step 9K): This PR is {age_days} days old. There are {stale_count} stale subconscious draft PRs (>30 days). Please review, merge, or close to prevent backlog accumulation."
6. Add to nightly report summary line:
   "Step 9K: {total_count} subconscious PRs open ({stale_count} stale, {critical_count} critical)"
```

2. **Bonus (same commit):** Fix Step 9J detection — change Step 9J.1 from `list_pull_requests(creator='dependabot[bot]')` to `search_pull_requests` with query `'is:pr is:open author:app/dependabot'`. This fixes the "No Dependabot PRs detected" failure on nightly-2026-08-30.

3. Commit: `feat(nightly): add Step 9K stale subconscious PR audit + fix Step 9J detection`

## What This Replaces
Active direction: run 113 winner (Step 9K — same recommendation). This implements it.

## Confidence
**HIGH** — governance mandate binding; condition confirmed (23 run dirs, 5+ open PRs); same SKILL.md-edit channel as 6 prior Step 9x implementations; GitHub list_pull_requests already used in Step 9J; `head.ref` startswith `subconscious/` is exact; escalation comment uses only tools already used in Step 9C/9I; 0 production code changes; 0 architectural risk.

## Run 115 Mandate
1. Verify Step 9K fires in nightly-2026-09-01: `grep 'Step 9K' ops/routines/logs/nightly-commit-review-2026-09-01.md`
2. Count: how many open subconscious PRs? How many stale (>30d)?
3. Step 9J detection fix: did Step 9J find Dependabot PRs on 2026-09-01?
4. GH #684 SUPABASE_ACCESS_TOKEN: set in Railway?
5. os_tool_executions.py: stable (0 commits 4d+)? If yes: run 115 god class split candidate.
6. M8: OAuth/service_role HOLD resolved? Calendar+CRM deploy progress?
