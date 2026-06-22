---
type: source
source_id: docs-managed-agents
origin: local-repo
path: /home/user/agentnexlify/docs/managed-agents.md
accessed: 2026-06-22
sensitivity: normal
tags: [source]
---

# Source: docs/managed-agents.md

## What this is
Operations doc for the Anthropic Claude Managed Agents integration.

## What it proves
- 8 server-managed agents: lead_qualifier, document_drafter, codebase_reviewer, support_agent,
  structured_extractor, deep_researcher, field_monitor, data_analyst. Live-validated 2026-04-09/10.
- Provisioning flow: edit `config/managed_agents.yaml` → `provision.py --dry-run` →
  `provision.py` → IDs to `.env.managed_agents` → deploy env to Railway.
