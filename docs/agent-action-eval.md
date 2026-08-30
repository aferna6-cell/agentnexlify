# Agent action evaluation harness

Measures the real decision path:

```
request → classifier/router → department → intent → action resolution
  → tool proposal → policy → approval behavior → execution state
```

## Commands

```bash
cd agent-service
npm test                 # includes evals/safety-gate.test.ts
npm run eval:actions     # full frozen 215 report
npm run eval:actions:gate
```

Frozen labels live in `evals/datasets/action-eval-v1.json`. Do not edit them.
The harness never sends mail: `send_email` is data-plane-only and no mailbox
port is attached.

## Metrics

Department accuracy, top-2, behavior, tool, approval, parameter extraction,
missed-action rate, unsafe-action count, routing null/clarification rate,
latency, estimated model cost (0 when offline).
