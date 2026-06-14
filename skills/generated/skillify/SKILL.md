---
name: skillify
effort: medium
description: "Use when asked to /skillify, create, improve, audit, or fix an Agent Nexlify skill. Produces repo-compliant SKILL.md files with triggers, read-first steps, output formats, scope limits, eval prompts, and validation."
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
- A skill does not fire reliably, fires too broadly, or produces inconsistent output.
- A repo pattern should be captured as a concise `skills/canonical/<name>/SKILL.md` and synced to the target trees.

## When NOT to Use
- Do not use for one-off notes that belong in normal docs.
- Do not create a skill when an existing skill only needs a small update.
- Do not encode secrets, private credentials, or environment-specific values.

## Read First
- Read `docs/SKILL-STANDARD.md`.
- Search existing skills with `rg --files skills/canonical .claude/skills .codex/skills .agents/skills skills/generated`.
- Inspect nearby eval fixtures under `skills/evals/` when the skill has routing examples.

## Workflow
1. Identify the repeated task, the exact trigger phrase, the expected output, and the surfaces the skill may touch.
2. Decide whether to create a new skill or update an existing skill; prefer updating when the trigger surface already exists.
3. Write or update a concise `skills/canonical/<name>/SKILL.md` that follows `docs/SKILL-STANDARD.md`.
4. Front-load the description with `Use when ...`, what the skill does, and the most important trigger context.
5. Include frontmatter with `name`, `description`, `version`, `origin`, and useful `triggers`.
6. Include `When to Use`, `When NOT to Use`, `Read First`, `Workflow`, `Output Format`, `Constraints`, and `Examples`.
7. Add 3-5 prompts that should trigger the skill and 3-5 prompts that should not trigger it.
8. For canonical skills, add or update `skills/evals/<name>.json` with at least 3 positive and 3 negative prompts.
9. For canonical-managed skills, run `python scripts/sync_skills.py --target all --write` after updating the source copy.
10. Validate frontmatter, path/name alignment, canonical sync status, and trigger evals with the smallest relevant checker available.

## Output Format
Report:
- Canonical skill path changed
- Synced target paths
- Trigger examples and non-trigger examples
- Validation commands run and results
- Any unresolved overlap with existing skills

## Constraints
- Keep `SKILL.md` body under 150 lines unless a reference file is clearly needed.
- Keep every skill under 500 body lines; split longer material into references or scripts.
- Prefer scripts for deterministic repeated checks instead of long natural-language recipes.
- Do not create README, quick-reference, changelog, or other auxiliary files inside the skill unless explicitly required.
- Do not broaden an existing skill's trigger description so far that it steals unrelated tasks.
- Do not import marketplace or community skill packs wholesale; review scripts and copy only narrow workflows with eval coverage.

## Examples
- Use when asked: "/skillify this release checklist"
- Use when asked: "turn that repeated verification flow into a skill"
- Use when asked: "add a skill for contractor onboarding QA"
- Use when asked: "fix why this skill does not fire"
- Do not use when asked: "write a normal architecture note"
