# Debate Log — 2026-06-02 (Run 46)

Top 3 ideas ranked by impact: Idea 1 (Item A), Idea 2 (billing.py investigation), Idea 3 (Item D autonomous).

---

## Idea 1: Item A — Scope em-dash check + wire Check 10 to pre-commit

### Round 1
**Challenge:** This is the 4th consecutive run recommending Item A (runs 43, 44, 45, 46).
The Widget Sync Guard triggered a mechanism switch at run 18 after exactly 4 consecutive
recs. Should the same threshold apply here?

**Defend:** Widget Sync Guard hit the mechanism switch because no active violation existed
at time of recommendation — widget copies were IN SYNC, so the urgency was theoretical.
Item A is different: `check_project_invariants.py` fails EVERY nightly run with exit 1
(confirmed in 3 consecutive nightly logs). The blockage is active, not hypothetical. Also,
runs 42→43→44 were not identical — each built new autonomous infrastructure. Run 45 was the
first purely "human-execute now" recommendation. Run 46 is the second — mechanism has already
shifted, this is not a 4th iteration of the same mechanism.

### Round 2
**Challenge:** If Item A has been the right answer for 4 runs without implementation, what
makes run 46 different from runs 43-45?

**Defend:** Run 46 has a specific forcing function none of the prior runs had simultaneously:
(1) human is running the subconscious interactively — they are AT the keyboard RIGHT NOW.
(2) Nightly 2026-06-02 independently reinforced this exact recommendation and flagged it in
the ops log. (3) The implementation sketch has been pre-written and battle-tested through
4 runs of review. Three independent signal sources (subconscious × 4 runs, nightly × 3
reviews, live interactive session) are aligned on the same 10-minute action.

### Round 3
**Challenge:** Should mechanism switch from "re-recommend human execution" to "recommend
Item D autonomous" (which the run 45 backlog said to do in run 47)?

**Defend:** That escalation belongs in run 47, not run 46. Run 45 backlog explicitly set
"promote Item D to run 46 winner IF Item A confirmed" — Item A not confirmed is not the
same as "switch now." Run 47 is the mandated switch point. Recommending Item D in run 46
would skip the mandate boundary and confuse sequencing. The human has one more interactive-
session window before the mechanism switches.

**Verdict: SURVIVES → WINNER.**
Final recommendation via human-execution path. Run 47 mandate: switch to Item D autonomous
if Item A still unimplemented.

---

## Idea 2: Billing.py Investigation

### Round 1
**Challenge:** GH #181 is in `rejected_paths`. Recommending billing investigation is
adjacent to recommending GH #181 as winner — does this violate the rejected_paths rule?

**Defend:** Categorically different. Rejected_paths bars GH #181 as the *winning concept*.
A 5-minute read-only investigation (find + grep) is not a winning concept — it's pre-work.
The rejected_paths note says "barred from being chosen as winner unless human implements it
or new evidence emerges." The billing.py path mystery IS new evidence. Investigation is how
we determine whether to update or close GH #181.

### Round 2
**Challenge:** Even if billing.py moved, locating it is trivial (one find command). Is this
substantive enough to be a winning concept?

**Defend:** Correct — this is NOT substantive enough to be the winner. The finding justifies
inclusion as a Bonus Action, not as the primary recommendation. The value is in preventing a
third failed fix attempt against a wrong file path. If AMOUNT_TO_PLAN already has 15000+25000
in a renamed file, GH #181 closes as resolved without any implementation — that's a free win
on a 26-day standing action.

### Round 3
**Challenge:** Runs 31-35 all cited `billing.py` AFTER the god-class refactor (PR #180,
May 23). If the file had moved, wouldn't those runs have caught it?

**Defend:** No — runs 31-35 cited `billing.py` from memory/governance.json notes, not by
re-verifying the path. Run 35 moved GH #181 to critical_standing_action and stopped
verifying location. The grep failure in THIS run is direct evidence the file is not where
the sketches say it is. Check 11 (billing-constant-guard) fires WARNING but only checks
that entries are missing — it doesn't reveal the file path. Previous runners assumed
continuity; they were wrong to do so.

**Verdict: WEAKENED → Bonus Action A.**
Include in winning-concept.md §Bonus A. Do after Item A commit.

---

## Idea 3: Item D AUTONOMOUS-EXECUTABLE (CI YAML creation)

### Round 1
**Challenge:** Run 45 backlog states: "premature — Item A must confirm first." This run
would violate that constraint.

**Defend:** Correct. The sequencing constraint exists because extending autonomous scope
should be validated one step at a time. Item A's autonomous infrastructure (runs 42→43→44)
was fully built but couldn't execute because of the Python script edit requirement. Adding
CI YAML scope before confirming Item A's human execution creates an unvalidated chain of
scope extensions. The constraint was explicitly set for this run.

### Round 2
**Challenge:** lead-qualifier-eval.yml is purely additive (new file, no code logic). Even
without Item A confirmed, the risk seems low. What's the actual harm in extending now?

**Defend:** The risk is autonomous channel credibility. The channel has had failures before
(post-split-test-repair SKILL.md missed twice). If CI YAML extension also fails, three
consecutive scope-extension failures undermine trust in the channel. Better to confirm one
scope extension works (Item A via human) before adding another untested scope (CI YAML).

### Round 3
**Challenge:** If Item A never gets executed via human path, Item D will sit in parking lot
indefinitely. Shouldn't we act on what CAN be done autonomously?

**Defend:** This is exactly the run 47 mandate. If Item A is not done this session, run 47
winner IS Item D autonomous — that's already agreed. Run 46 is the last human-execution
recommendation before the autonomous pivot. One more session is not indefinitely.

**Verdict: WEAKENED → Parking Lot. Promote as run 47 winner if Item A unimplemented.**

---

## Verdicts Summary

| Idea | Verdict | Disposition |
|------|---------|-------------|
| 1: Item A execution | SURVIVES → WINNER | Final human-execution rec before mechanism switch |
| 2: Billing.py investigation | WEAKENED → Bonus A | Include in winning-concept, 5 min, do after Item A |
| 3: Item D CI YAML autonomous | WEAKENED → Parking Lot | Run 47 winner if Item A still unimplemented |
| 4: Item B autonomous | WEAKENED → Parking Lot | Rejected-path adjacency; sequence after Item A |
| 5: GH sprint checklist | WEAKENED → Bonus B | Include as Bonus B, GitHub-native visibility |
