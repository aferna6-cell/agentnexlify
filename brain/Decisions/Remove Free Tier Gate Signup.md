---
type: decision
status: active
tags:
  - decision
  - pricing
source_status: source-backed
confidence: high
---

# Decision: Remove Free Tier, Gate Signup Behind Payment

## Decision
Eliminate the free signup path. Require a valid payment method at signup; grandfather existing
tenants. (#291, #298)

## Rationale
Reconcile the funnel to the paid two-plan model ([[2026-06-15 Plan Repricing]]); a free tier
diluted activation and revenue.

## Consequences
- `free` survives only as an internal lapsed state, never sold.
- Raises the bar on first-value (drove onboarding/demo investment — instant KB, /demo sandbox).

## Related
- [[2026-06-15 Plan Repricing]] · [[Kill Trial Charge On Signup]] · [[Convert Beta Tenants to Paid]]

## Provenance
- [[connector-github-history]]
