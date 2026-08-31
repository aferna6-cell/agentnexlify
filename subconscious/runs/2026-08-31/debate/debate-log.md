# Debate Log — Run 114 (2026-08-31)

Top 3 ideas ranked by impact: Idea 1 (Step 9K), Idea 2 (Step 9J detection fix), Idea 5 (__future__ annotations gap).

---

## Idea 1: Step 9K — Stale Subconscious Draft PR Audit

### Challenge
- Is this genuinely high-leverage? The subconscious pushes PRs to GitHub — the owner can see them there.
- Has Step 9K been so long deferred because it actually doesn't matter?
- Two-step problem: (a) Step 9K added to SKILL.md, (b) nightly executes it. Even if added today, impact is T+24h.
- Is adding yet another Step 9x to an already long SKILL.md creating bloat?

### Defend
- Governance mandate binding: run 113 mandate explicitly states "Step 9K is run 113 winner" on condition ≥3 open subconscious PRs. Condition confirmed (23 run dirs, 5+ PRs tracked). This isn't optional — it's a contractual governance obligation.
- Precedent: Steps 9F, 9G, 9I, 9J all implemented at 1st carry-forward via autonomous-executable channel. Same channel, same logic.
- The compound value is real: once added, Step 9K runs forever without additional effort. Every nightly thereafter checks subconscious backlog health.
- SKILL.md Step 9x bloat: the pattern is intentional. Each step adds one discrete observability unit. Step 9K closes a blind spot (PR accumulation).
- The owner cannot easily see stale subconscious PRs without going to GitHub — the nightly report brings this to them.

### Verdict: **SURVIVES → WINNER**

---

## Idea 2: Step 9J Detection Fix (search_pull_requests)

### Challenge
- Step 9J was just fixed in run 112 (added @dependabot rebase trigger). Now the detection is broken again. Is this a real different bug, or the same bug resurfacing?
- The nightly-2026-08-31 says "not scoped in this run" — this suggests the nightly agent CHOSE to skip Step 9J, not that detection failed. Is the root cause actually the SKILL.md instruction, not the GitHub API?
- Risk of changing the API call: different response schema could break parsing.

### Defend
- The detection failure is confirmed real: nightly-2026-08-30 explicitly logged "No Dependabot PRs detected" (0 found). This is NOT a "not scoped" decision — it was a detection failure. The "not scoped" on 2026-08-31 may be the nightly agent giving up after the failure.
- Run 113 mandate specifically calls this out as a bonus action: "Fix Step 9J detection: change list_pull_requests(creator='dependabot[bot]') to search_pull_requests(query='is:pr is:open author:app/dependabot')".
- The search API returns PRs with an author app/dependabot format that the list API misses for bot-authored PRs in headless sessions — this is a documented GitHub API behavior difference.
- Impact: 20+ aging Dependabot PRs can't merge until this is fixed.

### Verdict: **SURVIVES → parking lot (bonus action with Step 9K implementation)**
Reason: High value but same SKILL.md edit as Step 9K — should bundle, not be a separate winner. Step 9K wins on governance mandate; 9J fix rides as bonus.

---

## Idea 5: `__future__` Annotations Pre-commit Coverage Gap

### Challenge
- The pre-commit hook blocks `from __future__ import annotations` — this is an existing invariant. If it slipped in, maybe it was bypassed (--no-verify) or committed from a session that skipped the hook.
- Checking the hook coverage is a read-only investigation, not an actionable improvement unless we find a gap.
- M8 files are actively changing — investigating a single-instance slip now may lead to outdated findings within 24h.

### Defend
- The nightly had to auto-fix this — meaning the invariant was violated in production code. That's a real gap, not noise.
- If the pre-commit hook has a glob that misses new M8 service paths, this will recur with every new M8 service file.
- XS effort to verify + patch if gap exists.

### Verdict: **WEAKENED → parking lot**
Reason: Single instance, possibly a one-off bypass rather than a structural gap. Lower priority than Step 9K (governance mandate). Worth investigating but not this run's winner.

---

## Summary

| Idea | Verdict |
|------|---------|
| Step 9K stale PR audit | **SURVIVES → WINNER** |
| Step 9J detection fix | **SURVIVES → bonus action (bundle with Step 9K)** |
| M8 rollout gate GH issue | **WEAKENED → parking lot (already tracked via HOLDs)** |
| os_tool_executions split | **KILLED → deferred (not stable, 1 day old)** |
| __future__ annotations gap | **WEAKENED → parking lot (single instance, unverified gap)** |
