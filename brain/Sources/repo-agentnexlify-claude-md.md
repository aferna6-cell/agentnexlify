---
type: source
source_id: repo-agentnexlify-claude-md
origin: local-repo
path: /home/user/agentnexlify/CLAUDE.md
accessed: 2026-06-22
sensitivity: normal
tags:
  - source
---

# Source: agentnexlify/CLAUDE.md

## What this is
The project onboarding + rules file for the AgentNexLiFy repo. Curated source of truth for
product facts (what it is, tech stack, architecture), plan names/pricing, critical schema
invariants, the agent/skill roster, and the 12 user engineering rules.

## What it proves
- Product definition + architecture (widget → FastAPI → Claude → Supabase).
- Plan names + pricing (repriced 2026-06-15): `chatbot` $19.99/mo, `agent_os` $99.99/mo;
  `free` internal lapsed state; legacy `growth/autopilot/professional/enterprise`;
  retired `foundation/operations`.
- Critical invariants: `client_id` not `tenant_id`; `status` not `lead_stage`;
  `areas_of_interest` not `service_interest`; widget byte-identical; no
  `from __future__ import annotations` in FastAPI files; schema changes via numbered migrations.
- Competitive positioning (GoHighLevel #1 competitor; widget-first differentiation).

## Notes
Canonical, frequently-updated. Last audit noted in-file 2026-04-15. High trust.
