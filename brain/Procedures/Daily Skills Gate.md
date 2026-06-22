---
type: procedure
name: "Daily Skills Gate"
tags:
  - procedure
  - workflow
source_status: source-backed
sensitivity: normal
last_verified: 2026-06-22
---

# Daily Skills Gate

## When to use
The mandated development loop for non-trivial feature work.

## Sequence
WRITE-PRD → GRILL-ME (40+ clarifying questions, zero ambiguity) → PRD-TO-ISSUES → TDD
(failing tests first) → build (compound-engineering pipeline) → Monday: IMPROVE-ARCHITECTURE.

## Why
Encodes the builder's "plan first, tests first, keep the foundation clean" discipline — see
[[User Engineering Rules]].

## Related
- [[User Engineering Rules]] · [[Local Release Gate]]

## Provenance
- [[repo-agentnexlify-claude-md]] (daily-skills rule)
