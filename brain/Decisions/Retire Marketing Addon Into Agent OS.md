---
type: decision
status: active
tags:
  - decision
  - product
source_status: source-backed
confidence: medium
---

# Decision: Retire the Marketing Add-on, Fold into Agent OS

## Decision
Stop pursuing the standalone $49.99/mo Marketing Suite add-on; fold marketing capability into
[[Agent OS]]. (#228)

## Rationale
A separate add-on SKU added billing/gating complexity; the value belongs inside the
"AI Workforce" agent surface.

## Consequences
- The `MARKETING_ADDON` spec (migration 102) is **stale/abandoned** — confirmed by a separate
  testing session (2026-06-22): only the migration exists, no implementation; owner directed it
  be disregarded. See [[docs-marketing-addon]].

## Related
- [[Agent OS As Product Spine]] · [[Agent OS]]

## Provenance
- [[connector-github-history]] · [[docs-marketing-addon]]
