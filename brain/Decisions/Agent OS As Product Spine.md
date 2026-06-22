---
type: decision
status: active
tags:
  - decision
  - architecture
  - product
source_status: source-backed
confidence: high
---

# Decision: Make Agent OS the Product Spine

## Decision
Adopt the [[Agent OS]] demo framework as the orchestration core (#203), cut over to an
engine-only architecture (#219), and **retire 18 standalone dashboard pages** in favor of an
agent-first UI (#222, #236).

## Rationale
One conversational orchestrator + department-head agents is the product's differentiation and
simplifies the surface area vs a sprawling page-per-feature dashboard.

## Consequences
- Agent OS is gated to the `agent_os` ("AI Workforce") plan (#323).
- The marketing add-on was folded into Agent OS (#228) — see [[Retire Marketing Addon Into Agent OS]].
- Drove new agents: Outbound Outreach (#318), Conversation Insights (#312/#315/#316).

## Related
- [[Agent OS]] · [[2026-06-09 Agent OS Production Merge]] · [[Retire Marketing Addon Into Agent OS]]

## Provenance
- [[connector-github-history]] · [[repo-agent-os-readme]]
