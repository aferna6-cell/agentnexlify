---
description: Verify → simplify → PR to main → auto-merge on green CI. Runs at end of any implementation task.
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
6. Commit outstanding → push → open PR against `main`
7. `gh pr merge <num> --auto --squash --delete-branch`
8. Report PR URL + verification matrix

Halt rules:
- Any verification fails → halt before PR, surface blocker
- Pre-push hook blocks on unrelated issue → ask user
- No branch protection on main → skip auto-merge, warn

Never `--no-verify`. Never force-push main.

Full spec: `.claude/skills/go/SKILL.md`
