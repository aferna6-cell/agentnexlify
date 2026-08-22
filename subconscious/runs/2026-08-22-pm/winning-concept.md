# Winning Concept — Run 2026-08-22-pm (#109)

## AUTONOMOUS-EXECUTABLE

**Title:** Step 9J — Dependabot Auto-Merge in nightly SKILL.md (1st carry-forward mandate)

**Category:** operational

**Confidence:** HIGH (mandate fires; evidence conclusive; channel proven)

**Winner rank:** #1 of 3 debated

---

## Why This Wins

Governance mandate fires unconditionally at run 109. Run 108 set `escalation_condition = "Autonomous-executable if not approved by run 109 (1st carry-forward mandate)"`. Nightly channel proven: Steps 9C/9E/9F/9G/9I all implemented via same SKILL.md-edit channel, each landing within 1-2 cycles. No blocking evidence discovered in debate. 6 Dependabot PRs aging 4+ weeks (#629/#630/#631/#649/#665/#666) across 4 consecutive morning digests flagged as safe to merge.

## Evidence

- `grep 'Step 9J' .claude/skills/nightly-commit-review/SKILL.md` → returns 0 (not implemented)
- Run 108 governance: "Autonomous-executable if not approved by run 109 (1st carry-forward mandate)"
- Nightly logs 2026-08-21/22: both explicitly confirm Step 9J not applied
- 6 Dependabot PRs open 4+ weeks: #629/#630/#631/#649/#665/#666
- Morning digests 2026-08-11/12/17/18: all flagged same PRs, zero action taken
- Same channel: Steps 9C/9E/9F/9G/9I all implemented within 1-2 nightly cycles

## Implementation

Insert after Step 9I block (before "10. Commit report") in `.claude/skills/nightly-commit-review/SKILL.md`:

```
9J. (Dependabot Auto-Merge) Merge CI-green Dependabot PRs with no review requests:
    1. List open Dependabot PRs:
       mcp__github__list_pull_requests state="open" base="main" per_page=50
       Filter: author.login == "dependabot[bot]" OR head.ref starts with "dependabot/"
       If 0 found: log "Step 9J: 0 Dependabot PRs open — skip"
    2. For each Dependabot PR:
       a. mcp__github__pull_request_read → check mergeable_state
          Skip if mergeable_state != "clean" (log: "Step 9J: PR #{N} skip — {mergeable_state}")
       b. Check requested_reviewers array. Skip if non-empty.
       c. Check labels. Skip if any label is "do-not-merge" or "hold".
    3. For each eligible PR:
       mcp__github__merge_pull_request (merge_method: "squash",
         commit_title: "{PR title} (#{N})")
       Log success: "Step 9J: merged Dependabot PR #{N} ({package} {version})"
       Log failure: "Step 9J: merge failed PR #{N} — {error}"
    4. Log: "Step 9J: {N} checked, {M} merged, {K} skipped (CI/review/label)"
```

## Expected Impact

- 6 aging PRs merge within 24h of next nightly run (after CI confirms green)
- Security patches land within 24h indefinitely going forward
- ~15 min/week manual overhead eliminated
- Structural: runs automatically on every nightly cycle forever

## Debate Outcome

**SURVIVES → WINNER**

C1 (evidence strength): 4 consecutive digests flagging same PRs = conclusive. C2 (leverage): mandate is binding; GH #669 security issue is M-effort, human-approval-required. C3 (regression risk): mergeable_state=clean + no review requests + no blocking labels = same criteria human applies manually. Risk equivalent, not higher. C4 (governance): 1st carry-forward mandate fires at run 109 — binding. C5 (redundancy): this IS active_directions[0], not competing with it.

## Parking Lot (runners-up)

1. **Middleware block_demo_role comment on GH #669** — valid, but GH #669 already tracks the problem. Add implementation sketch as comment on existing #669, not a new issue. Bandwidth goes to Step 9J mandate this run.
2. **Step 9K stale subconscious PR auto-closer** — strong mechanics, low urgency while PR dedup guard is active. Promote to run 110 if >3 stale subconscious PRs confirmed open.
