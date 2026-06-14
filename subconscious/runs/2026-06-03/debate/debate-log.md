# Debate Log — Run 48 (2026-06-03)

## Ranking by Impact (pre-debate)

1. **Idea 3** — Fix em-dashes + Widget Sync Guard combined (2 closures, ~25 min)
2. **Idea 1** — Fix 5 JSX em-dashes alone (unblocks Item A chain reaction, ~10 min)
3. **Idea 4** — email_sequences.py god-class split (largest code_health win, standing active_direction)

*Ideas 2 and 5 folded into Idea 3 and the Bonus section respectively.*

---

## Idea 3: Fix em-dashes + Widget Sync Guard as single commit

### Round 1 — Challenge
Is combining two items into one commit a smell? The moratorium sprint principle was to use `/moratorium-sprint` skill for batching. Why not just invoke the skill?

### Round 1 — Defend
`/moratorium-sprint` has been recommended 14+ times without invocation — the activation energy of "load a skill, read governance.json, plan across 4 items" is the documented bottleneck. Two specific files + one bash script is a different cognitive load. This is a scoped atomic commit, not a sprint. The skill is for when there are 4+ items; here we have 2.

More importantly: Idea 3 combines things that share a **natural pairing** — both are pre-commit/pre-push guard additions. The `CLAUDE.md Invariant #4` fix (2→3 copies) is required by Item B and touches a nearby doc. They belong together.

### Round 1 — Verdict
**SURVIVES** this objection. The combination is coherent and avoids the sprint activation-energy problem.

---

### Round 2 — Challenge
The em-dash fix has been framed as "scope the Python script to skip JSX/TSX" for runs 44/45/46. Now it's framed as "fix the actual em-dashes." Run 44 tried the scope-fix and was wrong about AUTONOMOUS-EXECUTABLE. What's different now?

### Round 2 — Defend
Run 44 chose the **scope workaround** (modify `check_project_invariants.py` to skip `.jsx/.tsx`). That was arguably the wrong approach — it hides violations rather than fixing them. CLAUDE.md personality rule explicitly bans em-dashes in ALL content, including JSX copy. The correct fix is to remove the 5 actual em-dashes.

Difference from run 44: run 44 tried a Python script edit (outside nightly autonomous scope). Run 48 recommends editing the 5 JSX files directly — which is exactly what a human should do in a 10-minute session. The violations are at known line numbers (nightly logged them precisely). There is no ambiguity about what to change.

### Round 2 — Verdict
**SURVIVES.** Direct em-dash fix (edit 5 JSX lines) is cleaner, correct per CLAUDE.md, and causes chain reaction. Scope workaround was an expedient that deserves to stay rejected.

---

### Round 3 — Challenge
The em-dash violations are in UI copy: `IntegrationsPage`, `SettingsInboundChannels`, `MessagingSettingsCards`. These might be intentional design choices — em-dashes as punctuation in UI text (e.g., "Widget — Settings"). Changing them might degrade UX or break product copy.

### Round 3 — Defend
CLAUDE.md `personality.md` rule is unambiguous: em-dash is banned in content. This rule was applied to `WizardStepAutoKB.jsx` and `AutomationActivityCard.jsx` in commit 8f680e8 (2026-05-05) without reported UX issues. The violations aren't architectural — they're copy. A simple replacement (em-dash → hyphen) is readable and correct per project conventions. If specific copy needs review, that's a minor UX judgment call that doesn't block the fix from being recommended.

### Round 3 — Verdict
**SURVIVES.** Em-dash ban is a documented project rule. Prior fix (8f680e8) set precedent.

**Overall Verdict for Idea 3: SURVIVES all 3 rounds → WINNER**

---

## Idea 1: Fix 5 JSX em-dashes alone (subset of Idea 3)

### Challenge
Why recommend just the em-dash fix without adding the widget sync guard? Both are ~10-15 min. Together they achieve 2 closures. Is splitting them actually strategic?

### Defend
The em-dash fix is faster (~10 min) and has the cascading autonomous effect (Item A wires itself overnight). If human has only 10 min, Idea 1 is better than nothing. If human has 25 min, Idea 3 is superior. Idea 1 survives as a "minimal path" option but is dominated by Idea 3 if human is present for a session.

**Verdict: WEAKENED — dominated by Idea 3 when human is available. Kept as parking lot in case human has 10 min but not 25.**

---

## Idea 4: Invoke /god-class-splitter on email_sequences.py

### Round 1 — Challenge
This has been the recommended active_direction since run 35 (day 8+ unimplemented). Run 41 confirmed it as winner. Still no implementation. If it hasn't been done in 4+ days as the #1 recommended action, what makes run 48 different? Is the evidence strong enough to override the moratorium priority on structural guards (em-dash, widget sync)?

### Round 1 — Defend
New state: post-split-test-repair SKILL.md now exists (d481799 — run 41 governance correction), which was the final prerequisite. The autonomous channel is proven to work for tool creation. The split itself still requires a ~2-hour human session (M-effort), which is higher activation than the 25-min Idea 3. During moratorium, shorter wins first.

### Round 1 — Verdict
**WEAKENED.** Valid standing action; loses to Idea 3 on leverage-per-minute. Stays as primary parking lot item — the next winner after Items A and B close.

---

### Round 2 — Challenge
email_sequences.py is 1255L but it's a router, not a service. God-class splitter is designed for files that mix concerns. Do the 3 concerns (CRUD/enrollment/processor) actually justify the split risk? What if the tests break?

### Round 2 — Defend
post-split-test-repair SKILL.md was created specifically because 100% of prior splits required @patch target repair. The skill now exists for exactly this scenario. Prior splits (widget_helpers.py 6cf4646, local_seo 5f2cd2b) demonstrate the pattern is reliable. The 3 concerns are clean and independent — enrollment doesn't call processor, CRUD doesn't call enrollment.

### Round 2 — Verdict
**WEAKENED further — but valid.** The split is sound; the timing favors moratorium-exit items first. Parking lot.

**Overall Verdict for Idea 4: WEAKENED → Parking Lot (second priority after em-dash + widget sync)**

---

## Synthesis

| Idea | Verdict | Disposition |
|------|---------|-------------|
| Idea 3: Fix em-dashes + Widget Sync Guard combined | **SURVIVES → WINNER** | Primary recommendation |
| Idea 1: Fix em-dashes alone | WEAKENED | Parking lot — minimal path if time-constrained |
| Idea 4: email_sequences split | WEAKENED | Parking lot — next after Items A+B closed |
| Idea 5: Fix GH #181 billing | In rejected_paths — new evidence applies to path only; mechanism still requires human; note as Bonus B in winning concept | Bonus action |
| Idea 2: Widget sync guard alone | Subsumed by Idea 3 | N/A |

**Winner: Fix 5 JSX em-dashes + create widget sync guard as single ~25-min human commit.**

**Run 48 governance correction applied: Item D status → `implemented` (nightly 42992fa, 2026-06-03). runs_implemented: 12→13. pending drops 16→15.**
