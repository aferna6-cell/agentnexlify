# Improvement Backlog — 2026-06-01-pm (Run 45)

## Active

- Scope em-dash check to skip JSX/TSX + wire check_project_invariants.py as pre-commit Check 10
  — single human-executed commit (~10 min), closes GH #194, implements run 8 + run 22 winners

## Parking Lot (survived debate but not chosen this run)

- **Item D → AUTONOMOUS-EXECUTABLE scope** (Idea 2, WEAKENED — premature; Item A must confirm
  first. Promote run 46 after today's commit confirms. Lead-qualifier-eval.yml is LOW-risk
  additive CI YAML, ~20 min direct execution OR autonomous via nightly once run 46 extends scope.)

- **GH Sprint Checklist Issue** (Idea 3, WEAKENED → Bonus Action. Execute after today's commit.
  Consolidates runs 4/7/14/35/38 into single GitHub checklist issue for remaining human sprint.)

## Rejected This Run

- **Extend nightly Python edit scope** (Idea 5) — WEAKENED/DO NOT PROPOSE. Meta-loop risk;
  adds blast radius to Python logic files. Direct human execution is faster (10 min) and
  already recommended.

- **GH #181 fix as winner** (Idea 4) — REJECTED by governance (rejected_paths, 5-consecutive
  threshold). Remains critical_standing_action. Do before email_sequences split.

## Questions for Next Run (Run 46)

1. Was the scope fix + Item A wiring committed? (Check: `grep -n "Check 10" scripts/hooks/pre-commit`)
2. If yes: Did Check 10 fire correctly on a test commit?
3. Was the GH Sprint Checklist Issue created?
4. Is GH #181 still open?
5. Is Item D (lead-qualifier-eval.yml) ready for autonomous scope or direct human execution?

## Standing Actions (Unchanged Priority Order)

1. **GH #181** — billing.py add 15000+25000, fix test_billing_amount_to_plan.py backwards assertions (~15 min, HUMAN)
2. **Item B** — scripts/check-widget-sync.sh + pre-push wire + CLAUDE.md fix (~15 min, HUMAN)
3. **Item D** — .github/workflows/lead-qualifier-eval.yml (~20 min, HUMAN OR AUTONOMOUS run 46)
4. **email_sequences.py split** — /god-class-splitter (~2h, HUMAN, do after GH #181)
5. **AI-to-Human Handoff v1** — via os_outbound_mirror.py (~1 day, HUMAN, do after moratorium exits)
