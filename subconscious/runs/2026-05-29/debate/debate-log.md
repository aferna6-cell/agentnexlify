# Debate Log — Run 39 (2026-05-29)

Top 3 ideas by impact: Idea 1 (post-split-test-repair SKILL.md), Idea 2 (/god-class-splitter email_sequences.py), Idea 3 (handoff_requests migration only).

---

## Idea 1: post-split-test-repair SKILL.md

### Round 1
**Challenge:** This was run 36's winner (2026-05-27). dc5ef8e (nightly 2026-05-28) skipped it, calling it "docs only." Now run 39 is returning to run 36's winner without a new mechanism. What's different?

**Defense:** The mechanism changed: `061582c` (nightly 2026-05-29) implemented Check 11 — a similarly scoped item (new bash block, ~20 lines) — DESPITE the same "docs only" characterization that blocked dc5ef8e. The nightly review's execution criteria shifted. Also: today's nightly log explicitly lists post-split-test-repair in "Standing Actions #5" — the review is now AWARE of the item and has it queued. dc5ef8e ran with 3 unreviewed commits and prioritized the most urgently labeled one (Check 11 flagged HIGH in run 37). Now that Check 11 is done, post-split-test-repair is the remaining autonomous-executable item.

### Round 2
**Challenge:** The nightly review chose Check 11 OVER post-split-test-repair twice. Maybe it has a persistent preference for pre-commit guards over skill docs. What evidence says it will implement a SKILL.md file?

**Defense:** The nightly review has implemented SKILL.md files exactly 3 times: 7985fbb (moratorium-sprint SKILL.md), e848b87 (god-class-splitter SKILL.md), and 2ce31b2 (Moratorium Escalation Protocol section in nightly-commit-review SKILL.md). All 3 were labeled AUTONOMOUS-EXECUTABLE in the preceding winning-concept.md. The pattern is: explicit label in winning-concept → nightly review implements. Run 36's winning-concept.md says "Autonomously executable by nightly review (pure new .md file, LOW-risk)" — that label is present but not as explicit as the pattern requires. Run 39's winning-concept.md will use the stronger directive form: "AUTONOMOUS-EXECUTABLE: nightly review should implement directly."

### Round 3
**Challenge:** Why not recommend the email_sequences.py split directly? The SKILL.md is just scaffolding — the actual value is the split. Recommending the enabler instead of the enabled action adds a cycle of delay.

**Defense:** bca2082 (2026-05-28), 5f2cd2b (2026-05-26), and 4afb3cf (2026-05-27) prove that every split generates stale @patch repair commits WITHOUT the skill guide. That means: recommending the split without the guide guarantees a 3-commit sequence (split + 2 repair commits) instead of 1 clean PR. Rule 8 (no half migrations) and the spirit of the rule ("a migration finishes in one PR") mean the guide should exist first. The delay is one nightly review cycle (~12 hours). The cost of not delaying is 2 extra commits and potential CI failures after the split.

**Verdict: SURVIVES** — strongest autonomous execution evidence in 5 runs (061582c same day), nightly review confirmed aware, strongest SKILL.md precedent (3/3 times explicit label worked). 

---

## Idea 2: /god-class-splitter on email_sequences.py

### Round 1
**Challenge:** email_sequences.py is 1255L and has been the run 35 winner for 3+ days. The god-class-splitter SKILL.md exists. Why continue waiting for the post-split-test-repair SKILL.md when the split can just happen now?

**Defense:** 100% recurrence rate evidence: every split generates test-repair commits (5f2cd2b, 4afb3cf, bca2082 — that's 3 splits/migrations, 3 repair commits). Without the SKILL.md guide, the email_sequences split will produce a 4th repair commit. The split is ~2h human execution. Spending 2h then discovering stale @patch errors and spending another 30 min repairing is a worse outcome than spending 5 min on the SKILL.md first and doing the split cleanly.

### Round 2
**Challenge:** 3 repair commits is acceptable overhead for a 1255L → 3×400L reduction. The split value far outweighs 30 minutes of repair. The SKILL.md is a nice-to-have, not a blocker.

**Defense:** It's not just 30 minutes of repair. The stale @patch errors fail CI after the split commit is pushed. That means: merge → CI red → repair commit → CI green. The split PR cannot be merged in a single pass. For a moratorium context where we're trying to demonstrate implementation velocity, a PR that immediately breaks CI is counterproductive. The SKILL.md makes the split a clean 1-PR operation.

### Round 3
**Challenge:** The post-split-test-repair SKILL.md might not be implemented by nightly review. If it isn't, we're one more cycle behind on the email_sequences split. The split recommendation at least creates direct human accountability.

**Defense:** If post-split-test-repair SKILL.md isn't implemented by nightly review within 24h, run 40 can recommend the email_sequences split directly with a note to do the repair manually. The 24h wait is not a meaningful delay for a 2h human task. The SKILL.md uncertainty is lower than the certainty of repair-commit overhead without it.

**Verdict: WEAKENED → Parking Lot** — "next after post-split-test-repair SKILL.md confirmed to exist." Promoted to first priority for run 40 if SKILL.md is created.

---

## Idea 3: handoff_requests migration only

### Round 1
**Challenge:** Rule 8 — "a migration finishes in one PR or stays unstarted." Creating only the SQL migration without the detection code and service layer is a textbook half-migration.

**Defense:** The migration creates a new table with no existing dependents. Unlike a schema change to an existing table (which would break live queries if partial), a new empty table has zero impact on running code. It's more analogous to creating a new file in a directory than modifying a file.

### Round 2
**Challenge:** The defense is rationalization. The purpose of the handoff_requests table is to receive rows from widget_chat.py's handoff detection. Without the detection code, the table has no write path and no value. Future developers who see the table will be confused: "Why does this table exist with zero rows?" The migration is dead weight until widget_chat.py is modified.

**Defense:** Schema-first development is a legitimate pattern. But the defense has to acknowledge: the customer gap is "AI-to-Human Handoff," not "has a handoff_requests table." The gap is in the user experience, not in the schema.

### Round 3
**Challenge:** Moratorium parallel track has been authorized since run 29 specifically for customer_value work. But run 38's full AI-to-Human Handoff v1 (~1 day) is the authorized parallel-track action. A 15-minute migration stub doesn't close the customer gap; it just makes a partial commitment. If the human has 15 minutes, they should spend it on GH #181 (billing fix, ~15 min, closing a CRITICAL_STANDING_ACTION). The migration stub adds complexity without closing anything.

**Verdict: KILLED** — half-migration violates Rule 8. 15 minutes better spent on GH #181 billing fix. Full AI-to-Human Handoff v1 remains the pending_approval active_direction for human sprint.

---

## Summary

| Idea | Verdict |
|------|---------|
| post-split-test-repair SKILL.md | **SURVIVES → WINNER** |
| /god-class-splitter email_sequences.py | **WEAKENED → parking lot** |
| handoff_requests migration only | **KILLED — Rule 8 half-migration** |
| Billing Constants Contract Tests | Not debated — deferred post-GH #181 fix |
| Invoke /moratorium-sprint | Not debated — 14th rec, mechanism uncertain, standing action |
