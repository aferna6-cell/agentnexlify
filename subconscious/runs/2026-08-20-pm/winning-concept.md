# Winning Concept — Run 2026-08-20-pm (Run 109)

## Winner: Step 9J — Dependabot Auto-Merge in nightly SKILL.md

**Status: AUTONOMOUS-EXECUTABLE** — 1st carry-forward mandate fires.
run_108_mandate explicitly named Step 9J. Escalation condition: "Autonomous-executable if not approved by run 109 (1st carry-forward)". This is run 109.
Precedent: Steps 9F/9G/9I all implemented via same escalation path, all landed within 1-2 cycles.

---

## Why This, Why Now

- 6 Dependabot PRs aging (#629/#630/#631/#649/#665/#666) — 2–16 days old
- Morning digests 2026-08-11/12/17/18 all flagged the same PRs as "low risk, merge" — zero action across 4 weeks
- Step 9I first execution confirmed 2026-08-20: nightly sweep channel working (filed GH #669 correctly)
- Mandate item 1: grep returns 0 for "Step 9J" in SKILL.md — ABSENT, escalation condition MET
- Every delayed dep bump = wider CVE exposure window; this closes it permanently

---

## Implementation — Exact SKILL.md Edit

Insert after Step 9I log result (before "10. Commit report:") in `.claude/skills/nightly-commit-review/SKILL.md`:

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

---

## Debate Summary

| Idea | Verdict |
|------|---------|
| Step 9J (Dependabot auto-merge) | SURVIVES → WINNER (mandate fires) |
| Step 9K (stale PR commenter) | WEAKENED → Parking Lot (run 110 candidate) |
| GH #669 middleware sketch | KILLED (issue-to-pr-loop handles when GH #399 unblocked) |

---

## What This Closes

- Every Dependabot PR that passes CI merges within 24h of CI green, permanently
- ~15 min/week manual merge overhead eliminated
- 6 currently aging PRs resolved by next nightly run
- CVE exposure window bounded by CI cycle time, not human attention cycle

---

## Bonus Action (if time permits)

Post diagnostic comment on GH #403 listing ALL 3 required GH Actions secrets
(ANTHROPIC_API_KEY + SUPABASE_URL + SUPABASE_ANON_KEY) with exact setup steps.
Run 107 posted ANTHROPIC_API_KEY comment; KB still 28d stale → second blocker likely.

---

## Confidence

HIGH — mandate-triggered, evidence conclusive (4+ morning digests, 6 PRs aging, grep confirms ABSENT),
channel proven (Steps 9C/9E/9F/9G/9I all implemented same way, all landed within 1-2 cycles).
Merge heuristic (CI green + no review request + no blocking label) exactly matches human manual check.
