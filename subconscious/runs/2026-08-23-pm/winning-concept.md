# Winning Concept — 2026-08-23-pm (Run #109)

## Recommendation

Add Step 9J to `.claude/skills/nightly-commit-review/SKILL.md` — a nightly automated block that
lists open Dependabot PRs via `mcp__github__list_pull_requests`, checks CI status per PR, merges
CI-green patch/minor ones with no review requests via `mcp__github__merge_pull_request` (squash),
and logs a summary line. **CRITICAL REFINEMENT vs run 108:** Add major-version bump detection —
parse PR title for semver major bump (X.x → Y.x where Y > X) and skip automatically. Targets
patch and minor bumps only.

**Status: AUTONOMOUS-EXECUTABLE** — 1st carry-forward mandate. Governance escalation_condition:
"Autonomous-executable if not approved by run 109 (1st carry-forward mandate)." Channel proven:
Steps 9C/9E/9F/9G/9I all implemented via same nightly SKILL.md channel.

## Why This, Why Now

- Carry-forward mandate from run 108: escalation_condition met on run 109 (this run)
- Step 9J absent from SKILL.md as of 2026-08-23 (confirmed grep: 0 matches for "9J")
- 19 open Dependabot PRs (vs. 6 cited in run 108) — including major version bumps run 108 didn't guard against
- Major-version safety gap: react 18→19 (#586/#591/#593), stripe v11→v15 (#598), actions/checkout 4→7 (#580) — these MUST be skipped; CI green ≠ semantic compatibility
- Patch/minor PRs accumulating: e.g. #629, #630, #631, #649, #665, #666 (patch/minor bumps safe to auto-merge)
- 4+ morning digests flagged same PRs as "safe to merge" with zero action
- Channel proven: 5 Steps already implemented via same nightly SKILL.md path, each landing in 1-2 cycles

## Implementation — Exact SKILL.md Edit

Insert the following block after the Step 9I block (after line 391 "9I: {N} files scanned..."), before "10. Commit report":

```
9J. (Dependabot Auto-Merge) Merge CI-green patch/minor Dependabot PRs with no review requests:
    1. **List open Dependabot PRs:**
       `mcp__github__list_pull_requests` with:
         state: "open"
         base: "main"
       Filter results: keep only PRs where `user.login == "dependabot[bot]"`.
       If 0 Dependabot PRs found: log "Step 9J: 0 Dependabot PRs open — skip" and continue to step 10.
    2. **For each Dependabot PR:**
       a. Check for major-version bump:
          Parse PR title for pattern "from {old} to {new}". Extract major version from old and new
          using the first digit before the first dot (e.g. "from 18.2.0 to 19.0.0" → old_major=18, new_major=19).
          If new_major > old_major: log "Step 9J: PR #{N} — major version bump ({old}→{new}) — SKIP (human review required)" and skip this PR.
       b. Check CI status:
          `mcp__github__pull_request_read` for PR number — read `mergeable_state` field.
          If `mergeable_state != "clean"`: log "Step 9J: PR #{N} — CI not green (state: {state}) — skip" and skip this PR.
       c. Check for review requests:
          From PR read, check `requested_reviewers` array.
          If `requested_reviewers` is non-empty: log "Step 9J: PR #{N} — has review request — skip" and skip this PR.
       d. Check for blocking labels:
          From PR read, check `labels` array.
          If labels contain "do-not-merge" or "hold": log "Step 9J: PR #{N} — blocked label — skip" and skip this PR.
    3. **Merge eligible PRs:**
       For each PR that passed all checks (minor/patch only, CI clean, no review requests, no blocking labels):
       `mcp__github__merge_pull_request`:
         pull_number: {N}
         merge_method: "squash"
         commit_title: "{PR title} (#{N})"
       On success: log "Step 9J: merged Dependabot PR #{N} ({package} {old_ver}→{new_ver})"
       On failure: log "Step 9J: merge failed PR #{N} — {error}" and continue to next PR.
    4. **Log result:**
       Add to nightly report: "Step 9J: {N} Dependabot PRs checked, {M} merged (patch/minor), {K} skipped (major-version: {maj_count} / CI: {ci_count} / review: {rev_count} / label: {lbl_count})"
```

## Key Change vs Run 108 Winning-Concept

Run 108 defined the merge heuristic as: "CI green + no review request + no blocking labels."
This run adds: **major-version bump detection (step 2a)** as the first filter.

Rationale: 19 open Dependabot PRs include react 18→19 and stripe v11→v15. CI can be green for these (tests may not exercise breaking API changes). Human review is required for major bumps. The original heuristic was correct in spirit but insufficient for the actual PR inventory.

## What This Replaces

- Manual weekly scan of Dependabot PRs by human engineer
- Morning digest items flagging "safe to merge" with zero action (4+ weeks of digest entries)
- Future potential CVE exposure windows from delayed security dep bumps (patch/minor only)

## What This Does NOT Replace

- Major-version bump decisions (still require human review — react 18→19, stripe v11→v15)
- PRs with review requests or blocking labels (still require human action)

## Confidence

HIGH — mandate-triggered (1st carry-forward, governance autonomous-executable), evidence conclusive
(19 PRs aging, 4+ morning digests, channel proven by 5 prior Steps). Major-version safety gate
is conservative and correct. Merge heuristic for patch/minor (CI green + no review request + no
blocking labels + not a major bump) exactly matches what a human would do manually for these.

## What This Closes

Every patch/minor Dependabot PR that passes CI gets merged within 24h of CI going green, indefinitely.
Security patches applied without manual intervention. Major version bumps flagged in nightly log,
require human decision. Estimated 10-15 min/week of manual merge overhead eliminated for safe PRs.
