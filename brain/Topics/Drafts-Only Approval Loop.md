---
type: topic
name: "Drafts-Only Approval Loop"
tags:
  - topic
  - agent-design
source_status: source-backed
sensitivity: normal
last_verified: 2026-06-22
---

# Drafts-Only Approval Loop

## Definition
[[Agent OS]] worker agents produce **drafts for owner approval**, not auto-sends. Each draft
comes with an honest reasoning trace. `never_auto_send` is enforced for sensitive actions
(complaints, payments). This is the core trust mechanic of the product.

## Why it matters
- It is the safety boundary that lets small-business owners trust autonomous agents.
- Mirrors this vault's own rule: agents must get explicit approval before external mutations.

## Related
- [[Agent OS]] · [[Claude Managed Agents]] · [[Advisor-Executor Pattern]]

## Provenance
- [[repo-agent-os-readme]]
