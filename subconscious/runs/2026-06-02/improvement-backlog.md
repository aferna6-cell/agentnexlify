# Improvement Backlog — 2026-06-02 (Run 46)

## Active

- Execute Item A: scope em-dash check to skip JSX/TSX + wire Check 10 to pre-commit
  (~10 min, human-execute this interactive session, closes GH #194, implements run 8 + run 22)

## Parking Lot (survived debate but not chosen this run)

- **Item D AUTONOMOUS-EXECUTABLE** (Idea 3, WEAKENED → Parking Lot. Promote as RUN 47 WINNER
  if Item A still unimplemented after this session. Extend nightly scope to cover
  `.github/workflows/*.yml` creation + inline lead-qualifier-eval.yml patch. Run 45 backlog
  set this constraint explicitly: "premature until Item A confirms.")

- **Billing.py location investigation** (Idea 2, WEAKENED → Bonus A. Run `find backend/
  -name "*billing*"` + `grep -rn "AMOUNT_TO_PLAN" backend/` before any GH #181 fix attempt.
  New evidence: billing.py not found at expected path — may explain 2 failed fix attempts.
  May reveal GH #181 already resolved in god-class refactor. 5 min, do after Item A commit.)

- **Item B AUTONOMOUS-EXECUTABLE** (Idea 4, WEAKENED → Parking Lot. Rejected-path adjacency
  for concurrent A+B execution. Sequence: Item A confirms → then Item B autonomous. ~15-line
  bash script creation + pre-push hook entry.)

## Rejected This Run

- **GH sprint checklist as winner** (Idea 5, WEAKENED → Bonus B. Precedent shows GH issues
  without implementation pressure don't drive action faster than direct recs. Included as
  Bonus B in winning-concept.md.)

## Questions for Next Run (Run 47)

1. Was Item A executed? (`grep -n "Check 10" scripts/hooks/pre-commit` should return content)
2. Did `python3 scripts/check_project_invariants.py` exit 0 after the fix?
3. Was Bonus A (billing.py investigation) run? Where is AMOUNT_TO_PLAN now?
4. Is GH #181 still open, or can it close as already-fixed?
5. Was GH sprint checklist issue created (Bonus B)?

## Standing Actions (Priority Order)

1. **GH #181** — INVESTIGATE billing.py location first (Bonus A, 5 min); then fix
   AMOUNT_TO_PLAN (~10 min, HUMAN)
2. **Item B** — scripts/check-widget-sync.sh + pre-push wire (~15 min, HUMAN)
3. **Item D** — .github/workflows/lead-qualifier-eval.yml (~20 min, HUMAN or AUTONOMOUS run 47)
4. **email_sequences.py split** — /god-class-splitter (~2h, HUMAN, after GH #181)
5. **AI-to-Human Handoff v1** — via os_outbound_mirror.py (~1 day, HUMAN, after moratorium exits)
