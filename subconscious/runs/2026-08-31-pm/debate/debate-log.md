# Debate Log — Run 114 (2026-08-31-pm)

Top 3 ideas ranked by impact: Idea 1 (Step 9K), Idea 2 (M8 Invariant Scan), Idea 3 (Step 9J Detection Fix).

---

## Idea 1: Step 9K — Stale Subconscious Draft PR Audit

### Challenge
- Is the evidence strong enough? Just counting run directories isn't proof open PRs are actually stale.
- Is this the highest-leverage action? Other ideas directly touch M8 (active $-sprint) or fix a broken automation step.
- Has this been tried before? If subconscious PRs keep accumulating, adding a nightly alert might not change behavior.
- Is it too similar to active direction? It IS the active direction — run 113 winner.

### Defend
- Evidence is strong: governance.json explicitly tracked 5+ open subconscious draft PRs since run 102 (runs 110, 111, 112 all show open PRs in mandate tracking). 23 run directories exist. The mandate condition is binary and confirmed.
- Highest-leverage for automation: Step 9K is autonomous-executable in the same SKILL.md channel that successfully implemented Steps 9C/9E/9F/9G/9I/9J. All 6 landed in 1-2 cycles. Nightly will execute it automatically on next firing.
- "Alert might not change behavior" is weak: Step 9K escalates to PR comment after 5 stale PRs or 1 critical (>60d). That's not just logging — it's active escalation to the PR author. Same mechanism as Step 9C brain-connector age gate (which immediately triggered human action on GH #684).
- Same active direction: governance mandate explicitly says "autonomous_executable_run_114_if_not_approved." This IS the run 114 mandate.

### Verdict: **SURVIVES → WINNER**
Governance mandate binding. Same autonomous-executable SKILL.md channel. High evidence. Implementation is atomic. Bonus: Step 9J detection fix rolls into same commit.

---

## Idea 2: M8 Invariant Scan in Deploy Checklist

### Challenge
- Is the evidence strong enough? One nightly fix (c159976) for one file is a thin sample. Could be a one-time oversight.
- Is this the highest-leverage action? Pre-commit already guards `__future__ annotations`. Adding it to a doc checklist is redundant.
- What could go wrong? A doc-only checklist is advisory, not enforced. The real gate (pre-commit) already exists.
- Has something similar been rejected? Yes — run 8 wired check_project_invariants.py to pre-commit (enforcement); run 40 fixed the autonomous channel for SKILL.md creation. The established pattern is to put enforcement in code/hooks, not docs.

### Defend
- Single data point c159976 is genuine. M8 sprint is generating new files fast and at least one bypassed pre-commit.
- A doc checklist reminder has value when humans are running deploy scripts manually in a fast sprint.
- The real root cause should be investigated: did pre-commit fail to run? Was it committed directly? A doc-only checklist doesn't address root cause.

### Verdict: **WEAKENED → Parking Lot**
Pre-commit already has this guard. If violations are reaching main, the root cause is that pre-commit isn't being run (or the commit was direct). A doc checklist addition doesn't fix that. Lower leverage than enforcement-level fix. Defer to run 115 if pattern repeats.

---

## Idea 3: Step 9J Detection Fix

### Challenge
- Is this the highest-leverage standalone winner? It's already planned as Bonus Action #1 in the run 113 winning-concept.md. Proposing it as winner would be redundant.
- Is it in frozen/rejected paths? No, but it was already triaged as a bonus.
- What could go wrong? search_pull_requests might have rate limits or pagination differences vs list_pull_requests. Need to verify the query syntax is correct for GitHub API.

### Defend
- search_pull_requests with "is:pr is:open author:app/dependabot" is standard GitHub search API syntax.
- The fix is 1 line change and is being implemented in the same SKILL.md commit as Step 9K anyway.
- The root cause of Step 9J 0% effectiveness is now the detection failure, not the unknown-state logic.

### Verdict: **WEAKENED → Bonus Action**
Correct and needed. But already planned as bonus with Step 9K. Not high enough standalone leverage to displace the governance mandate winner. Implemented as bonus in same commit.

---

## Summary

| Idea | Verdict | Outcome |
|------|---------|---------|
| Step 9K — nightly PR audit | SURVIVES | Winner |
| M8 invariant scan in doc checklist | WEAKENED | Parking lot |
| Step 9J detection fix | WEAKENED | Bonus action (same commit) |
| os_tool_executions.py split | Not debated | Deferred (not stable) |
| M8 OAuth blocker doc | Not debated | Deferred (lower priority) |
