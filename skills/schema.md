# Skill Schema

All generated skills in `skills/generated/` must follow this structure.

## Required Fields
- `name`
- `purpose`
- `when_to_use`
- `inputs`
- `workflow_steps`
- `constraints`
- `examples`

## Required Format
- Store each skill in its own directory under `skills/generated/<skill-slug>/SKILL.md`.
- Include YAML frontmatter with at least `name`, `description`, and `created_by`.
- Keep workflows deterministic. A skill should describe a reliable reusable sequence, not a loose brainstorm.
- Prefer repository conventions and safety constraints over generic external advice.

## Required Sections
1. `## Purpose`
2. `## When To Use`
3. `## Inputs`
4. `## Workflow Steps`
5. `## Constraints`
6. `## Examples`

## Safety Rules
- Never include API keys, secrets, or production credentials.
- Never encode schema changes without requiring a migration.
- Never normalize a workflow into a skill until it matches repository conventions.
