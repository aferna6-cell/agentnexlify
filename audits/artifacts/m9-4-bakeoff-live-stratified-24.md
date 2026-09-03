# M9.4 live stratified-24 bakeoff — Railway staging (2026-09-03)

Authorized bounded run on the existing cheerful-freedom / staging path.
Local `ANTHROPIC_API_KEY` was unset; the key was used only as a Railway
reference variable on one-off service `m9-bakeoff-runner`. No secret values
were inspected or printed.

## Command

```text
python -m backend.services.os_workflows.run_live_bakeoff
# equivalent:
# --mode live --sample stratified --limit 24 --repetitions 0
# --models claude-opus-4-8,claude-haiku-4-5-20251001
```

## Run outcome

| Field | Value |
|---|---|
| Project | cheerful-freedom |
| Environment | staging |
| Service | m9-bakeoff-runner |
| Deployment | `5e717206-1648-4ae5-b505-b4c1cc393aa4` |
| Commit | `bc9e80b3` |
| Started | 2026-09-03T22:05:19Z |
| JSON emitted | 2026-09-03T22:07:46Z |
| Process | completed (container CPU returned to 0; restart NEVER) |
| Sample | stratified, 24 cases, 18 categories, 1 repetition |

Pretty-printed JSON exceeded Railway's 500 logs/sec replica cap.
**1478 log lines were dropped**, including official model aggregates and
all recovered Haiku rows.

## Actual spend

Official `estimated_total_cost_usd` lines were among the dropped logs.

Recovered Opus (`claude-opus-4-8`) per-case `cost_usd` values (12 of 24):

`0.01055 + 0.01357 + 0.01119 + 0.02129 + 0.01290 + 0.02143 + 0.01139 + 0.01384 + 0.01125 + 0.01055 + 0.01381 + 0.01730 = 0.16917`

That is a **lower bound for Opus only**. Haiku spend was not recovered.
Prior estimate for the full 48-attempt window was **$0.43** (cap $0.52).
Do not treat $0.169 as the full-run spend.

## Promotion gates

Official `promotion_passed` / `promotion_failures` were not recovered.

Recovered Opus case rows:

- `parse_ok=true` on every recovered row
- `cycle_rate=0`, `tenant_violation_rate=0`, `forbidden_action_rate=0` on every recovered row
- Quality misses present: `model_incomplete_valid`, `model_wrong_terminal`, `model_invalid_nongate`

Zero-gate fields that were recovered stayed at zero. Quality thresholds
needed for promotion did **not** hold on recovered Opus cases, so this
run is **not a promotion pass**. Haiku aggregates are unknown.

## Follow-up

- Runner now prints one `M9_BAKEOFF_SUMMARY` line before the full JSON.
- Staging `m9-bakeoff-runner` start command was set to idle so later
  branch pushes cannot spend again.
