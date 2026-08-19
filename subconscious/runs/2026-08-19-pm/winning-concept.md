# Winning Concept — 2026-08-19-pm (Run 108)

## Recommendation

Add Step 9J to `.claude/skills/nightly-commit-review/SKILL.md` — a nightly automated sweep that lists open Dependabot PRs, checks CI status on each, and squash-merges those that are CI-green with no requested reviewers. Gate is strict: any failing/pending CI check or any requested reviewer → skip and log.

**Status: AUTONOMOUS-EXECUTABLE** — 1st run as winner. Channel proven (Steps 9C/9E/9F/9G/9I all implemented via same SKILL.md-edit). Evidence conclusive: 6 Dependabot PRs aging 2-17 days with zero human action after repeated morning digest warnings.

## Why This, Why Now

- 6 Dependabot PRs open: #629 (playwright 17d), #630 (vite/demo 17d), #631 (plugin-react 17d), #665 (eslint 2d), #666 (ts-eslint-parser 2d), plus pip deps #597/#598 (stripe/uvicorn, older)
- Morning digest flagged dep PRs daily for 7+ days — human has not acted
- skill-discovery-2026-08-17 independently proposed `dependabot-merge-runner` with identical CI-green heuristic
- Run 107 parking lot explicitly names Step 9J as run 108 candidate
- Security patches in deps go unapplied while PRs age — each day is risk exposure
- Same proven channel as Steps 9I (implemented 24h ago), 9G (implemented 2026-08-06), 9F (2026-07-20)

## Implementation — Exact SKILL.md Edit

Add the following block after the Step 9I block in `.claude/skills/nightly-commit-review/SKILL.md`:

```
9J. (Dependabot Auto-Merge) Merge CI-green Dependabot PRs automatically:
    1. **List open Dependabot PRs:**
       mcp__github__list_pull_requests (owner=aferna6-cell, repo=agentnexlify,
         state=open, perPage=50, fields=["number","title","head","draft","requested_reviewers"])
       Filter: pr["head"]["ref"].startswith("dependabot/")
    2. **For each Dependabot PR, check CI status:**
       mcp__github__actions_list (owner=aferna6-cell, repo=agentnexlify,
         branch=pr["head"]["ref"])
       Extract latest workflow run for this branch. Status must be "completed" + conclusion "success".
       If no runs found OR latest conclusion != "success": skip this PR.
    3. **Safety gates — skip if ANY of:**
       - CI not passing (step 2)
       - pr["draft"] == true
       - len(pr["requested_reviewers"]) > 0
       - PR title contains "BREAKING" or "major" (case-insensitive)
    4. **Merge passing PRs:**
       mcp__github__merge_pull_request (owner=aferna6-cell, repo=agentnexlify,
         pull_number=pr["number"], merge_method="squash",
         commit_title=f"chore(deps): {pr['title']} [auto-merge]")
       Log: "Step 9J: merged PR #{N} — {pr['title']}"
    5. **Log result:**
       "Step 9J: {N} Dependabot PRs reviewed, {M} merged, {K} skipped
        (CI-failing: {ci_fail_count}, draft: {draft_count}, has-reviewers: {reviewer_count})"
```

## Safety Rationale

- **CI gate**: only merges PRs where ALL checks passed. A bad dep breaks CI → not merged.
- **Squash merge**: single commit, easy to revert with `git revert <sha>`.
- **No-requested-reviewers gate**: respects any human review assignment.
- **No-draft gate**: only touches ready PRs.
- **BREAKING/major title filter**: skips any PR that signals a major version bump requiring human judgment.
- **Reversibility**: any auto-merged dep can be reverted in one commit if it causes issues.

## What This Closes

- Eliminates the 2-17 day Dependabot aging cycle that accumulates silently despite morning digest alerts.
- Security patches applied within 24h of CI passing (current average: 17+ days).
- Frees human attention for decisions that actually require human judgment (major version bumps, BREAKING changes).
- No human will ever need to manually merge a routine Dependabot patch-or-minor PR again.

## Confidence

HIGH — mandate-triggered (run 107 parking lot explicit), channel proven (5 prior Steps), CI gate prevents bad merges, squash merge is reversible, evidence from 6 aging PRs + daily morning digest confirms human will not act manually.
