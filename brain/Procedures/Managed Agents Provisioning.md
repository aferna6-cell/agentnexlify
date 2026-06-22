---
type: procedure
name: "Managed Agents Provisioning"
tags:
  - procedure
  - ai
source_status: source-backed
sensitivity: normal
last_verified: 2026-06-22
---

# Managed Agents Provisioning

## When to use
Adding/updating an Anthropic [[Claude Managed Agents]] definition.

## Steps
1. Edit `config/managed_agents.yaml`.
2. `provision.py --dry-run` (review).
3. `provision.py` (create/update on Anthropic).
4. Write returned IDs to `.env.managed_agents`.
5. Deploy env vars to Railway.

## Related
- [[Claude Managed Agents]] · [[Anthropic]] · [[Production Deploy]]

## Provenance
- [[docs-managed-agents]]
