# Milestone 6 — Router / cascade decision

**Date:** 2026-08-30  
**Selection split:** `validation-v3` (208 cases, independent, leakage-checked)  
**Frozen measurement split:** `action-eval-v1` (215 cases) — used only after selection

## Candidates evaluated

| # | Architecture | validation-v3 dept acc | macro F1 | top-2 | clarify/null | LLM escalations / 1k | p95 latency |
|---|--------------|------------------------|----------|-------|--------------|----------------------|-------------|
| 1 | Heuristic (shipped offline) | 36.5% | 0.393 | 47.1% | 20.7% (orchestrator) | 0 | 0.14 ms |
| 2 | TF-IDF only | 51.9% | 0.511 | 71.2% | 0% | 0 | 1.05 ms |
| 3 | Haiku (production when keyed) | *not measured in CI* | — | — | — | 1000 | ~$1.11 / 1k |
| 4 | Heuristic → TF-IDF (C) | 48.1% | — | — | 0% | 0 | 1.07 ms |
| 5 | Heuristic → Haiku (E) | *escalation 45.7%* | — | — | — | 457 / 1k | unmeasured w/o key |
| 6 | Heuristic → TF-IDF → Haiku (F) | *escalation 25.5%* | — | — | — | 255 / 1k | unmeasured w/o key |
| 7 | Heuristic → TF-IDF → ask owner (G) | 36.5% | — | 64.9% cov | 35.1% | 0 | 1.07 ms |

Artifact: `ml/routing/artifacts/milestone6-validation-v3.json`

Embeddings were **not** retained — no competitive artifact on this branch without heavy deps; routing-only gain did not justify the operational surface.

## Downstream action benchmark (frozen 215, offline heuristic + semantic pipeline)

Run after router selection freeze — **not** used to tune routers.

| Metric | Result |
|--------|--------|
| Department accuracy | 80.5% (top-2 83.3%) |
| Behavior accuracy | 80.0% |
| Tool accuracy | 66.7% |
| Approval accuracy | 100.0% |
| **Unsafe actions** | **0** |
| Missed-action rate | 29.8% |

Artifact: `agent-service/evals/results/action-eval-action-eval-v1-2026-08-30.json`

## Risk / coverage (architecture G, abstention arm)

At calibrated TF-IDF abstention threshold, ~35% of validation-v3 cases would route to owner clarification rather than a department guess. Accuracy on handled cases trades off against coverage — see `abstention_threshold_sweep` in the milestone6 artifact.

Low-evidence region: 95/208 cases (45.7%); TF-IDF accuracy there 41.0% vs heuristic 15.8%.

## Decision

**Production routing remains: heuristic (+ semantic intent/subject scoring) with Haiku when `ANTHROPIC_API_KEY` is present.**

Rationale:

1. **Zero unsafe actions** on the frozen action benchmark with the shipped path — the north-star constraint.
2. TF-IDF improves **routing-only** accuracy on validation-v3 (+15.4 pp) but **does not** improve the heuristic→TF-IDF cascade end-to-end (48.1% < 51.9% TF-IDF-only; cascade adds complexity without downstream proof).
3. Haiku is already the production classifier when keyed; adding TF-IDF as a middle tier increases deploy surface (artifact versioning, calibration, drift) without a demonstrated gain on **behavior** or **tool** accuracy.
4. LLM escalation cost ($1.11/1k) is acceptable for production when keyed; offline/heuristic remains the CI and eval default.

**Do not auto-promote TF-IDF or cascades.** A future `ML_ROUTING_ENABLED` feature flag may host architecture C for A/B measurement once downstream action eval shows improvement.

## Confidence thresholds (if TF-IDF flag enabled later)

| Threshold | % handled w/o LLM | Notes |
|-----------|-------------------|-------|
| Heuristic evidence floor (MIN_BUSINESS_EVIDENCE) | ~54% | Escalates weak heuristic to next stage |
| TF-IDF calibrated abstention (G) | ~65% coverage | 35% owner clarification |
| TF-IDF → LLM (F) | ~74% w/o LLM | 25.5% LLM escalation rate |

## Reproduction

```bash
python3 ml/routing/train_tfidf.py
python3 ml/routing/milestone6.py --split validation --validation-version v3
cd agent-service && npm run eval:actions -- --report
cd agent-service && npm run eval:actions:gate
```
