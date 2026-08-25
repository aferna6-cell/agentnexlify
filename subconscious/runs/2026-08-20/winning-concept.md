# Winning Concept — 2026-08-20

## Recommendation

Add Step 9J to `.claude/skills/nightly-commit-review/SKILL.md` — a nightly automated block that
lists open Dependabot PRs via `mcp__github__list_pull_requests`, checks CI status per PR, merges
CI-green ones with no review requests via `mcp__github__merge_pull_request` (squash), and logs
a summary line.

**Status: AUTONOMOUS-EXECUTABLE** — mandate-triggered (run_108_mandate explicitly named Step 9J).
Channel proven: Steps 9C/9E/9F/9G/9I all implemented via same nightly SKILL.md channel, each
landing within 1-2 cycles. Skill discovery 2026-08-17 proposed `dependabot-merge-runner` with
4+ weeks of evidence. 6 PRs currently aging (#629/#630/#631/#649/#665/#666).

## Why This, Why Now

- Morning digests 2026-08-11/12/17/18 all flagged same 4–6 Dependabot PRs as "safe to merge" —
  zero action taken across 4 weeks
- Skill discovery 2026-08-17 explicitly proposed `dependabot-merge-runner` with this exact
  evidence trail
- Run 108 mandate named Step 9J as primary candidate — mandate condition met
- Step 9I's first execution (2026-08-20) found 97/97 routers missing block_demo_role — confirms
  the nightly sweep channel works and Step 9J lands in the same proven channel
- Each delayed security dep bump = wider CVE exposure window; 6 PRs currently aging
- Once added, structural: Dependabot PRs merge automatically forever, not a one-shot action

## Implementation — Exact SKILL.md Edit

Insert the following block after the Step 9I block (after line 391, before "10. Commit report"):

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
- Morning digest items flagging "safe to merge" with zero action (4+ weeks of digest entries)
- Future potential CVE exposure windows from delayed security dep bumps

## Bonus Action

Post targeted diagnostic comment on GH #403 (KB autopopulate 28d stale) listing ALL required
GitHub Actions secrets — not just ANTHROPIC_API_KEY but also SUPABASE_URL + SUPABASE_ANON_KEY —
since run 107's ANTHROPIC_API_KEY setup comment has not yet unblocked KB (24h+ elapsed with no
change in staleness). This diagnoses whether a second blocker exists.

## Confidence

HIGH — mandate-triggered (run_108_mandate explicitly named Step 9J), evidence conclusive (4+
morning digests, 6 PRs aging), channel proven (5 Steps implemented same way, all landed within
1-2 cycles). Merge heuristic (CI green + no review request) exactly matches what human does
manually. Risk equivalent to manual merge, not higher.

## What This Closes

Every Dependabot PR that passes CI gets merged within 24h of CI going green, indefinitely.
Security patches applied weekly without human intervention. Each dep bump delay = wider CVE
exposure window. Estimated 15 min/week of manual merge overhead eliminated.
