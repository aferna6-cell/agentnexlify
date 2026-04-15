---
name: write-prd
description: Generate a Product Requirements Document via interactive interview, codebase exploration, and module design. Output saved to specs/<feature>_spec.md. Load when user says "write a PRD", "draft a spec", "spec this feature", "PRD for X".
origin: https://github.com/mattpocock/skills/tree/main/write-a-prd
version: 1.0.0
triggers:
  - write a PRD
  - write PRD for
  - draft a spec
  - spec this feature
  - PRD for
  - product requirements
---

# Write PRD — Spec Authoring

Interview → explore → design → file. Output: `specs/<feature-name>_spec.md`.

## When to Use
- New feature requested without spec
- Existing rough notes that need formalization
- Pre-implementation gate for compound-engineering pipeline
- Multi-stakeholder feature (tenant + admin + widget)

## When NOT to Use
- One-file bug fix
- Pure infra change (use `planning/decisions/` ADR instead)
- Spec already exists (extend, don't rewrite)
- User wants direct execution

## Process
1. **Read context** — `CLAUDE.md`, `planning/CONTEXT.md`, existing specs in `specs/`
2. **Run grill-me skill** if scope unclear — get resolved decisions
3. **Explore codebase** — find related routers/pages/migrations to reference
4. **Draft PRD** using template below
5. **Write to** `specs/<kebab-feature>_spec.md`
6. **Hand off** to `prd-to-plan` for phased plan or `prd-to-issues` for GH backlog

## PRD Template
```markdown
# [Feature Name] — Spec

**Status:** draft | in-review | approved | shipping | shipped
**Owner:** <user>
**Created:** YYYY-MM-DD
**Tenant scope:** all | gated | single
**Priority:** P0 | P1 | P2

## Problem
<2-3 sentences. Who hurts. What they can't do today.>

## Goals
- Goal 1 (measurable)
- Goal 2

## Non-Goals
- What we explicitly will NOT build
- Adjacent features deferred

## User Stories
- As a <role>, I want <action>, so that <outcome>.
- Edge cases: <list>

## Success Metrics
- Metric: <baseline → target>
- How we measure: <SQL query / event / dashboard>

## Constraints
- Multi-tenant: every query carries `client_id`
- Schema invariants: `client_id` not `tenant_id`, `status` not `lead_stage`, `areas_of_interest` not `service_interest`
- No `from __future__ import annotations` in FastAPI files
- Widget JS byte-identical in `widget/` AND `frontend/public/widget/`
- Plan names: free, growth, professional, autopilot, enterprise
- <feature-specific limits>

## Architecture
- Backend changes: <routers, services, migrations>
- Frontend changes: <pages, components, API clients>
- Widget changes: <events, UI, knowledge base>
- DB changes: <migration NNN_name.sql>

## Data Model
- New tables/columns
- New indexes
- RLS policies
- Migration safety (additive vs destructive)

## API Surface
- New endpoints (method + path + auth)
- Pydantic models (request/response)
- Webhook contracts

## Security
- AuthN/AuthZ
- Tenant isolation verification
- Webhook signature checks
- PII handling

## Open Questions
- <question> — owner: <user> — blocks: <work>

## Out-of-Scope (defer)
- <feature> — defer to <next sprint / not planned>
```

## Naming
- File: `specs/<kebab-name>_spec.md`
- Example: `specs/lead-scoring-v2_spec.md`

## Cross-refs
- Companion skills: `grill-me` (run first), `prd-to-plan`, `prd-to-issues`
- `CLAUDE.md` — workflows section + naming conventions
- `.claude/skills/feature-build/SKILL.md` — implementation harness
- `PROMPTLIBRARY.md` — BUILD New API Endpoint, BUILD New Dashboard Page prompts
