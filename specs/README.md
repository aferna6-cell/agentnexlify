# /specs — Law (enforce)

Binding requirements. The contract every feature MUST honor.

## Role
This folder answers: **"What MUST this feature do? What does done look like?"**

Specs are AUTHORITATIVE. If code disagrees with spec, code is wrong (or spec needs amendment via PR with rationale).

## What goes here
- Feature specs / PRDs (`<feature>_spec.md`)
- Acceptance criteria
- Success metrics (target values)
- Non-goals (what we explicitly will NOT build)
- Open questions blocking implementation
- Tenant scope, security constraints, schema invariants

## What does NOT go here
- HOW to implement it (that's `/plans/`)
- Background reading or definitions (`/docs/`)
- Verification that spec was met (`/audits/`)
- Architecture rationale (`/planning/decisions/`)

## Spec structure
Required sections in every spec:
1. **Status** — draft | in-review | approved | shipping | shipped
2. **Problem** — who hurts, what they can't do
3. **Goals** — measurable
4. **Non-Goals** — explicit defer list
5. **User Stories** — as-a / I-want / so-that
6. **Success Metrics** — baseline → target + measurement method
7. **Constraints** — tenant scope, schema invariants, performance bounds
8. **Architecture** — backend + frontend + widget + DB layer touches
9. **Data Model** — tables, columns, RLS, migration safety
10. **API Surface** — endpoints, models, contracts
11. **Security** — authN/Z, tenant isolation, webhook verification
12. **Open Questions** — owner + blocked work

See `.claude/skills/write-prd/SKILL.md` for the full template.

## AgentNexLiFy invariants every spec MUST honor
- `client_id` not `tenant_id` on leads/conversations
- `status` not `lead_stage`
- `areas_of_interest` not `service_interest`
- Widget JS byte-identical in `widget/` and `frontend/public/widget/`
- No `from __future__ import annotations` in FastAPI files
- Plan names: free, growth, professional, autopilot, enterprise (NEVER foundation/operations)

## Naming
`<feature>_spec.md` (kebab-case feature name, e.g. `lead-scoring-v2_spec.md`)

## Producer skills
- `write-prd` → `specs/<feature>_spec.md`
- `grill-me` (precursor) → resolved decisions feed into spec

## Lifecycle
- Spec status flows: draft → in-review → approved → shipping → shipped
- Shipped specs stay (historical record of what was built)
- Specs that diverged from reality → amend with rationale, do not silently retcon

## Cross-refs
- See `/STRUCTURE.md` for the 4-folder convention
- Companion: `/plans/` (how to deliver), `/audits/` (proof delivered), `/planning/decisions/` (why)
