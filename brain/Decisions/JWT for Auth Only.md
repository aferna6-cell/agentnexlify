---
type: decision
status: active
tags:
  - decision
  - architecture
source_status: source-backed
confidence: high
---

# Decision: JWT for Auth Only; Display Data from Live API

## Decision
Use JWT strictly for authentication. Always fetch display data (plan, business fields) from the
live API, never from JWT claims.

## Rationale
JWT claims do not refresh on plan change, so trusting them for display causes stale/incorrect
plan gating in the [[Dashboard]].

## Consequences
- Frontend reads plan/entitlements from API responses, not the token.

## Related
- [[Dashboard]] · [[2026-06-15 Plan Repricing]]

## Provenance
- [[dev-knowledge-architecture-decisions]]
