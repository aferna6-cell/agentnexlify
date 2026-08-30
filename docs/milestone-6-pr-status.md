# Milestone 6 — PR / branch status (2026-08-30)

## Merged to main (production)

| PR | Summary |
|----|---------|
| #694 | Typed Agent OS action foundation |
| #695 | Gmail/send contract tests |
| #696 | Independent validation-v3 dataset + leakage tooling |
| #697 | L2 idempotency + execution data redaction |
| #699 | Unknown-send handling, pre-claim validation, claim-gated execution |
| #700 | Sales-only `send_email` behind default-OFF `SEND_EMAIL_ENABLED` |

## This milestone branch (`cursor/milestone6-completion-b6dd`)

Integrates from research **selectively** (not wholesale #693):

- Production action evaluation harness (`agent-service/evals/`)
- Semantic decision pipeline (`_intent.ts`, `_resolve.ts`, `communication_actions.ts`)
- Communication capability config (`communication_capabilities.ts`)
- ML router bakeoff tooling (`ml/routing/milestone6.py`, TF-IDF trainer)
- Router decision + Gmail proof documentation

## Reference / research — do not merge wholesale

| PR / branch | Status | Notes |
|-------------|--------|-------|
| #693 (`claude/agent-action-executor-v8ntvk`) | **Reference** | Source for eval harness + semantics; decomposed into this PR |
| #698–#703 | **Measurement experiments** | Evidence only; superseded by validation-v3 + this milestone's frozen run |

## Superseded / ambiguous measurement PRs

Older measurement PRs (#698–#702) should be **closed or labeled `superseded`** once this PR merges, with a comment pointing to:

- `docs/milestone-6-router-decision.md`
- `agent-service/evals/results/action-eval-action-eval-v1-2026-08-30.json`
- `ml/routing/artifacts/milestone6-validation-v3.json`

#703 (if present as latest measurement successor) remains the reference for methodology comparison only.

## Post-merge clarification

Merged PRs #694–#700 descriptions that still say "do not merge" are stale — those changes **are** on main. This doc is the visible post-merge clarification.
