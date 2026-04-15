---
name: skill-creator
description: Create new skills, edit existing skills, or benchmark skill triggering accuracy. Load when user says "create a skill", "add a skill to .claude/skills/", "improve this SKILL.md description", "eval this skill", or "why isn't my skill triggering".
origin: https://github.com/anthropics/skills/tree/main/skills/skill-creator
version: 1.0.0
triggers:
  - create a skill
  - add a skill
  - improve SKILL.md
  - eval this skill
  - why isn't my skill triggering
  - skill description
---

# Skill Creator — SKILL.md Authoring + Eval

## When to Use
- Creating a new `.claude/skills/<name>/SKILL.md`
- Rewriting an existing skill's description for better triggering
- Evaluating whether a skill auto-loads on the right prompts
- Debugging why a skill doesn't load when it should

## When NOT to Use
- Writing rules (use `.claude/rules/`, not skills)
- Writing commands (use `.claude/commands/`, not skills)
- Writing agents (use `.claude/agents/`, not skills)

# Skill Creator (thin wrapper)

Test-driven workflow for authoring `.claude/skills/<name>/SKILL.md` files. Adapted from anthropics/skills.

## Loop
1. Decide what the skill does and when it should load (trigger spec)
2. Draft SKILL.md — YAML frontmatter (`name`, `description` ≤200 chars, optional `dependencies`, `version`) + markdown body (≤150 lines)
3. Write 3–5 test prompts that should trigger the skill + 3–5 that should NOT
4. Run each prompt with the skill installed — observe whether Claude auto-loads it
5. Score: triggered-when-should ≥80%, triggered-when-shouldn't <10%
6. Rewrite description if below bars. Specific verbs + file paths in description win.
7. Repeat

## AgentNexLiFy conventions
- Location: `.claude/skills/<kebab-name>/SKILL.md`
- Frontmatter fields we use: `name`, `description`, `origin` (optional URL), `version`, `dependencies` (optional, e.g. `python>=3.11`)
- Body under 150 lines. Long references go to `.claude/skills/<name>/resources/`
- Tone: caveman — see `.claude/rules/caveman-mode.md`
- Test with 5 trigger prompts in a scratch session; grade pass/fail manually
- Reference existing good skills: `schema-guard/SKILL.md`, `widget-test/SKILL.md`

## Description guidelines
- Lead with the action verb (create, audit, generate, fix)
- Name concrete triggers: file paths, task verbs, error messages
- Drop generic filler ("help", "assist", "general")
- ≤200 chars — Claude uses this at startup to decide whether to load the skill body
- Bad: "Helps with database stuff"
- Good: "Load when writing queries against Supabase leads/conversations tables in backend/routers/ or authoring migrations/NNN_*.sql"

## Full upstream skill
https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md (485 lines — eval harness + variance analysis)
