---
name: verify
description: "Use when asked to run /verify, verify Agent Nexlify changes, run checks, or prepare a quality gate without committing or pushing."
version: 1.0.0
origin: claude
user_invocable: true
allowed_tools: [Read, Bash, Grep, Glob]
depends_on: [verification-loop]
triggers: ["/verify", "verify", "verify changes", "run checks", "quality gate", "pre-PR check"]
---

# Verify

## When to Use
- After Agent Nexlify code, docs, config, or test changes.
- Before asking for review, opening a PR, or handing work back.
- When the user asks for `/verify`, "verify", "run checks", or a quality gate.

## When NOT to Use
- Do not use as a commit, push, deploy, or release workflow.
- Do not use during the middle of an edit unless the user asks for an incremental check.
- Do not run the full suite first when a small targeted check is enough to find the likely failure.

## Workflow
1. Inspect the changed files with `git status --short` and `git diff --stat`.
2. Run the fastest relevant gate first, normally `npm run check:quick` when available.
3. Run targeted tests for touched surfaces:
   - Backend Python: the narrowest matching `pytest` file or test node.
   - Frontend: the matching build, lint, or Vitest command used by the repo.
   - Scripts/docs: syntax, frontmatter, markdown, or command help checks as appropriate.
4. Escalate to `npm run check:full` before final handoff when changes cross surfaces or user asks for complete verification.
5. Review the outgoing diff after checks. Report pass/fail, commands run, unresolved risks, and skipped checks.

## Constraints
- Never commit, push, tag, deploy, or alter git remotes.
- Do not hide failures. Summarize the first useful failure and stop broad reruns until it is fixed.
- Prefer existing package scripts and repo-local test helpers over ad hoc commands.
- Keep verification proportional to risk, but explain any skipped full-suite check.

## Examples
- Use when asked: "/verify"
- Use when asked: "verify this before we ship"
- Use when asked: "run the quality gate"
- Use when asked: "check the backend change"
