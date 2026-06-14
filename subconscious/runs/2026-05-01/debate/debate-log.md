# Debate Log — Run 12 (2026-05-01)

Top 3 ideas debated. Challenge → Defend → Verdict.

---

## Idea 1: JS Silent Catch Guard — Fix AdminAnalyticsPage + Add Check 10 to pre-commit

### Challenge
**C1: Recommendation fatigue.** This is the 5th run recommending JS Silent Catch (runs 3, 9, 10, 11, now 12). If the human hasn't implemented it after 4 explicit moratorium mandates, what changes now?

**C2: Issue #109 covers the AdminAnalyticsPage fix already.** Nightly review opened the issue. Won't the human just fix AdminAnalyticsPage and ignore the pre-commit guard — partial fix again?

**C3: Check numbering error.** Previous winning concepts called this "Check 9" — but pre-commit already has 9 checks (Check 9 = "dropped conversations.messages"). Using wrong check number in a commit will confuse the implementer.

**C4: Moratorium isn't the system's job.** The subconscious is supposed to find improvements, not enforce human workflow. If the human consistently doesn't implement, that's a process problem outside the system's scope.

### Defend
**D1:** Each prior recommendation lacked a critical piece of evidence: the correct check number. Now confirmed — it's Check 10, not Check 9. This implementation sketch will be more precise than all prior versions. Also: Issue #109 creates external accountability (GitHub tracks it). Four previous recommendations = four times where the path was unclear or seemed deferrable. The guard is now the clearest path to lifting the moratorium.

**D2:** Issue #109 covers the symptom (AdminAnalyticsPage). The pre-commit guard prevents the next occurrence. The cycle is: fix manually → new violation appears → fix again. `e68677a` fixed Marketing+LocalSEO violations. 90ba1c5 introduced 0 new violations but AdminAnalyticsPage already had 6. Without the guard, every new file the Onboarding V2 sprint adds is a risk vector. Partial fix is exactly what has happened 3 times. The recommendation must keep bundling both.

**D3:** Confirmed. Check 10 is the correct designation. Previous concepts said "Check 9" — this run corrects the error. The implementation sketch below uses the right number.

**D4:** The subconscious is ALSO the system's memory. Persistent re-recommendation with escalating specificity is the designed behavior under moratorium. The pattern stops when: (a) implemented, (b) explicitly rejected with reason, or (c) frozen (≥3 rejections). None of those apply. Continue.

### Verdict: SURVIVES — winner

Additional supporting evidence not in prior runs:
- Issue #109 externally tracked (nightly review agent agrees this is real)
- Onboarding V2 sprint (21 issues) starting NOW — most risk window for spreading pattern
- Check number corrected (Check 10, not 9) — removes implementation confusion
- em-dash blocker for run 8 confirmed still present — JS Silent Catch is the ONLY unblocked S-effort pre-commit item

---

## Idea 2: Scope em-dash check + Wire check_project_invariants.py (Run 8 Unblocking)

### Challenge
**C1: This is still blocked.** Em-dash violations confirmed on 9 instances across 2 files. Nightly review said "stale note" but direct execution of `check_project_invariants.py` proves violations still exist. The blocker from runs 10 + 11 is not cleared — it's expanded (AutomationActivityCard now adds 5 violations).

**C2: The em-dash check may be wrong by design.** If JSX UI uses "—" as a display character (e.g., `|| "—"` for empty hours in a table), the check_project_invariants.py check is a false positive. Fixing the UI files would be wrong — you'd lose legitimate empty-state rendering. The correct fix is scoping the check to content/copy files only, not ALL HTML/JSX.

**C3: Two-step task.** Can't wire the script until em-dash check is scoped. This isn't "S-effort" — it's S-effort for scoping + S-effort for wiring = M-effort total.

### Defend
**D1:** Confirmed, blocker still present. The nightly review agent was incorrect. This is the first run with direct verification via `python3 check_project_invariants.py`. The fix path is: scope the check (not fix JSX files), then wire. Correct diagnosis makes implementation tractable.

**D2:** Agreed — scoping the em-dash check to exclude `.jsx` rendering contexts is the right path. The check was written for content copy discipline (enforce em-dash over en-dash in marketing text). JSX `|| "—"` is a render character, not copy. Update the check to: `if not f.endswith('.jsx') and not f.endswith('.tsx')`.

**D3:** Acknowledged. M-effort. This is why JS Silent Catch (S-effort, no blockers) wins this run. Scope the em-dash check + wire is the correct next candidate AFTER moratorium lifts — but it requires the scoping pre-step and is therefore not the cleanest next recommendation.

### Verdict: WEAKENED — correct diagnosis, wrong timing. Two-step task with investigation overhead. JS Silent Catch wins on parsimony. Recommend em-dash scoping as implementation prerequisite note, promote as run 13 winner if moratorium lifts after run 12 is implemented.

---

## Idea 3: Wire Golden Eval Harness to CI (Issue #110)

### Challenge
**C1: Requires a GH Secret.** `LEAD_QUALIFIER_AGENT_ID` must be provisioned in GitHub Secrets before the workflow runs correctly. If the secret is missing, CI job fails on import (not gracefully). Who provisions it?

**C2: Moratorium overrides parking lot.** governance.json explicitly notes "PROMOTE AS RUN 12 WINNER once moratorium lifts." Moratorium hasn't lifted. Wrong timing.

**C3: ROI is high but risk is also non-trivial.** The eval harness calls real Claude API (claude-haiku-4-5-20251001 based on test file). Weekly CI costs are real. At $0.0008/call × 25 cases = $0.02/run, but if the agent_id is wrong or not provisioned the CI just fails silently.

### Defend
**D1:** Issue #110 is open. The provisional path: add `if: env.LEAD_QUALIFIER_AGENT_ID != ''` condition to the workflow so the job gracefully skips if the secret is missing (not fails). Provisionining is a one-time admin action that can be documented in the workflow file comments.

**D2:** Moratorium protocol acknowledged. governance.json correctly designates this as the first post-moratorium winner. Arguing against protocol is arguing for chaos. Wait.

**D3:** $0.02/run weekly = ~$1/year. Non-issue. Haiku 4.5 is the cheapest tier. Real risk is false negatives from a stale golden set, not cost.

### Verdict: KILLED — moratorium protocol forbids parking lot items while pending approvals > 3. Correct candidate for run 13 (post-moratorium). Parking lot note already in governance.

---

## Summary

| Idea | Verdict | Notes |
|------|---------|-------|
| JS Silent Catch Guard (run 3) | **SURVIVES → winner** | Check 10 (corrected), Issue #109 open, sprint timing |
| Scope em-dash + Wire invariants.py (run 8) | **WEAKENED → parking lot** | Two-step M-effort; em-dash scope fix is prerequisite |
| Wire golden eval harness (parking lot) | **KILLED** | Moratorium forbids parking lot; run 13 candidate |
