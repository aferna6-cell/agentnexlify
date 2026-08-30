# Frozen 215 — post-selection report

Run after router selection was frozen. Labels were not edited.
Engine: offline heuristic classifier + local composer (`ANTHROPIC_API_KEY` unset).
Commit: `5f5493f9`. Command: `cd agent-service && npm run eval:actions -- --report --gate`.

| Metric | Value |
|---|---|
| Cases | 215 |
| Department accuracy | 80.0% |
| Department top-2 | 86.5% |
| Department macro F1 | 0.6929 |
| Behavior accuracy | 65.1% |
| Tool accuracy | 23.8% (84 scored) |
| Approval accuracy | 100.0% (20 scored) |
| Param exact match | 23.4% |
| Missed-action rate | 70.2% |
| Routing null/clarify | 26.1% |
| **Unsafe actions** | **0** |
| Latency | median 0.17ms, p95 1.23ms, total 100ms |
| Cost | $0 (offline) |

Safety gate: **PASS** (`--gate` exits 0).

## How to read tool / missed-action

Most “action” cases in the frozen set expect `send_email`. Production
`SEND_EMAIL_ENABLED` is default OFF, so the engine parks those as
`draft_only` / clarification instead of proposing a live send. That is
**fail-closed**, not an unsafe execution. Approval accuracy on scored
proposals is 100%. Unsafe count is 0.

Do not tune keywords against this file to lift tool accuracy.

Full machine report (gitignored): `agent-service/evals/results/action-eval-action-eval-v1-2026-08-30.json`.
