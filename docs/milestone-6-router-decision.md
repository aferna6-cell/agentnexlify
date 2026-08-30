# Milestone 6 router decision

Selection set: **validation-v3** (n=208, independent, leakage-checked).
Frozen 215 was **not** used for selection.

`classify()` is **unchanged**. A bakeoff win does not auto-promote.

The original validation-v3 file still says `not_for_model_selection: true`
("not yet"). Milestone 6 explicitly authorizes this split as the selection
set. That supersedes the authoring-time note. The frozen 215 remains
`not_for_model_selection`.

## Candidates

| Candidate | Dept acc (incl. acceptable) | Exact acc | Macro F1 | Null rate | LLM esc. | Cost / 1k | Latency / req |
|---|---|---|---|---|---|---|---|
| heuristic (shipped offline) | **43.3%** | 37.0% | 0.389 | 20.7% | 0% | $0 | 1.5 ms |
| TF-IDF | **51.9%** | 45.2% | 0.448 | 0.0% | 0% | $0 | 0.03 ms |
| heuristic → TF-IDF (score &lt; 3) | **51.4%** | 44.7% | 0.453 | 0.0% | 0% | $0 | 1.5 ms |
| Haiku | *not measured* | — | — | — | 100% | ~$1.10 est. | — |
| heuristic → Haiku | *not measured* | — | — | — | — | — | — |
| heuristic → TF-IDF → Haiku | *not measured* | — | — | — | — | — | — |

Official harness (`npm run eval:routing:v3`) matches heuristic department
accuracy at **43.3%** (top-2 **53.4%**). Behavior / tool / approval are
null on this split — it has no `SharedContext`. Downstream numbers live
on the frozen 215 run *after* this freeze.

Unsafe actions on every measured candidate: **0** (routing-only; no
executor, no Gmail).

## Risk / coverage (heuristic confidence floor)

| Min heuristic score | Handled without LLM | Acc on handled | Escalated | Unsafe |
|---|---|---|---|---|
| 0 | 79.3% | 54.5% | 20.7% | 0 |
| 2 | 73.1% | 55.9% | 26.9% | 0 |
| 3 | 54.3% | 62.8% | 45.7% | 0 |
| 4 | 51.0% | 63.2% | 49.0% | 0 |
| 5 | 42.3% | 64.8% | 57.7% | 0 |
| 6 | 36.1% | 65.3% | 63.9% | 0 |
| 8 | 35.6% | 64.9% | 64.4% | 0 |
| 10 | 24.0% | 64.0% | 76.0% | 0 |

Raising the floor improves handled accuracy into the low 60s and dumps
nearly half the traffic. That is a coverage trade, not a production
router.

## Decision

**Measured accuracy leader:** TF-IDF (51.9% vs 43.3% heuristic).

**Production recommendation:** **keep the shipped heuristic.**

Reasons:

1. The goal is the cheapest/simplest system with strong downstream
   correctness and zero unsafe actions — not the highest routing number.
2. 52% department accuracy is **not** strong enough to replace a
   transparent, already-shipped offline path.
3. The cascade is statistically tied with standalone TF-IDF and adds a
   second system without a safety gain.
4. Haiku (the production `classify()` first hop when a key is present)
   was not measured here — `ANTHROPIC_API_KEY` is absent. Estimated
   ~$1.10 / 1k routes. Do not invent Haiku numbers.
5. Policy, approval, risk, tenant, idempotency, and verification stay
   router-independent. Promoting a router must not touch them.
6. **`winner_auto_promoted` is false.** `classify()` still prefers Haiku
   when keyed, else heuristic. No `setRoutingProvider`. No `"ml"`
   classifier union.

Promote TF-IDF or a cascade only after an explicit owner decision and a
Haiku-inclusive re-measure.

## Artifact

`ml/routing/artifacts/bakeoff-validation-v3.json`

## Frozen 215

Run only after this document exists. Results are recorded separately and
must not be used to pick a different winner.
