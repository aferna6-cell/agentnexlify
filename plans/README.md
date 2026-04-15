# /plans — Intent (plan)

Sequenced intent. What we INTEND to do, in what order, with what gates.

## Role
This folder answers: **"What's the next step on X? In what order? With what dependencies?"**

## What goes here
- Implementation plans (`<feature>_plan.md`) — phased work derived from a spec
- Refactor plans (`refactor-<scope>_plan.md`)
- Rollout plans (`rollout-<feature>_plan.md`)
- Migration plans (`migration-<from>-to-<to>_plan.md`)
- Sprint plans (`sprint-YYYY-MM-DD_plan.md`)

## What does NOT go here
- The spec itself (binding requirements live in `/specs/`)
- Verification of completed phases (those go in `/audits/`)
- Architectural background reading (`/docs/`)
- Decision records (`/planning/decisions/` for ADRs)

## Plan structure
Each plan derived from a spec. Each phase ships a working vertical slice:
1. Tracer bullet (smallest user-visible win)
2. Edge cases
3. Admin/internal views
4. Metrics + polish
5. GA + flag removal

See `.claude/skills/prd-to-plan/SKILL.md` for the methodology.

## Naming
`<feature>_plan.md` matching the spec name (e.g. `onboarding-wizard_spec.md` → `onboarding-wizard_plan.md`)

## Producer skills
- `prd-to-plan` → `plans/<feature>_plan.md`
- `request-refactor-plan` → `plans/refactor-<scope>_plan.md`

## Lifecycle
- Plans go stale when phases ship — update `## Status` per phase
- When all phases shipped → archive to `plans/archive/<feature>_plan.md` or delete
- Plan that no longer matches reality → DELETE, do not let stale plans rot

## Cross-refs
- See `/STRUCTURE.md` for the 4-folder convention
- Companion: `/specs/` (source of truth), `/audits/` (verification of done phases)
