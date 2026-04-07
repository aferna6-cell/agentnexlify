# SKILL.md Standard — AgentNexLiFy

## The Standard

Every SKILL.md file follows this structure:

```yaml
---
name: skill-name
description: "One sentence. When to use it. What it does."
version: 1.0.0
origin: claude | codex | repo | generated
user_invocable: true  # optional, default true
allowed_tools: [Read, Edit, Bash, Grep, Glob]  # optional
depends_on: [other-skill-name]  # optional, list of skill dependencies
triggers: ["phrase one", "phrase two"]  # optional, common user phrases that should trigger this skill
---
```

## Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Kebab-case identifier. Must match directory name. |
| `description` | Yes | One sentence. Must include when to use AND what it does. |
| `version` | Yes | Semver. Start at 1.0.0. Bump on breaking changes. |
| `origin` | Yes | Where this skill lives: `claude` (.claude/skills/), `codex` (.codex/skills/), `repo` (skills/), or `generated` (skills/generated/) |
| `user_invocable` | No | Whether users can directly invoke this skill. Default: `true`. |
| `allowed_tools` | No | Tools this skill is permitted to use. Omit if unconstrained. |
| `depends_on` | No | Other SKILL.md names this skill requires. Enables dependency resolution. |
| `triggers` | No | Common user phrases that should load this skill. |

## Body Structure

After the frontmatter, the skill body follows this structure:

```markdown
# Skill Title

## When to Use
Clear list of situations. Bullet points. No ambiguity.

## When NOT to Use
Explicitly state when this skill should NOT be loaded.

## Workflow
Step-by-step instructions. Numbered. Actionable.

## Constraints
Hard rules. Things this skill must not do.

## Examples
- Use when asked: "example user request"
- Use when asked: "another example"
```

## Progressive Disclosure

Skills are designed for three-level loading:

- **Level 1 (name + description only):** Agent decides whether to load this skill
- **Level 2 (full SKILL.md body):** Agent reads the complete skill
- **Level 3 (referenced files):** Skill references external files via `depends_on` or inline file paths

Every skill must be usable at all three levels. The frontmatter is Level 1. The body is Level 2. Cross-references are Level 3.

## Naming Conventions

- Directory name = `name` field (kebab-case)
- File must be `SKILL.md` (exact case)
- No spaces, no special characters in names
- Prefix repo-specific skills with `agentnexlify-` only if they are surface-wide constraints

## Location Map

| Location | Purpose |
|----------|---------|
| `.codex/skills/{name}/SKILL.md` | Codex-native skills (surface-wide constraints, schema guards) |
| `.claude/skills/{name}/SKILL.md` | Claude-native skills (workflows, patterns, domain knowledge) |
| `skills/{name}/SKILL.md` | Repo-level shared skills (cross-tool compatible) |
| `skills/generated/{name}/SKILL.md` | Auto-generated or imported skills |

## Migration Guide

For existing skills:
1. Add missing frontmatter fields
2. Standardize description format: "Use when [situation]. [What it does]."
3. Add `version: 1.0.0`
4. Add `origin` based on location
5. Add `triggers` if the skill has clear trigger phrases
6. Add `depends_on` if the skill references other skills
7. Ensure body has "When to Use" and "When NOT to Use" sections
