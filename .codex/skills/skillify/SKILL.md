---
name: skillify
description: "Use when asked to /skillify a repeated Agent Nexlify workflow into a repo-compliant SKILL.md with trigger examples and validation."
version: 1.0.0
origin: claude
user_invocable: true
allowed_tools: [Read, Edit, Bash, Grep, Glob]
depends_on: [skill-creator]
triggers: ["/skillify", "skillify", "create a skill", "turn this into a skill", "make this repeatable", "add a workflow skill"]
---

# Skillify

## When to Use
- A workflow has been repeated enough that a one-line trigger would save time.
- The user asks to create, improve, or evaluate an Agent Nexlify skill.
- A repo pattern should be captured as a concise `skills/canonical/<name>/SKILL.md` and synced to the target trees.

## When NOT to Use
- Do not use for one-off notes that belong in normal docs.
- Do not create a skill when an existing skill only needs a small update.
- Do not encode secrets, private credentials, or environment-specific values.

## Workflow
1. Identify the repeated task, the exact trigger phrase, the expected output, and the surfaces the skill may touch.
2. Search existing skills first with `rg --files skills/canonical .claude/skills .codex/skills .agents/skills skills/generated` and avoid duplicates.
3. Write or update a concise `skills/canonical/<name>/SKILL.md` that follows `docs/SKILL-STANDARD.md`.
4. Include frontmatter with `name`, `description`, `version`, `origin`, and useful `triggers`.
5. Add 3-5 prompts that should trigger the skill and 3-5 prompts that should not trigger it.
6. If an eval fixture, trigger checker, or skill index exists, update it with the new trigger examples. For canonical-managed skills, run `python scripts/sync_skills.py --target all --write` after updating the source copy.
7. Validate frontmatter, path/name alignment, and canonical sync status with the smallest relevant checker available.
8. Report the canonical skill path, trigger examples, validation performed, and any unresolved overlap with existing skills.

## Constraints
- Keep `SKILL.md` body under 150 lines unless a reference file is clearly needed.
- Prefer scripts for deterministic repeated checks instead of long natural-language recipes.
- Do not create README, quick-reference, changelog, or other auxiliary files inside the skill unless explicitly required.
- Do not broaden an existing skill's trigger description so far that it steals unrelated tasks.

## Examples
- Use when asked: "/skillify this release checklist"
- Use when asked: "turn that repeated verification flow into a skill"
- Use when asked: "add a skill for contractor onboarding QA"
- Do not use when asked: "write a normal architecture note"
