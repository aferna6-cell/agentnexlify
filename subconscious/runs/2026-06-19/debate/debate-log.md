# Debate Log — 2026-06-19 (Run 61)

Top 3 ranked by impact: Idea 1 (GH #308), Idea 2 (GH #292/#293), Idea 5 (schema checklist).

---

## Idea 1: Fix GH #308 — Webhook Idempotency Early-Write (3rd consecutive)

### Challenge Round 1 — Evidence strength
**Attack:** Third consecutive recommendation of the same winner. Nightly review has a
"nightly_review_path: true" flag but "autonomous_executable: false" — the nightly won't
implement it. Human hasn't acted in 3 runs. Is this just repeating a failed mechanism?

**Defend:** The implementation sketch is complete, unambiguous, and verified against the
actual code (idempotency.py:85-93 confirmed). The failure mode is not "sketch unclear" —
it's "human hasn't had a session to implement it." High-velocity sprint (leadgen, onboarding,
security) may have redirected attention. Payment bug with moratorium override is still valid.

**Ruling:** Evidence is strong. Mechanism is "awaiting human session," not "sketch wrong."

### Challenge Round 2 — Highest leverage right now
**Attack:** GH #308 is 20 min (async Python, exception handling). GH #292/#293 is 10 min
(add plan names to sets). Both require human. Lower activation energy = higher implementation
probability. Should GH #292/#293 win on practicality?

**Defend:** Payment event loss (GH #308) is categorically more severe than feature
unavailability (GH #292/#293). If a stripe webhook fails and the idempotency row persists,
that tenant never recovers — manual intervention required. GH #292/#293 is broken for new
tenants but a workaround exists (support can manually set limits). Revenue recovery > feature
access. Priority must reflect severity.

**Ruling:** Severity argument holds. GH #308 retains winner slot on merit.

### Challenge Round 3 — Pattern from GH #181
**Attack:** GH #181 was recommended 5 consecutive times before governance pivot (runs 31-35).
We're at run 3 of GH #308. Is there value in pre-emptively setting a mechanism-change
mandate now rather than waiting until run 5?

**Defend:** GH #181's failure mode was different — two prior implementation attempts
(c72b535, 1eaaeec) both targeted the wrong file path. GH #308 has had ZERO implementation
attempts — nightly review path is non-autonomous by design (medium-risk payment code).
The bottleneck is scheduling, not ambiguity. A run-4 mandate is appropriate (consistent
with how previous consecutive-run patterns were handled: boundary condition set at N+1).

**Ruling:** SURVIVES. Set RUN 62 MANDATE: if GH #308 still unimplemented, switch to
GH #292/#293 as winner (lower activation energy, 10 min, also revenue-affecting).

**VERDICT: SURVIVES → WINNER**

---

## Idea 2: Fix GH #292/#293 — chatbot/agent_os Plan-Name Dicts

### Challenge Round 1 — Severity vs GH #308
**Attack:** Both require human. GH #308 is more severe. Why debate this as winner when
GH #308 is still on the table?

**Defend:** GH #292/#293 is compelling as a mandate path. If GH #308 doesn't land in
run 62, GH #292/#293 is the natural fallback — it's shorter (10 min), affects more tenants
(every new paid signup since repricing), and SMS/Zapier breakage directly impacts product
trust. Good candidate for run 62 mandate.

**Ruling:** Valid pending item, lower severity than GH #308. Correct as mandate path.

### Challenge Round 2 — Product decision ambiguity
**Attack:** Proposed SMS limits (chatbot=200/day, agent_os=500/day) were pre-made in run 60
Bonus A. But these are unconfirmed by the product owner. Is this a true S-effort or does
it require a product conversation first?

**Defend:** Run 60 Bonus A sketch already sets limits. The sms_rate_limiter._UNLIMITED_PLANS
pattern suggests unlimited plans bypass the limiter entirely — both chatbot and agent_os
should be unlimited on their paid tiers (this is simpler and avoids product debate).
Alternatively, just match the existing pattern for 'professional'/'enterprise' (which are
in _UNLIMITED_PLANS). This resolves the product decision without a conversation.

**Ruling:** Product decision resolvable by mirroring existing unlimited-plan pattern.

### Challenge Round 3 — Moratorium compatibility
**Attack:** Moratorium is active. Adding these plan names is arguably a feature fix, not
a pure pre-commit guard. Does it violate moratorium principles?

**Defend:** Moratorium protects against adding net-new complexity. Adding missing plan
names to existing lists is a correction, not a feature. Same class as the em-dash fixes
and plan-name dict entries that were moratorium-exempt in prior runs.

**Verdict: SURVIVES WEAKENED → parking lot with RUN 62 MANDATE if GH #308 unimplemented.**

---

## Idea 5: Add New-Table Checklist to schema-discipline.md

### Challenge Round 1 — Is this autonomous?
**Attack:** Run 44 showed nightly review cannot edit existing Python scripts. schema-discipline.md
is a markdown file, not Python — different class. But has nightly successfully edited
existing .md rule files before?

**Defend:** Nightly has created new .md files (god-class-splitter SKILL.md, post-split-test-repair
SKILL.md, moratorium-sprint SKILL.md). Editing an existing .md rule file is adjacent but
distinct from creating new files. The run 44 failure was specifically for Python script
edits. Markdown edits to rule files may work — e.g., nightly-commit-review SKILL.md was
updated by nightly in run 43 (4226ef4). That's an existing .md file edit. Precedent exists.

**Ruling:** Precedent exists for nightly editing existing .md files. Potentially autonomous.

### Challenge Round 2 — Highest leverage right now?
**Attack:** There are 2 confirmed revenue-affecting bugs (GH #308, GH #292/#293) pending.
A documentation checklist is low urgency compared to actively broken payment recovery and
new-tenant feature availability. Why propose this as top-3?

**Defend:** This is the only idea with a clear autonomous path (nightly review tonight).
It doesn't compete with GH #308/GH #292/#293 — it's additive and parallel. If nightly
can implement it tonight, it compounds while human works on the payment fix.

**Ruling:** Valid autonomous candidate but loses to GH #308 on severity. Not worth winner
slot when payment bug is pending.

### Challenge Round 3 — Sequencing
**Attack:** Is this well-timed? Agent OS hasn't shipped a new service since os_graph_memory.
No active sprint that would benefit immediately.

**Defend:** Prevention is best before the next sprint. But timing is not urgent.

**VERDICT: WEAKENED → parking lot. Valid autonomous candidate for a future run when payment
bugs are resolved.**

---

## Summary

| Idea | Verdict | Reason |
|------|---------|--------|
| GH #308 (idempotency) | SURVIVES → WINNER | Payment revenue, moratorium override, complete sketch |
| GH #292/#293 (plan dicts) | SURVIVES WEAKENED | Valid, RUN 62 MANDATE if #308 unimplemented |
| schema-discipline checklist | WEAKENED → parking lot | Autonomous but lower urgency vs open revenue bugs |
