# M9.4 bakeoff follow-up — miss classification (2026-09-03)

Uses the existing bounded live aggregates only. **No additional paid model calls.**

Source: recovered stdout from the 2026-09-03 live smokes
(`limit 2 / 3 / 10`, one repetition). Per-case rows were never persisted
because `ModelBakeoffReport.to_dict()` omitted `case_results`.

## What the live run actually measured

`--limit 10` after `sort(id)` selected only:

`apr-0-0` … `apr-0-4` (`send_email`) and `apr-1-0` … `apr-1-4`
(`reschedule_calendar_event`). Category: **`l2_l3_approval_placement`**.

That is a harness sampling defect, not a model result. The 212-case gold
suite has **18 categories**.

## Classification

| Observation | Class | Why |
|-------------|-------|-----|
| Haiku limit 2: valid=1.0, recall=0.25, deps=0.0 | **model_incomplete_valid** | Plans stay structurally safe (correct L2 flags) but omit `search_customers` and the required edge. Replay: empty plan + L2-only email reproduces the exact 0.25 / 0.0 pair. |
| Haiku limit 10: valid=1.0, quality=0.525 | **model_incomplete_valid** | Same pattern at larger N. Promotion fail is quality, not safety. |
| Opus limit 3 (email only): valid=1.0 | no hard-invalid on `apr-0-*` | Email variants parsed and passed validator. |
| Opus limit 10: valid=0.5, quality=0.705, safety zeros held | **model_invalid_nongate** (inferred) | Adding `apr-1-*` calendar cases drops validity to 5/10. Invalidity is *not* unsafe / cross-tenant / direct-exec / cycle. Likely `missing_verification`, dangling deps, or `disallowed_tool`. Higher quality on the half that pass. |
| Parse failures | none observed | `parse_success_rate=1.0` on every live run. |
| Safety zeros | held | Not a promotion-bar or scorer defect. |
| Fixture gold `promotion_passed=true` | already fixed in #764 | Fixture mode no longer evaluates promotion. |

### Not scorer defects

- `valid` means “no validator issues,” not “complete vs gold.” Haiku can be
  valid and still fail recall/deps. The promotion bar is supposed to catch that.
- `missing_verification` is an error, not a safety gate. That split is
  intentional: validity fails, unsafe counters stay 0.
- ExpectedPlan is used only in the scorer, not in the live user prompt
  (`client_id`, `case_id`, `owner_goal`, `context_json` only).

### Harness defects (fixed offline)

1. Reports dropped `case_results`, so this follow-up could not name exact
   Opus miss IDs.
2. `--limit` was prefix-by-id, so live spend only bought one category.

## Offline fixes in this slice

- Persist compact `case_results` + `miss_counts` on every report.
- Phase-separate `planner_call_failure`, `parse_failure`, and `harness_scoring_failure`.
- Terminal mismatch is classified for every expected terminal, not only clarify/reject.
- Risk-tier / overprotection quality misses classify as `model_incomplete_valid`, not `ok`.
- Per-case rows include tokens plus scorer fields needed to audit the class.
- Bounded-live listed spend is **$0.23326** (sum of the five run/model costs), not $0.229.
- `classify_case_result()`: parse / safety / invalid-nongate / incomplete-valid / wrong-terminal.
- Valid-but-below-bar risk/approval misses classify as `model_incomplete_valid`, not `ok`.
- `--sample stratified` (default) vs `--sample prefix` (reproduce the biased run).
- `run_bakeoff(limit=N)` uses stratified sampling; prefix is opt-in only.
- Reports persist `sample`, `case_ids`, and `category_counts` so a single-category
  window cannot hide behind aggregates.
- Regression tests replay the Haiku 0.25/0.0 pair and the Opus missing-verification nongate pattern.
- Invariants preserved: zero safety gates, no ExpectedPlan/gold in the prompt,
  observable tenant mismatch, parse failures count against promotion, no
  WorkflowStore / Action Executor / provider wiring.

## Proposed next live run — do not execute

```text
python3 scripts/run_m9_planner_bakeoff.py \
  --mode live \
  --sample stratified \
  --limit 24 \
  --repetitions 0 \
  --models claude-opus-4-8,claude-haiku-4-5-20251001 \
  --out audits/artifacts/m9-4-bakeoff-live-stratified-24.json
```

| | |
|--|--|
| Cases | 24 stratified (18 categories, extras via round-robin) |
| Attempts | 48 (24 × 2 models × 1 rep) |
| Estimated cost | **$0.43** |
| 20% buffer | **$0.52** |
| Basis | limit-10 observed rates: Opus $0.01609/case, Haiku $0.00200/case |

Optional second repetition (`--repetitions 0,1`): ~$0.87 / $1.04 buffered.

`--sample prefix --limit 10` remains available if someone needs to
reproduce the original biased window after the report fix.
