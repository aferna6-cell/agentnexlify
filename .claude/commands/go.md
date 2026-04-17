---
description: Verify → simplify → push direct to main. Solo-dev flow at end of any implementation task.
argument-hint: [optional: scope description]
model: sonnet
---

Invoke the `go` skill. Arguments: `$ARGUMENTS`.

Steps (delegate to skill):
1. Detect changed surfaces (backend/frontend/widget/schema/infra)
2. Boot services for touched surfaces
3. E2E verify — Playwright MCP + chrome-devtools-mcp + autonomous-webapp-test (all three for frontend)
4. Run `/simplify` on diff
5. Run `verification-loop` full gate
6. Commit outstanding → `git push origin HEAD:main`
7. If rejected: `git fetch origin main && git rebase origin/main && git push`
8. Report commit SHA + verification matrix

Halt rules:
- Any verification fails → halt before push, surface blocker
- Pre-push hook blocks on unrelated issue → ask user

Never `--no-verify`. Never force-push main.

Full spec: `.claude/skills/go/SKILL.md`
