# Winning Concept — Run 115 (2026-09-04)

## Recommendation
Edit Step 9J block in `.claude/skills/nightly-commit-review/SKILL.md` — after the existing Dependabot PR detection logic, add a per-PR `mergeable_state` check (cap 10 per run). For `clean` PRs with no blocking labels, call `mcp__github__merge_pull_request` (squash). For `unknown` PRs, post `@dependabot rebase` (already implemented). Log count.

## Why This, Why Now

Step 9J has been in nightly SKILL.md since run 108 (2026-08-20, 15 days). It has never merged a single Dependabot PR. Run 115 nightly confirmed: detection works (19 PRs found via `search_pull_requests`), but the merge loop is absent — SKILL.md ends at detection. The "rate concern" logged in the nightly is a false explanation; 19 sequential API calls is 0.38% of GitHub's hourly rate limit.

The consequence: 19 dependency PRs aging in place, CVE window stays open. Each day without merging extends exposure.

The fix is a SKILL.md edit — same autonomous-executable channel that delivered Steps 9C, 9E, 9F, 9G, 9I, and 9J detection. No production code changes. No architectural risk.

## Implementation Sketch

Edit `.claude/skills/nightly-commit-review/SKILL.md` — find the Step 9J block (currently ends after logging detected PRs). Replace with the following logic after detection:

```markdown
### Step 9J — Dependabot Auto-Merge (updated)

1. Call `mcp__github__search_pull_requests` with query `'is:pr is:open author:app/dependabot repo:aferna6-cell/agentnexlify'`.
2. If 0 results: log "Step 9J: 0 Dependabot PRs open" and skip.
3. Log count: "Step 9J: {count} Dependabot PRs detected."
4. For each PR (process up to 10 per run):
   a. Call `mcp__github__pull_request_read` to get `mergeable_state` and `labels`.
   b. If `mergeable_state == "unknown"`:
      - Post comment via `mcp__github__add_issue_comment`: body "@dependabot rebase"
      - Log: "Step 9J: #{number} unknown — posted @dependabot rebase"
      - Skip to next PR.
   c. If `mergeable_state == "dirty"` or PR has any label in `["do-not-merge", "hold", "blocked"]`:
      - Log: "Step 9J: #{number} skipped — {reason}"
      - Skip to next PR.
   d. If `mergeable_state == "clean"`:
      - Call `mcp__github__merge_pull_request` with `merge_method: "squash"`.
      - Log: "Step 9J: #{number} MERGED — {title}"
      - Increment merged_count.
5. Log summary: "Step 9J: {merged_count} merged, {rebased_count} rebase-requested, {skipped_count} skipped (of {total} detected)."
```

## What This Replaces

Active direction: Step 9J detection (runs 108–115). Detection confirmed working. Merge execution never implemented. This implements the missing half.

## Confidence

**HIGH** — governance mandate binding; Step 9J absence confirmed (nightly log: "Merge eligibility check deferred — requires mergeable_state per-PR read; no merges executed"); same SKILL.md-edit channel as 6 prior Step 9x implementations; `mcp__github__pull_request_read` + `mcp__github__merge_pull_request` already used in this SKILL; `mergeable_state=clean` check is a reliable filter; cap-10 per run limits blast radius; no production code changes; no architectural risk.

## Run 116 Mandate

1. Verify Step 9J merges PRs in nightly-2026-09-05: `grep 'Step 9J.*MERGED' ops/routines/logs/nightly-commit-review-2026-09-05.md`
2. How many of the 19 Dependabot PRs were `clean` vs `unknown` vs `dirty`?
3. os_tool_executions.py: stable (0 commits 4d+)? If yes: run 116 god-class split candidate.
4. GH #684 SUPABASE_ACCESS_TOKEN: set in Railway? (43 days stale, still missing)
5. AUTOPILOT_GH_TOKEN: 62 days old (14 days from 76d threshold) — rotate before run 117.
6. Step 9E early warning: add 60-day threshold? (currently fires only at 76d)
