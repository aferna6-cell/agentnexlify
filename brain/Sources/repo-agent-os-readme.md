---
type: source
source_id: repo-agent-os-readme
origin: local-repo
path: /home/user/Agent-Nexlify-OS/README.md
accessed: 2026-06-22
sensitivity: normal
tags:
  - source
---

# Source: Agent-Nexlify-OS/README.md

## What this is
README for the Agent OS product — the conversational orchestrator surface for AgentNexLiFy,
built as a standalone demoable product.

## What it proves
- Agent OS: a small-business owner talks to one **orchestrator** in plain English; it routes
  to a best-fit **worker agent**, which runs, streams a reasoning trace, and produces a draft
  for approval.
- **Merged into production 2026-06-09**: vendored into
  `agentnexlify/agent-service/src/agent-os/` and made the only agent path (agentnexlify PRs
  #203–#208, #219). Canonical engine now lives in the `agentnexlify` repo; this repo remains
  spec + offline demo.
- **v2 model**: owner talks to 8 department-head agents (Sales, Marketing, Customer Service,
  Operations, Invoicing & Collections, Accounting & Finance, Customer Data & Administration,
  People Management); each bundles former specialist workers as internal skills.
- Live demo: https://agent-nexlify-os.vercel.app (demo bypass as "Maya"; seeded "Sunset Auto
  Care" data).

## Notes
High trust. Note the merge banner — make engine changes in `agentnexlify`, not this repo.
