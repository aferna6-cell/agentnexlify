# Debate Log — 2026-04-28-pm

Top 3 by impact: Idea 1 (Check 9 guard), Idea 2 (wire check_project_invariants), Idea 3 (widget sync guard).

---

## Idea 1: Add pre-commit Check 9 — JS Silent Catch Guard

### Round 1 Challenge
> The violations were just fixed in e68677a. The patient is healed. Why install a guard when the wound is closed?

**Defend:** Because e68677a is a cure, not a vaccine. The same 3 violations existed undiscovered for 14+ days. The subconscious caught them via evidence gathering — not the commit flow. Without a guard, any developer (or Claude Code on autopilot) can write `.catch(() => null)` in the next feature branch and it'll merge silently. The pre-commit hook's entire purpose is to catch repeat-offender patterns (Check 6: bare Python excepts, Check 8: dropped conversations.messages column). This is the same category of rule.

### Round 2 Challenge
> False positives. Some legitimate async patterns use empty catches — event listeners that intentionally swallow, cleanup handlers, fire-and-forget. Blocking those hurts developer velocity.

**Defend:** Legitimate empty catches are rare in a frontend React/FastAPI app. The guard blocks `.catch(() => null)` and `.catch(() => {})` specifically — both imply discarded errors with zero signal. Any genuinely justified case should have at minimum `console.warn(...)`. If a developer needs an empty catch for a real reason, `git commit --no-verify` is the escape hatch (same as all other checks). The pre-commit hook already has this escape valve documented.

### Round 3 Challenge
> This is the same thing as the current Check 6 (Python bare-except). Aren't we duplicating effort? And Check 6 was for Python, not JS — does the hook even have JS infrastructure?

**Defend:** Not duplication — extension. Check 6 guards Python bare excepts; Check 9 guards JS silent catches. Different language, same class of error. The hook already greps staged files by extension for Python (`*.py`) — the same pattern works for JS/JSX/TS/TSX. Infrastructure exists. The only new code is the regex pattern and the JS extension filter. ~8 lines total.

**Verdict: SURVIVES.** All three challenges answered. Evidence strong (14-day undiscovered violations, existing hook pattern, S-effort). No significant objection stands.

---

## Idea 2: Wire scripts/check_project_invariants.py into pre-commit

### Round 1 Challenge
> This is run 8 winner from 3 days ago. If it's been pending 3 days without implementation, there's probably a friction reason. What's blocking it? If this subconscious run recommends it again, is it just recycling?

**Defend:** Pending 3 days because the human hasn't approved+implemented it yet — the subconscious recommends, humans implement. The script exists and works. The friction is scheduling, not technical. However: this run's primary mandate is to fully close run 3 (the moratorium trigger). Recommending run 8 winner AGAIN while run 3 is still only partially implemented would violate moratorium protocol ordering.

### Round 2 Challenge
> The invariant violations it catches (tenant_id on leads, lead_stage, service_interest) — are these actually appearing in recent commits?

**Defend:** Not in the last 3 days of evidence. The most recent occurrences were the spec-drift bugs logged in bug-patterns.md around 2026-04-15. The script is preventive, not reactive. However, the absence of recent violations slightly weakens urgency vs. Idea 1 where violations were found AND regression risk is active.

### Round 3 Challenge
> Why not combine Check 9 (Idea 1) and wiring check_project_invariants (Idea 2) into one recommendation?

**Defend:** The subconscious discipline is ONE winner per run. Both are S-effort and could be done in 15 minutes together, but the recommendation must be atomic. If the human implements Idea 1 this week, Idea 2 naturally follows as the next implementation candidate (it's the second-oldest pending item after run 3 closes).

**Verdict: WEAKENED.** Correct diagnosis, correct action, but lower priority than Idea 1 given moratorium ordering. Moves to parking lot as next-in-line.

---

## Idea 3: Create scripts/check-widget-sync.sh and wire into pre-push

### Round 1 Challenge
> landing-page-v2/ is marked "legacy, do not touch" in CLAUDE.md. If it's not being touched, it can't drift. Does a sync guard for a do-not-touch file actually matter?

**Defend:** The byte-identical invariant in CLAUDE.md covers "widget/ AND frontend/public/widget/" primarily. landing-page-v2/ was added as the third copy in run 7 analysis, but if it's truly abandoned legacy code, the effective invariant is two-way: widget/ → frontend/public/widget/. The guard is still valuable for the two active copies. However, this weakens the "3-copy" framing — the real risk is the 2-copy sync between widget/ and frontend/public/widget/, and this has been pending since run 7.

### Round 2 Challenge
> No evidence of actual sync failures in 4 days since run 7. Is the risk real or theoretical?

**Defend:** The risk is structural, not theoretical — any widget edit that forgets to copy to frontend/public/widget/ silently ships broken embeds to all tenants. But without an incident in 4 days, urgency is lower than run 3's active regression risk (violations were actively in the codebase).

### Round 3 Challenge
> Vs. Idea 1: both are S-effort. Why is Idea 1 better?

**Defend:** Idea 1 directly closes the moratorium-triggering item (run 3, oldest pending). Idea 3 closes run 7 (newer pending). Moratorium protocol: close oldest first. Idea 3 is correct but second in line.

**Verdict: WEAKENED.** Valid, S-effort, established need. Not chosen because run 3 has moratorium priority. Remains in active_directions as pending_approval (unchanged status). Will be promoted when run 3 + run 8 are implemented.

---

## Summary

| Idea | Verdict | Reason |
|------|---------|--------|
| 1. JS Silent Catch Pre-commit Guard | **SURVIVED → CHOSEN** | Closes run 3 (moratorium trigger), prevents regression, S-effort |
| 2. Wire check_project_invariants.py | WEAKENED | Valid but run 3 has moratorium priority |
| 3. Widget 3-Copy Sync Guard | WEAKENED | Valid but second in moratorium queue |
| 4. Stripe webhook smoke tests | Not debated (top-3 only) | Parks to backlog |
| 5. local_seo_handlers.py split | Not debated (top-3 only) | New god class, parks to backlog |
