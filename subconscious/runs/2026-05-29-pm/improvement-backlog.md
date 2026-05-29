# Improvement Backlog — 2026-05-29-pm (Run 40)

## Active

- **Fix nightly-commit-review SKILL.md — add SKILL.md creation to LOW-risk autonomous scope.** Root cause of 2-cycle autonomous channel failure identified (`dc5ef8e`: "docs only, skipped"). ~15 min edit. Systemic fix for all 54 remaining god-class splits.
  - Bonus Action A: Create post-split-test-repair SKILL.md now (5 min, pre-written content in `subconscious/runs/2026-05-29/winning-concept.md §Implementation Sketch`). Do not wait for nightly.

## Parking Lot (survived debate but not chosen)

- **Invoke /god-class-splitter on email_sequences.py** — After post-split-test-repair SKILL.md exists. 1255L → email_crud + email_enrollment + email_processor. ~2h human execution. First priority after Step 4.
- **Update god-class-refactor_plan.md** — Add mandatory post-split test repair checklist step for all 54 targets. ~10 min. Complementary to SKILL.md fix, independent of autonomous channel.
- **PR #186 Dependabot merge** — @typescript-eslint/parser 8.58→8.60. Safe minor bump. 5 min.

## Rejected This Run

- **post-split-test-repair SKILL.md as winner (3rd recommendation)** — WEAKENED. Captured as Bonus Action instead. Human-execute framing is valid (5 min) but not systemic enough to win over channel fix.
- **/moratorium-sprint as winner** — WEAKENED. Standing action, no new forcing function since run 25. Invoke when human has 40 min.

## Questions for Next Run

1. Was `.claude/skills/nightly-commit-review/SKILL.md` updated to include SKILL.md creation in autonomous scope?
2. Was post-split-test-repair SKILL.md created (either by Bonus Action or next nightly cycle)? Check: `ls .claude/skills/post-split-test-repair/SKILL.md`
3. Was the next nightly review after the fix able to self-execute a SKILL.md item? (Confirms channel repair worked)
4. Was GH #181 billing fix applied? Check: `grep "15000" backend/routers/billing.py`
5. Was email_sequences.py split started? Check: `wc -l backend/routers/email_sequences.py`

## Critical Standing Actions (Require Human)

1. **GH #181** — `billing.py` AMOUNT_TO_PLAN missing 15000→autopilot + 25000→professional. Check 11 fires WARNING on every commit. ~15 min. `test_billing_amount_to_plan.py:38-44` backwards assertions must also be fixed.
2. **AI-to-Human Handoff v1** — run 38 winner, 43+ days, Critical gap all 7 industries. Agent OS reduces scope to ~1 day. Implementation sketch: `subconscious/runs/2026-05-28-pm/winning-concept.md`.
3. **Moratorium Sprint A/B/D** — check_project_invariants pre-commit (5 min), widget sync guard (15 min), CI eval workflow (20 min). moratorium-sprint SKILL.md ready (`7985fbb`).
