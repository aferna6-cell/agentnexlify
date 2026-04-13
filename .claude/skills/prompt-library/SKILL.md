---
name: prompt-library
description: Reusable prompt library for consistent AI agent workflows. Always consult PROMPTLIBRARY.md before starting tasks to pick the right prompt, gather context, and execute with proven patterns. Use when user says 'any task', 'before starting work', 'research', 'debug', 'write', 'review', or asks about prompt library.
version: 1.0.0
origin: claude
triggers:
- any task
- before starting work
- research
- debug
- write
- review
- build
- test
- summarize
- reason
user-invocable: false
effort: medium
---

# Prompt Library Workflow

This skill ensures every AI agent follows proven patterns instead of improvising.

## Mandatory Pre-Task Workflow

**Before starting ANY task, you MUST:**

1. **Read `PROMPTLIBRARY.md`** — scan the Index table for a matching prompt
2. **Find the matching prompt** by category:
   - Research → `RESEARCH Codebase Investigation`
   - Summarization → `SUMMARIZE Code Change Summary`
   - Debugging → `DEBUG Bug Investigation` or `DEBUG Production Error Analysis`
   - Writing → `WRITE Documentation Article` or `WRITE Commit Message`
   - Reasoning → `REASON Architecture Decision` or `REASON Debugging Hypothesis`
   - Review → `REVIEW Code Review Checklist`
   - Feature → `BUILD New Feature`
   - Database → `DATABASE Schema Change`
   - Testing → `TEST Add Test Coverage`
   - Library maintenance → `PROMPT Create or Improve Prompt`

3. **Follow the prompt's steps** — each prompt tells you exactly what context to gather and what steps to follow

4. **If no prompt exists** for your task type:
   - Create a new entry in `PROMPTLIBRARY.md` under the appropriate category
   - Write the prompt you wish you had been given
   - Execute the task using your new prompt
   - After completion, refine the prompt with what you learned

5. **After completing the task**, if you used a prompt:
   - Did the prompt help? Was anything missing or wrong?
   - Update the prompt with what you learned (add steps, remove unnecessary ones, add pitfalls)
   - Update the "Last improved" line with the date and what changed
   - Bump the version number

## Why This Matters

- **Consistency:** Every agent follows the same proven patterns
- **Speed:** No reinventing the wheel for common tasks
- **Learning:** Every interaction improves the library
- **Quality:** Prompts are battle-tested and iteratively refined

## Relationship to Other Skills

This skill does NOT replace `.claude/skills/`, `.claude/commands/`, or `.claude/agents/`. It complements them:

- **Skills** (`.claude/skills/`) — Deep domain-specific workflows (schema guard, coordinator, etc.)
- **Commands** (`.claude/commands/`) — Executable multi-step workflows
- **Agents** (`.claude/agents/`) — Specialized agent role definitions
- **Prompt Library** (`PROMPTLIBRARY.md`) — Lightweight, reusable task patterns for ANY agent

The prompt library is the **first stop** — it tells you what context to gather and which deeper skill to activate if needed.

## Anti-Patterns to Avoid

- ❌ Starting a task without checking `PROMPTLIBRARY.md` first
- ❌ Ignoring a prompt's "Context needed" section
- ❌ Skipping the "Improve the prompt" step after completing a task
- ❌ Making prompts longer when they should be more precise
- ❌ Creating a new prompt when an existing one covers 80% of the use case
