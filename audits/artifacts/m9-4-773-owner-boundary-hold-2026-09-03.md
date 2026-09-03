# M9.4 #773 — frozen at owner boundary (2026-09-03)

**Status:** FROZEN — merge-ready, hold for owner merge approval  
**PR:** https://github.com/aferna6-cell/agentnexlify/pull/773  
**CI:** PR Validation run [33783280252](https://github.com/aferna6-cell/agentnexlify/actions/runs/33783280252) SUCCESS  
**Draft:** no · **Mergeable:** CLEAN

## Independent check (this freeze)

Agrees with the stratified-default / report-integrity fix on
`cursor/m9-4-bakeoff-miss-analysis-b916`:

- `run_bakeoff(limit=N)` defaults to **stratified** sampling; `sample="prefix"` is opt-in
- Reports persist `sample`, `case_ids`, and `category_counts`
- Valid-but-below-bar risk/approval (and recall/deps) misses classify as
  `model_incomplete_valid`, not `ok`
- Prefix `--limit 10` still reproduces the biased `l2_l3_approval_placement` window
- No ExpectedPlan/gold in the user prompt; tenant mismatch still hard-fails;
  no WorkflowStore / Action Executor / provider wiring

## Hard stops until owner merge

- Do **not** merge #773 without owner approval
- Do **not** run the paid / live bakeoff
- Do **not** start M9.5 shadow planner

## Next action after owner merge approval

Bounded stratified live run only, then a promotion decision:

```text
python3 scripts/run_m9_planner_bakeoff.py \
  --mode live --sample stratified --limit 24 --repetitions 0 \
  --models claude-opus-4-8,claude-haiku-4-5-20251001
```

Documented cap: **~$0.43** estimate, **~$0.52** with 20% buffer. Owner
approval is still required before that paid run. M9.5 stays blocked until
the promotion decision.
