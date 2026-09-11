# Idea 2: Fix Step 9G — replace gh CLI with mcp__github__actions_run_trigger

**Evidence:**
- Step 9G broken: gh CLI unavailable in cloud/CCR sessions (confirmed runs 115, 116, 117, nightly-2026-09-11).
- kb-autopopulate.yml has `workflow_dispatch: {}` — MCP trigger IS viable.
- KB at 16 days stale (last: 2026-08-26). AI answers degrade after 7 days.
- mcp__github__actions_run_trigger listed in deferred tools available to nightly sessions via GitHub MCP.
- Nightly sessions routinely use mcp__github__add_issue_comment, mcp__github__search_issues — same MCP server.

**Action:**
Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9G block:
Replace `Bash: gh workflow run kb-autopopulate.yml` with:
`ToolSearch("mcp__github__actions_run_trigger") then mcp__github__actions_run_trigger(owner="aferna6-cell", repo="agentnexlify", workflow_id="kb-autopopulate.yml", ref="main")`
Then check run status; if failed: comment on GH #403 with specific error.

**Impact:**
- KB autopopulate may re-enable if ANTHROPIC_API_KEY is now available in GH Actions.
- Even if key missing: Step 9G gets the actual run error from GH Actions (vs current "gh CLI unavailable" failure).
- WEAKENED if ANTHROPIC_API_KEY still missing (#403) — the workflow still fails, just via MCP now.

**Category:** operational

**Effort:** XS (one-line swap in Step 9G SKILL.md block)

**Confidence:** MEDIUM — MCP tool availability in nightly sessions unverified. If tool absent: Step 9G falls back to "ToolSearch returned nothing" log. No worse than current state.
