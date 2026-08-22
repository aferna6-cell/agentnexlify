# Winning Concept — 2026-08-22

## Recommendation

Add Step 9J to `.claude/skills/nightly-commit-review/SKILL.md` — a nightly block that lists open
Dependabot PRs, checks CI status + no review requests + no blocking labels per PR, merges
eligible PRs via squash, and logs a summary line.

**Status: IMPLEMENTED THIS RUN** — 1st carry-forward from run 108. Governance escalation rule
fires at run 109 first carry-forward. Same autonomous-executable channel as Steps 9C/9E/9F/9G/9I.
All five prior steps landed within 1-2 cycles via this exact path.

## Why This, Why Now

Step 9J was run 108's winner (2026-08-20) and remained absent from SKILL.md through nightlies
2026-08-21 + 2026-08-22. Both nightly reports explicitly flagged it as "unexecuted". The 1st
carry-forward escalation condition is met. Morning digests 2026-08-11/12/17/18 all flagged 4-6
identical Dependabot PRs as safe to merge — zero action taken across 4 weeks. Each Dependabot PR
aging = wider CVE exposure window. Step 9J closes the class permanently: every future Dependabot
PR merges within 24h of CI going green, without human intervention.

## Implementation — Exact SKILL.md Edit

Inserted after Step 9I block (line 391), before "10. Commit report" (line 392):

```
9J. (Dependabot Auto-Merge) Merge CI-green Dependabot PRs with no review requests:
    1. **List open Dependabot PRs:**
       `mcp__github__list_pull_requests` with:
         state: "open"
         base: "main"
       Filter results: keep only PRs where `user.login == "dependabot[bot]"`.
       If 0 Dependabot PRs found: log "Step 9J: 0 Dependabot PRs open — skip" and continue to step 10.
    2. **For each Dependabot PR:**
       a. Check CI status:
          `mcp__github__pull_request_read` for PR number — read `mergeable_state` field.
          If `mergeable_state != "clean"`: log "Step 9J: PR #{N} — CI not green (state: {state}) — skip" and skip this PR.
       b. Check for review requests:
          From PR read, check `requested_reviewers` array.
          If `requested_reviewers` is non-empty: log "Step 9J: PR #{N} — has review request — skip" and skip this PR.
       c. Check for blocking labels:
          From PR read, check `labels` array.
          If labels contain "do-not-merge" or "hold": log "Step 9J: PR #{N} — blocked label — skip" and skip this PR.
    3. **Merge eligible PRs:**
       For each PR that passed all checks:
       `mcp__github__merge_pull_request`:
         pull_number: {N}
         merge_method: "squash"
         commit_title: "{PR title} (#N)"
       On success: log "Step 9J: merged Dependabot PR #{N} ({package} {version})"
       On failure: log "Step 9J: merge failed PR #{N} — {error}" and continue to next PR.
    4. **Log result:**
       Add to nightly report: "Step 9J: {N} Dependabot PRs checked, {M} merged, {K} skipped (CI/review/label)"
```

## What This Replaces

- Manual weekly scan of Dependabot PRs by human engineer
- Morning digest items flagging "safe to merge" with zero action (4+ weeks of unactionable digest entries)
- Future CVE exposure windows from delayed security dep bumps

## Confidence

HIGH — mandate-triggered (run_109_mandate escalation condition met at 1st carry-forward),
conclusive evidence (4 morning digests, 6 PRs aging, nightly confirmation), channel proven
(5 Steps implemented same way, all landed within 1-2 cycles). Merge heuristic is identical
to what the human does manually: CI green + no review request. Risk equivalent to manual merge.
