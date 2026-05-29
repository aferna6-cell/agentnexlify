# Improvement Backlog — 2026-05-29 (Run 39)

## Active

- **Create `.claude/skills/post-split-test-repair/SKILL.md`** — AUTONOMOUS-EXECUTABLE by nightly review. 8-step checklist for repointing stale @patch targets after splits. Unblocks email_sequences.py split (run 35 winner).

## Parking Lot (survived debate but not chosen)

- **Invoke /god-class-splitter on email_sequences.py** — WEAKENED (sequencing: SKILL.md must exist first). First priority for run 40 if SKILL.md confirmed created. 1255L → email_crud + email_enrollment + email_processor. ~2h human execution.
- **Billing Constants Contract Tests (run 30)** — valid after GH #181 fix. Parametric pytest assertions for all 5 plans × current prices. Creates stronger CI forcing function than Check 11 WARNING.
- **Invoke /moratorium-sprint (Items A/B/D)** — standing action, not re-recommended as winner (14th would add noise, not value). Invoke when human has 40 min.

## Rejected This Run

- **handoff_requests migration only** — KILLED (Rule 8: half-migration; table without detection code is dead weight). Full AI-to-Human Handoff v1 via Agent OS remains the pending parallel-track action.

## Governance Correction Applied

- **Run 37 (billing-constant-guard Check 11):** status pending_approval → **implemented** (commit `061582c`, nightly-commit-review 2026-05-29). runs_implemented: 8 → 9.

## Critical Standing Actions (Require Human)

1. **GH #181** — `billing.py` AMOUNT_TO_PLAN missing 15000→autopilot + 25000→professional. Check 11 fires WARNING on every commit. ~15 min. `test_billing_amount_to_plan.py:38-44` backwards assertions must also be fixed.
2. **AI-to-Human Handoff v1** — run 38 winner, 43 days, Critical gap all 7 industries. Agent OS reduces scope to ~1 day. Run implementation sketch: `subconscious/runs/2026-05-28-pm/winning-concept.md`.
3. **Moratorium Sprint A/B/D** — check_project_invariants pre-commit (5 min), widget sync guard (15 min), CI eval workflow (20 min). moratorium-sprint SKILL.md ready (`7985fbb`).

## Questions for Next Run

1. Was post-split-test-repair SKILL.md created by nightly review? (Check: `ls .claude/skills/post-split-test-repair/SKILL.md`)
2. If yes: was email_sequences.py split executed? (Check: `wc -l backend/routers/email_sequences.py` — should be <600L or file should not exist)
3. Was GH #181 billing fix applied? (Check: `grep "15000" backend/routers/billing.py` — should return a line)
4. Is moratorium still active? (Check: pending_approvals ≤ 2?)
