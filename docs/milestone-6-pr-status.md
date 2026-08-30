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

## Merged Milestone 6 completion

| PR | Summary |
|----|---------|
| #705 | Production eval harness, semantic pipeline, v3 bakeoff, router decision. On main as of 2026-08-30. |

A parallel research branch (`cursor/m6-decision-intelligence-ba5d`) extracted the same themes independently and is **not** a second production merge. Keep it as a reference; do not merge it wholesale onto #705.

## Reference / research — do not merge wholesale

| PR / branch | Status | Notes |
|-------------|--------|-------|
| #693 (`claude/agent-action-executor-v8ntvk`) | **OPEN — reference only** | Source for eval harness + semantics. Decomposed into #694–#700 and #705. Do not merge wholesale. |
| #698 | **CLOSED** | Measurement research. Superseded. |
| #701 | **CLOSED** | Measurement research. Superseded. |
| #702 | **CLOSED** | Measurement research. Superseded. |
| #703 | **OPEN draft — evidence only** | Claim-then-execute methodology. Not a production merge. |
| `cursor/m6-decision-intelligence-ba5d` | **Reference** | Parallel M6 extraction. Do not merge over #705. |

## Post-merge clarification

Merged PRs #694, #699, and #700 may still say "do not merge" in their original bodies. That draft language is stale — those changes **are** on main. This doc is the visible post-merge clarification.
