# Milestone 6 — Production Decision Intelligence

Status: **HOLD**
Evaluation branch: `cursor/milestone-6-decision-intelligence-888d`

This is the canonical Milestone 6 evidence record. Historical results in
`agent-decision-pipeline-error-analysis.md`, `ml-router-benchmark.md`, and
`ml-router-calibration.md` came from research PR #693 and are not production
claims.

## Production decision

Keep the current production router unchanged. The measured offline winner is
the heuristic → TF-IDF cascade because it has the strongest downstream behavior
accuracy and lowest null/clarification rate among the credential-free
candidates. It is **not** promoted: validation-v3 Haiku results are missing, so
the required six-way comparison is incomplete.

`SEND_EMAIL_ENABLED` remains default OFF. No deploy configuration changed.

## Reproducibility

| Dataset | Use | Cases | SHA-256 |
|---|---|---:|---|
| `validation-v3.json` | model selection | 208 | `f7cef8630f91091c4419fb2ed03220b5d79d61783eed9921afe574413b3875b9` |
| `action-eval-v1.json` | frozen final benchmark | 215 | `0997c4de4a82afba3bcf3befa25c2c7b3fc898c14da1960d8bbe9856b849d6b0` |
| `train-v1.jsonl` | TF-IDF fitting/CV | 1,216 | `79cb88fa7b97706d0ffe3295065677142314779bc93d55d0d0c3372dc3ac6820` |

Leakage checks report zero train↔validation, train↔frozen, and
validation↔frozen collisions. TF-IDF hyperparameters were selected by
five-fold `StratifiedGroupKFold` on training templates, not on validation-v3.

## Validation-v3 routing results

| Candidate | Department | Macro F1 | Top-2 | LLM escalation | p95 | Cost/1k |
|---|---:|---:|---:|---:|---:|---:|
| Heuristic | 36.5% | 0.3927 | 47.1% | 0% | 0.16 ms | $0 |
| TF-IDF | **51.9%** | **0.5114** | **71.2%** | 0% | 1.55 ms | $0 |
| Haiku | not measured | — | — | 100% | — | est. $1.109 |
| Heuristic → TF-IDF | 48.1% | — | — | 0% | 1.46 ms | $0 |
| Heuristic → Haiku | not measured | — | — | 45.7% | — | est. $0.507 |
| Heuristic → TF-IDF → Haiku | not measured | — | — | 25.5% | — | est. $0.283 |

The Haiku-containing rows are cost/escalation estimates, not accuracy
measurements. The runner fails to substitute heuristic answers for missing
Haiku output.

## Validation-v3 downstream results

Validation-v3 contains routing and behavior labels, but no action/tool gold
labels. Tool and approval accuracy are therefore correctly reported as `N/A`
rather than invented.

| Candidate | Department | Behavior | Null/clarify | Tool | Unsafe population |
|---|---:|---:|---:|---:|---:|
| Heuristic | 33.2% | 30.3% | 47.6% | N/A | 0 labelled |
| TF-IDF | **51.4%** | 41.3% | 18.8% | N/A | 0 labelled |
| Heuristic → TF-IDF | 50.0% | **44.2%** | **13.0%** | N/A | 0 labelled |

These values replay the full classifier → department → semantic intent →
action resolution → policy path with offline composers and in-memory ports.

## Safety

The deterministic detector independently checks:

- `must_not_execute` activity;
- Level 2+ execution without a persisted approval actor and timestamp;
- mutation when draft/clarify/decline was required;
- execution without a complete audit record;
- cross-tenant execution;
- execution after rejection;
- duplicate external execution by attempts or idempotency key.

Request origin is part of the authorization boundary: inbound customer text and
automated/system prompts may be classified and drafted, but only authenticated
owner text can authorize a mutation or external-action proposal.

Synthetic negative controls force every unsafe class and prove the detector
fails closed. Runtime tests also cover cross-tenant approval, rejection replay,
claim-before-execute, unknown send outcomes, Message-ID adoption, and
double-approval idempotency.

The frozen 215 safety count is intentionally not reported yet. Selection cannot
freeze until Haiku is measured on validation-v3, and the frozen benchmark may
only run after that point.

## Gmail proof boundary

The controlled path is prepared and fake-boundary verified:

1. `send_email` proposal is Level 2 and parks at `pending_approval`.
2. Gmail remains untouched before the owner claim.
3. Claim atomically writes `status=running`, `approval_state=approved`, and
   `approved_by`.
4. One send uses a deterministic RFC 5322 Message-ID.
5. The message is read back and recipient, subject, and Message-ID must match.
6. A match reaches `status=succeeded`, `verification_state=passed`.
7. A mismatch reaches `verification_failed`, never a false success.
8. Replay/redrive searches by Message-ID and adopts the existing message.
9. A failed Message-ID lookup is an unknown outcome and never falls through to
   another send attempt.

No real external send occurred. A real proof requires an owner-approved test
tenant, connected test Gmail account, and harmless recipient. Production
enablement is not part of that proof.

## PR state

- #694, #695, #696, #697, #699, #700: merged production foundations.
- #693: deferred research/reference; never merge wholesale.
- #698, #701, #702: closed/deferred measurement predecessors.
- #703: current measurement reference, marked `human-action-required`; keep
  until the successor Milestone 6 integration is reviewed.
- #700: description corrected post-merge to remove stale “do not merge” wording.

## HOLD reasons

1. No `ANTHROPIC_API_KEY` is available to measure Haiku and the two
   Haiku-containing cascades on validation-v3.
2. Without complete validation selection, running the frozen 215 benchmark
   would violate the pre-registered evaluation order.
3. A real Gmail send requires explicit owner authorization and controlled test
   credentials.

Until those three boundaries are cleared:

**MILESTONE 6 HOLD**
