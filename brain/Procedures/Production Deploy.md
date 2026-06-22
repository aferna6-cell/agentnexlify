---
type: procedure
name: "Production Deploy"
tags:
  - procedure
  - ops
source_status: source-backed
sensitivity: normal
last_verified: 2026-06-22
---

# Production Deploy

## When to use
Shipping to production (Railway backend + Vercel frontend).

## Steps
1. Run backend tests (Python 3.12 via `.venv312`).
2. Run frontend tests + build.
3. Apply database migrations **first**.
4. Deploy backend; confirm `/healthz`.
5. Deploy frontend after backend is healthy.
6. Watch logs for 15 minutes.

## Related
- [[Database Migration Workflow]] · [[Local Release Gate]] · [[Vendor Stack]]

## Provenance
- [[docs-production-runbook]]
