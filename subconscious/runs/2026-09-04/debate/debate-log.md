# Debate Log — Run 115 (2026-09-04)

## Contestants
- **Idea 1:** Fix Step 9J — implement merge eligibility loop (cap 10/run)
- **Idea 3:** Direct fix for GH #787 — website_connect.py block_demo_role
- **Idea 5:** M9 planner bakeoff offline quality gate in CI

---

## Round 1: Idea 1 — Fix Step 9J merge eligibility

### Objections

**O1:** Step 9J already posts `@dependabot rebase` for `unknown` state. Maybe the PRs are `unknown` and that's the real blocker — implementing the merge loop won't help if all 19 stay `unknown` indefinitely.

**O2:** Squash-merging 10 Dependabot PRs in one nightly run could trigger merge conflicts with each other if multiple PRs touch the same lockfile. The next PR in the batch would have a stale base.

**O3:** Step 9J is a SKILL.md edit — unreviewed edits to nightly automation that auto-merges dependency PRs carry real blast radius if a bad version slips through.

**O4:** The rate concern logged by nightly was "requires mergeable_state per-PR read" — this implies 19 additional API calls. Won't this hit GitHub API secondary rate limits?

### Defense

**D1:** The `@dependabot rebase` comment is posted when `mergeable_state=unknown`. Dependabot processes rebases within minutes. On the NEXT nightly run, those PRs would be `clean`. If the merge loop existed, they'd merge. But there's no merge loop — the skill ends at detection. So the rebase posts never pay off because no merge ever fires. The fix specifically checks `mergeable_state=clean` to merge only PRs that are already ready.

**D2:** Cap-10 means max 10 merges per run. Dependabot auto-rebases PRs that conflict after a prior merge in the same group — it handles lockfile conflicts by design. The cap-10 + per-PR check means we never blindly batch-merge; each one passes `mergeable_state=clean` individually before merging.

**D3:** GitHub primary rate limit is 5,000 req/hr for authenticated apps. 19 API calls is 0.38% of the hourly budget. Secondary rate limits require >100 concurrent requests. 19 sequential calls is well within bounds. The "rate concern" in the nightly log is a false explanation for unimplemented logic.

**D4:** The blast radius concern is real but bounded. Dependabot PRs from GitHub are dependency bumps where CI must be green for `mergeable_state=clean`. If CI catches a regression, the PR won't be `clean` and won't merge. The skip-on-blocking-labels guard adds another layer. Risk is LOW.

### Verdict: **SURVIVES → WINNER**
Evidence is strong, objections answered. 19 PRs aging for 15 days. Detection works. Merge loop is provably absent (SKILL.md ends without merge call). Highest leverage unblocked improvement this run.

---

## Round 2: Idea 3 — Direct fix GH #787 block_demo_role

### Objections

**O1:** This was classified MEDIUM risk by the nightly auto-fix gate — that gate exists for good reason. Overriding MEDIUM risk classification to auto-apply is unsafe process precedent.

**O2:** GH #787 already exists and is labeled `ai-ready`. The issue-to-pr-loop skill polls `ai-ready` issues. This fix will be picked up when the loop is unblocked. No subconscious action needed.

**O3:** The fix is 2 lines — too narrow to be a subconscious winner. Subconscious winners should have "permanent compounding value."

**O4:** website_connect.py is part of Website Connect v1 (PR #772, 2535 lines added). The full PR may still be in review. Merging a partial fix to a half-reviewed feature could confuse reviewers.

### Defense

**D1:** MEDIUM risk classification is correct — it requires a human decision, not auto-apply. Subconscious doesn't auto-apply; it recommends. The recommendation is legitimate. But the issue-to-pr-loop gate and GH #787 already exist as the correct execution path.

**D2–D4 together:** Conceded. GH #787 is already filed, labeled `ai-ready`, and waiting for the issue-to-pr-loop. The fix is being tracked. Repeating it as a subconscious winner would make two competing fix paths for the same 2-line change. This wastes governance momentum on something already in the queue.

### Verdict: **WEAKENED → Bonus action, not winner**
Legitimate security fix, but already tracked. Issue-to-pr-loop is the correct execution path. Subconscious winner should be structural. Demoted to run-116 bonus monitor.

---

## Round 3: Idea 5 — M9 planner bakeoff CI gate

### Objections

**O1:** The bakeoff system had 5 commits in 3 days immediately before this run. Adding a CI gate to an unstable system creates a flaky gate that fails for reasons unrelated to planner quality. Teams learn to dismiss flaky CI.

**O2:** `plan_eval.py` currently has 44 tests — but how many cover the FULL action space M9 targets? A 90% pass threshold on 44 tests could be achieved by a regression that drops 4 tests covering edge cases that are the whole reason the gate exists.

**O3:** The offline evaluator is deterministic — but against what reference? If the bakeoff uses recorded conversation replays, the replays become stale as the action space grows. Gate could green on replays while production degrades.

**O4:** CI gate failures block ALL PRs touching `backend/services/os_workflows/` — including hotfixes. A false-positive on a hotfix is a production incident risk.

### Defense

**D1:** Velocity argument conceded. 5 commits in 3 days = system is still being calibrated. Adding a hard gate now would require tuning the threshold alongside feature work, creating a secondary debugging surface.

**D2–D4:** The evaluation design questions are real gaps: what's the threshold evidence? How large is the evaluated action space vs total? Replay staleness is a known eval problem. These design gaps mean implementing a gate now creates a false-confidence signal rather than a real regression detector.

### Verdict: **WEAKENED → Parking lot**
Correct direction for the future, premature for this run. Revisit after M9 bakeoff velocity settles (<2 commits/week for 2 weeks).

---

## Final Rankings

| Rank | Idea | Verdict |
|------|------|---------|
| 1 | Step 9J merge eligibility loop | WINNER |
| 2 | GH #787 block_demo_role fix | Bonus monitor |
| 3 | M9 CI gate | Parking lot |

**Winner: Idea 1 — Fix Step 9J**
