---
name: agentnexlify-schema-guard
description: "Protect live schema and API conventions in AgentNexLiFy. Use when editing backend routes, services, migrations, Supabase queries, or any code that reads/writes tenant, lead, conversation, billing, or automation data."
version: 1.0.0
origin: codex
triggers: ["schema guard", "check the schema", "verify columns", "before writing a query"]
depends_on: []
---

# AgentNexLiFy Schema Guard

This repo has active schema drift. Verify the live pattern before changing queries.

## When NOT to Use
- Do not use for purely algorithmic changes that don't touch database reads/writes.
- Do not use for frontend-only CSS/style changes with no data layer impact.

## Mandatory invariants
- Auth and JWT claims use `tenant_id`.
- The `leads` table still uses `client_id` for tenant linkage.
- Lead stage is stored in `status`, not `lead_stage`.
- Current plan names are `free`, `growth`, `professional`, `enterprise`.
- In FastAPI router files, do not add `from __future__ import annotations`.

## Conversation and widget data
- Treat `chat_messages` as the active message-history source.
- Treat `backend/services/conversation.py` as a stale subsystem unless the task explicitly revives JSONB-backed conversations.
- Widget auth is based on `widget_configs.api_key`.

## Before editing
- Read the relevant router and its direct Supabase queries.
- Check the matching migration files in `migrations/`.
- Search for both `tenant_id` and `client_id` when touching lead or appointment flows.
- Search for both old and current plan names when touching billing or tier gating.

## Refactor guidance
- Prefer reusing `backend.routers.auth._get_current_tenant` patterns over creating more auth helper variants.
- Do not trust comments alone when they mention “live schema”; confirm against the current query pattern and migration history.
- Keep Pydantic schemas aligned with the actual columns the router reads or writes.

## Smell list
- New code querying `leads.tenant_id`
- New code writing `lead_stage`
- New code reviving `conversations.messages` without an explicit schema change
- New plan labels or mixed legacy/current plan names in the same flow
