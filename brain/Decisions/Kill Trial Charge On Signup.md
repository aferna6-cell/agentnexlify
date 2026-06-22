---
type: decision
status: active
tags:
  - decision
  - pricing
source_status: source-backed
confidence: high
---

# Decision: Kill the 7-Day Trial — Charge on Signup

## Decision
Remove the 7-day checkout trial; charge immediately at signup. (#322)

## Rationale
The trial was added (#299) then reversed within ~weeks — immediate charge converts higher-intent
buyers and removes trial-abuse + dunning complexity.

## Alternatives Considered
- Keep the 7-day trial (#299) — rejected; reversed.

## Consequences
- Triggered the TermsOfService §4 rewrite now awaiting legal review (#330).
- Pairs with [[Remove Free Tier Gate Signup]].

## Related
- [[Remove Free Tier Gate Signup]] · [[2026-06-15 Plan Repricing]]

## Provenance
- [[connector-github-history]]
