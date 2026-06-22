---
type: procedure
name: "Local Release Gate"
tags:
  - procedure
  - quality
source_status: source-backed
sensitivity: normal
last_verified: 2026-06-22
---

# Local Release Gate

## When to use
Before pushing / opening a PR.

## Command
`npm run check:local-release` — runs agent-system checks + frontend build + focused backend
tests + frontend tests.

## Notes
- A separate full-suite test session (2026-06-22) confirmed: root pytest 1084 pass, backend
  pytest 1088 pass, frontend vitest 140 pass, agent-service 25 pass, all builds clean.

## Related
- [[Production Deploy]] · [[Daily Skills Gate]]

## Provenance
- [[repo-agentnexlify-readme]]
