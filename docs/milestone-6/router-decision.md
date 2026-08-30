# Milestone 6 router decision

Selection set: **independent validation-v3** (208 cases).
Frozen 215 was **not** used for selection.
Production `classify()` was **not** auto-changed.

**Winner (documented, not auto-promoted): `heuristic→tfidf`**

Cheapest/simple system with zero observed unsafe actions and competitive department accuracy on validation-v3. Not auto-promoted into production classify().

## Candidate metrics

| Candidate | Dept acc | Macro F1 | Null rate | LLM % | $/1k | Unsafe |
|---|---:|---:|---:|---:|---:|---:|
| heuristic | 43.3% | 0.355 | 20.7% | 0.0% | $0.00 | 0 |
| tfidf | 48.1% | 0.422 | 0.0% | 0.0% | $0.00 | 0 |
| haiku | skipped | — | — | — | — | 0 |
| heuristic→tfidf | 49.5% | 0.440 | 0.0% | 0.0% | $0.00 | 0 |
| heuristic→haiku | skipped | — | — | — | — | 0 |
| heuristic→tfidf→haiku | skipped | — | — | — | — | 0 |

## Heuristic risk / coverage

| Threshold | Handled w/o LLM | Acc on handled | Escalated | Unsafe |
|---:|---:|---:|---:|---:|
| 0.30 | 79.3% | 54.5% | 20.7% | 0 |
| 0.40 | 73.1% | 55.9% | 26.9% | 0 |
| 0.50 | 73.1% | 55.9% | 26.9% | 0 |
| 0.60 | 54.3% | 62.8% | 45.7% | 0 |
| 0.70 | 42.3% | 64.8% | 57.7% | 0 |
| 0.80 | 35.6% | 64.9% | 64.4% | 0 |

## Decision

- Keep production routing as shipped: Haiku when keyed, else heuristic.
- Bakeoff winner is evidence for a later, explicit promotion PR.
- Policy, approval, tenant, idempotency, and verification stay router-independent.

