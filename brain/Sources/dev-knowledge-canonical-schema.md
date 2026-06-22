---
type: source
source_id: dev-knowledge-canonical-schema
origin: local-repo
path: /home/user/agentnexlify/docs/dev-knowledge/canonical-schema.md
accessed: 2026-06-22
sensitivity: normal
tags: [source]
---

# Source: docs/dev-knowledge/canonical-schema.md

## What this is
Canonical database schema reference (migration #106 baseline).

## What it proves
- `leads` + `conversations` use `client_id` (FK to tenants); other tables use `tenant_id`.
  client_id fix shipped in migration 076.
- Lead `status` enum: new/visited/contacted/appointment_booked/closed/lost.
- Service interest column = `areas_of_interest`.
- Widget API key format `anx_...`; MCP keys `mcp_...`.
- Multi-tenant + RLS on every table.
- Contains older plan-price figures (free/growth/professional/enterprise) — see pricing drift.
