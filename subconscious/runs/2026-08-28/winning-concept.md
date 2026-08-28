# Winning Concept — Run 110 (2026-08-28)

## Winner: Fix Step 9J — Add `@dependabot rebase` trigger for `mergeable_state: unknown` PRs

**Category:** workflow
**Effort:** S
**Confidence:** HIGH
**Status:** RECOMMENDATION — autonomous-executable on 1st carry-forward (run 111 mandate)
**Source run:** 110
**Compounds:** run 109 (Step 9J added — now needs rebase trigger to activate it)

---

## Why This, Why Now

Run 109 added Step 9J (Dependabot auto-merge) — an immediate improvement. But the first nightly execution (2026-08-28) got 0 merges because all 20+ Dependabot PRs returned `mergeable_state: unknown`. This is GitHub's documented behavior for PRs whose base has diverged and mergeability hasn't been recomputed — they never reach `clean` without a rebase trigger. The fix is 10-15 lines in the same SKILL.md block. Without it, Step 9J is permanently at 0% effectiveness. CVE window stays at 2-3 weeks.

The nightly log itself recommended the fix: "Next actions: Trigger rebase via @dependabot comment." Evidence, root cause, and fix are all confirmed in the same nightly run that revealed the problem. S-effort, same autonomous-executable channel used by Steps 9C/9F/9G/9I/9J.

---

## Implementation Sketch

Edit the Step 9J block in `.claude/skills/nightly-commit-review/SKILL.md`:

After checking `mergeable_state != "clean" → skip`, add:

```
   b2. If mergeable_state == "unknown":
       - List comments on PR via mcp__github__list_issue_comments
       - Check if any comment body contains "@dependabot rebase" AND was created within 48h
       - If already posted within 48h: skip (dedup guard)
       - If not posted (or older than 48h): post "@dependabot rebase" via mcp__github__add_issue_comment
       - Log: "Step 9J: triggered rebase on PR #{N} (state: unknown)"
       - Increment rebase_trigger_count
       - If rebase_trigger_count >= 5: stop triggering rebases for this run (cap)
       - Skip to next PR (this PR not eligible for merge this run; will be clean after rebase + CI)
```

Updated Step 9J log line:
```
Step 9J: {N} checked, {M} merged, {K} skipped (CI/review/label), {R} rebase-triggered (unknown state)
```

**Dedup guard:** prevents rebase spam on 20+ PRs simultaneously.
**Cap of 5:** prevents GitHub notification flood in a single nightly run.
**Loop safety:** rebased PRs → CI runs → next nightly sees `clean` → merges. No circular behavior (failed CI → `dirty`/`behind`, not `unknown`).

---

## What This Replaces

Step 9J as implemented in run 109 had a silent failure mode: all 20+ Dependabot PRs were in `unknown` state, so 0 merges happened and would continue to happen indefinitely. This adds the rebase trigger that activates the already-written merge logic.

---

## Run 111 Mandate

1. Verify rebase trigger fires in nightly post-2026-08-28: `grep 'triggered rebase on PR' ops/routines/logs/nightly-commit-review-*.md`
2. Count: how many rebases triggered? (cap at 5)
3. Did any Dependabot PRs become `clean` + merge within 24-48h of trigger?
4. Final Step 9J log line format: `N checked, M merged, K skipped, R rebase-triggered`
5. GH #669: still open? Any middleware PR from issue-to-pr-loop?
6. GH #643 (21d) + GH #660 (13d): still stalled? Any linked PRs?
7. Brain connector GH #684: SUPABASE_ACCESS_TOKEN set in Railway?

---

## Impact (Compounding Run 109)

- Step 9J goes from 0% → ~80% effectiveness within 24-48h of next nightly
- 20+ Dependabot security dep bumps unblocked; CVE window 2-3 weeks → <48h
- Zero additional human effort once deployed
- Compounds permanently: new Dependabot PRs with unknown state get rebase triggers automatically
