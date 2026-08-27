# Debate Log — Run 114 (2026-08-27)

## Setup

5 candidate ideas scored. Top 3 advanced to full debate. Ideas 3 and 4 (file GH issue for agent_escalation.py + Step 9D enhancement) eliminated in pre-debate triage: Idea 3 is a one-off reaction to a single file (deferred to backlog), Idea 4 is workflow noise given GH #399 still blocks the loop (zero leverage until AUTOPILOT_GH_TOKEN rotates).

Top 3:
- **Idea 1**: Fix Step 9J — Handle `mergeable_state: unknown`
- **Idea 2**: Step 9K — Stale Autonomy PR Closer (Report-Only)
- **Idea 5**: Step 9L — Dead Service Detector (nightly)

---

## Round 1: Initial Positions

### Idea 1 — Fix Step 9J
**FOR:** Step 9J fired for the first time 2026-08-27 nightly. 3 PRs checked, 0 merged. All returned `mergeable_state: unknown`. This is documented GitHub behavior — mergeability isn't computed until GitHub resolves a stale-base PR. The current SKILL.md block requires `"clean"` and skips all others. Result: 19+ Dependabot PRs continue aging (oldest 2026-07-27, 31 days). The mandate from run 109 was "verify Step 9J fired" — it fired, but delivered zero value. This is a bug in the Step 9J implementation, not a new idea. Fix is surgical: add `unknown` → branch-update → re-read → attempt-merge logic (~8 lines). Effort: XS-S. Autonomous-executable: YES (same class as Step 9J which was a SKILL.md edit).

**AGAINST:** Could this cause spurious merge attempts? If a PR is `unknown` for a reason other than stale base (e.g., merge conflict), forcing it through could fail loudly. But Step 9J already calls `mcp__github__merge_pull_request` which returns 405/422 on conflict — graceful error handling already in design. Risk is low; the fix adds handling, not recklessness.

**VERDICT:** STRONG. Core mandate execution. Zero ambiguity.

### Idea 2 — Step 9K (Stale Autonomy PR Closer, Report-Only)
**FOR:** Condition from run_109_mandate explicitly met: 6 open subconscious PRs (#683, #653, #626, #613, #611, #606). Condition was "≥3 open". Named mandate from run 109. The oldest (#606) is from 2026-07-28, 30 days. No-auto-close variant is report-only + comment on oldest if >21d. Effort: XS. Zero production risk. Addresses structural PR debt accumulation.

**AGAINST:** Adding another SKILL.md step increases nightly execution time. But Step 9K is report-only — list PRs, count, comment on one. Negligible overhead. Legitimate concern: is commenting on stale draft PRs actually useful if no human is watching? Counter: the comment goes on the PR where the human WILL see it if they ever look. Notification mechanism works.

**VERDICT:** APPROVED as Bonus A. Mandate condition met, effort minimal, no production risk.

### Idea 5 — Step 9L (Dead Service Detector)
**FOR:** agent_escalation.py is the 2nd service file with tests and 0 router callers (prev: appointment_completion.py ~3 weeks). Systematic detection via nightly grep catches this class of gap before it becomes dead code or a 3-week confusion source. Low-effort SKILL.md addition, report-only (file GH issue only).

**AGAINST:** Adding Step 9L to SKILL.md creates noise if the detector has false positives. "0 import references in backend/routers/" grep must exclude cron-triggered services, helpers, utils, bases, __init__.py, test files. Pattern is workable but requires careful exclusion list. More importantly: the exclusion list is brittle — future legitimate services may be incorrectly flagged. Better to validate the grep pattern first before committing it to nightly.

**VERDICT:** WEAKENED. Parking lot. Promote in run 111 if agent_escalation.py still unwired (proving the problem recurs) AND the grep exclusion pattern is validated.

---

## Round 2: Cross-Examination

### Idea 1 vs Idea 2 (priority ordering)

Can both be implemented this run? YES. Idea 1 edits the Step 9J block in SKILL.md. Idea 2 adds a new Step 9K block after Step 9J. No conflict. Idea 1 goes first (core mandate fix), Idea 2 goes second (bonus mandate).

### Idea 1 technical review

Implementation path per ideas.md §Idea 1:
```
When mergeable_state == "unknown":
  → call mcp__github__update_pull_request_branch (triggers GitHub recompute)
  → re-read PR via mcp__github__pull_request_read
  → if still "unknown": attempt merge anyway via mcp__github__merge_pull_request
  → handle 405/422 gracefully (log + continue)
```

Does this introduce risk? Updating the branch on a Dependabot PR causes GitHub to re-run CI. If CI was already passing (which it was — the Dependabot auto-merge Idea assumes CI-green as a precondition), this is safe. The branch update just rebases/merges base into the PR branch, making GitHub recompute mergeability. Then if still `unknown` (rare — usually resolves), we attempt and handle failure.

One edge case: what if `update_pull_request_branch` fails because the PR is already up to date? GitHub returns 422 "pull request head sha is up to date" — treat as no-op, proceed with merge attempt anyway.

**REVISED IMPLEMENTATION:**
```
a. If mergeable_state == "unknown":
   i.  Call update_pull_request_branch. On 422 (already up to date): skip update step.
   ii. Re-read PR. If now "clean": proceed to merge. If still "unknown": attempt merge anyway.
   iii. Handle merge 405/422 gracefully.
b. Log: "Step 9J: {N} checked, {M} merged, {K} skipped-CI, {L} skipped-unknown-recheck"
```

**VERDICT:** Sound. No additional risk beyond what Step 9J already accepts.

---

## Round 3: Final Positions

| Idea | Verdict | Role |
|------|---------|------|
| Idea 1: Fix Step 9J (unknown state) | **WINNER** | Core implementation |
| Idea 2: Step 9K (stale PR closer) | **BONUS A** | Mandate condition met |
| Idea 5: Step 9L (dead service detector) | PARKING LOT | Run 111 candidate |

---

## Governance Check

- **Autonomous-executable?** YES — both Idea 1 and Idea 2 are SKILL.md edits, same class as Steps 9C/9E/9F/9G/9I/9J. No production code changes. No schema changes.
- **Moratorium status?** INACTIVE. No new human-approval pending items added this run.
- **Carry-forward?** Idea 1 is a bug fix on Step 9J (not a new carry-forward chain). Step 9K is 1st implementation of the run_109_mandate. Both proceed.
- **PR dedup:** PR #683 exists (created 2026-08-24, title "subconscious: runs #110-111"). Commits go to that branch. No new PR needed.
