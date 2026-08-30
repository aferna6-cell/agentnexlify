# Idea 02 — Step 9J Detection Fix: search_pull_requests for Dependabot

## Category
workflow_efficiency

## Summary
Step 9J uses `mcp__github__list_pull_requests` with `user.login == "dependabot[bot]"` filter, which fails in headless sessions. Fix: use `mcp__github__search_pull_requests` with query `"repo:aferna6-cell/agentnexlify is:pr is:open author:app/dependabot"`.

## Evidence
- nightly-commit-review-2026-08-30.md: "Step 9J: skipped — No Dependabot PRs detected"
- Run 113 winning-concept.md bonus action: confirms detection failure, proposes search API fix
- Run 113 mandate check confirms Step 9J rebase trigger FAILED (0 PRs detected)
- GitHub Search API is more reliable for bot-authored PRs in headless/API contexts
- `mcp__github__search_pull_requests` already available (same MCP server)

## Implementation
In `.claude/skills/nightly-commit-review/SKILL.md` Step 9J.1 (lines 394-395):
- FROM: `mcp__github__list_pull_requests` state="open", base="main", filter user.login=="dependabot[bot]"
- TO: `mcp__github__search_pull_requests` query="repo:aferna6-cell/agentnexlify is:pr is:open author:app/dependabot"

## Risk
LOW — same result set, more reliable API, no behavior change when PRs present

## Confidence
HIGH (failure documented in consecutive nightly logs, fix is exact search API swap)
