---
type: product
name: "Claude Managed Agents"
aliases:
  - "Managed Agents"
tags:
  - product
  - integration
source_status: source-backed
sensitivity: normal
last_verified: 2026-06-22
---

# Claude Managed Agents

## Summary
AgentNexLiFy's integration with Anthropic's server-managed agents runtime ([[Anthropic]]).
Eight managed agents back product features; live-validated 2026-04-09/10.

## The 8 agents
lead_qualifier · document_drafter · codebase_reviewer · support_agent · structured_extractor ·
deep_researcher · field_monitor · data_analyst. Source: [[docs-managed-agents]]

## Provisioning
- Edit `config/managed_agents.yaml` → `provision.py --dry-run` → `provision.py` → IDs to
  `.env.managed_agents` → deploy env to Railway. See [[Managed Agents Provisioning]].

## Relationship to dev-time agents
- Distinct from the 57 Claude Code dev agents in `.claude/agents/`. These are product-runtime,
  user-facing. Uses the [[Advisor-Executor Pattern]] in `advisor_executor.py`.

## Related
- [[Agent OS]] · [[Anthropic]] · [[Claude Model Routing]]

## Provenance
- [[docs-managed-agents]]
