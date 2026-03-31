# Planning Workspace
<!-- Last updated: 2026-03-31 -->

Product thinking, feature specs, architecture decisions, and phase tracking for AgentNexLiFy.

## What Happens Here

1. New feature ideas get scoped into specs with clear requirements and acceptance criteria
2. Architecture decisions get documented with trade-offs and rationale
3. Phase milestones get tracked (what's done, what's next, what's blocked)
4. Beta deployment plans get written and tracked

## Process

- **Before writing code:** write a spec in `/planning/specs/`
- **Before a significant architecture choice:** document it in `/planning/decisions/`
- **When milestones are hit:** update phase tracking status

## Naming

- Specs: `feature-name_spec.md`
- Decisions: `YYYY-MM-DD-decision-title.md`

## What Good Looks Like

- Specs have clear scope, acceptance criteria, and explicit non-goals
- Architecture decisions include alternatives considered and why they were rejected
- Phase tracking is current and honest about what's blocked

## What to Avoid

- Vague specs that don't define scope ("make the dashboard better")
- Making significant architecture decisions without documenting them
- Planning without referencing current known issues and tech debt

## Folders

- `/planning/specs` — Feature specs and PRDs
- `/planning/architecture` — System design docs, data models, integration diagrams
- `/planning/decisions` — Architecture Decision Records (ADRs)

## Current Priorities (2026-03-31)

- **Phase A:** Critical fixes — lead capture flag, dashboard stats zero bug, teaser bubble
- **Phase B–D:** Full dashboard page audit and activation
- **Self-serve onboarding wizard** — spec written (`onboarding-wizard_spec.md`)
- **Agency architecture** — white-label for marketing agencies (design needed)
- **Revenue:** Converting beta partners (MTOptions) to paying customers

## Existing Specs

- `full-dashboard-buildout_spec.md` — Full dashboard buildout plan
- `onboarding-wizard_spec.md` — Self-serve onboarding flow
