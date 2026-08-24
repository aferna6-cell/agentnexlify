# Run 110 — Winning Concept (2026-08-24-pm)

## Winner: Add major-version safety gate to Step 9J

**Category:** code_health
**Effort:** XS (~12 lines in SKILL.md)
**Autonomous-executable:** YES — proven nightly SKILL.md channel
**Urgency:** CRITICAL — Step 9J fires for first time 2026-08-25 02:37 AM

## Problem statement

PR #674 (merged 2026-08-24) claimed to include a major-version safety gate in Step 9J. The PR description reads: "Skips major-version bumps (react 18→19, stripe v11→v15, actions/checkout 4→7, etc.) — requires human review... Step 2a (major-version detection via title parse) blocks those."

Direct read of `.claude/skills/nightly-commit-review/SKILL.md` lines 392-411 shows no such check. Step 2 has exactly three sub-checks:
- (a) CI status (mergeable_state)
- (b) Review requests (requested_reviewers)
- (c) Blocking labels (do-not-merge / hold)

No step (d) for version parsing. No regex. No major-version comparison.

Memory line 108 (run 109 second entry) incorrectly states "major-version safety gate from prior iterations confirmed." This is false. The entry trusted the PR description without verifying the SKILL.md content.

## Impact if not fixed

Step 9J fires tomorrow (2026-08-25 at 02:37 AM). Currently open major-version Dependabot PRs that would pass all three existing checks:
- #586, #591, #593 — react 18→19 (3 PRs, CI green, no review requests, no blocking labels)
- #598 — stripe v11→v15 (CI green, no review requests, no blocking labels)

React 19 has breaking changes (new JSX transform, concurrent features, deprecated APIs removed). Stripe v11→v15 spans 4 major versions. Both require deliberate migration, not automatic merge.

## Exact edit

File: `.claude/skills/nightly-commit-review/SKILL.md`

**After line 403** (the blocking-labels check), insert new sub-check 2d before the "Merge eligible PRs" block:

```
       d. Major-version bump: from PR `title`, extract version pattern.
          Dependabot titles follow: "Bump {package} from {old} to {new}" or "build(deps): bump {package} from {old} to {new}".
          Split title on " to " → last token = new_version_str. Split new_version_str on first non-digit/dot char, take first segment.
          Split title on " from " → second token before " to " = old_version_str. Same trim.
          Extract major: integer before first dot (or whole token if no dot). Use string comparison on digit prefix: int(old_version_str.split(".")[0]) vs int(new_version_str.split(".")[0]).
          If new_major > old_major:
          log "Step 9J: PR #{N} — major-version bump ({old_version_str}→{new_version_str}) — SKIP (human review required)" and skip.
          If title does not match pattern (no " from " or no " to "): log "Step 9J: PR #{N} — title unparseable — SKIP (manual review)" and skip.
```

**Line 411** (step 4 log): update skip reason list from "(CI/review/label)" to "(CI/review/label/major-version/unparseable)".

## Implementation

This run implements the edit directly (autonomous-executable per nightly SKILL.md channel authorization).

The SKILL.md edit adds only prose instructions. No code files touched. No tests needed. Reversible: revert SKILL.md text if nightly misparses a title.

## Mandate for run 111

1. Verify Step 9J fired in nightly-commit-review-2026-08-25 log
2. Count: how many PRs checked, merged, skipped (CI/review/label), skipped (major-version)?
3. Verify react 18→19 PRs (#586/#591/#593) logged as "major-version bump — SKIP"
4. Verify stripe v11→v15 (#598) logged as "major-version bump — SKIP"
5. GH #669: is block_demo_role middleware PR (#653) merged?
6. GH #399: AUTOPILOT_GH_TOKEN still expired?
7. Step 9K if ≥3 open subconscious PRs remain
8. Step 9L substrate health monitor if ops/routines/logs/ baseline established (2+ days data)
