### Idea 2: Fix Step 9G — Replace gh CLI with mcp__github__actions_run_trigger

**Evidence:**
nightly-2026-09-05 Step 9G reports: "gh CLI not available in this remote environment. Cannot trigger
gh workflow run kb-autopopulate.yml." KB is 10 days stale (threshold: 7 days). Step 9G was designed
to self-heal KB staleness by triggering the GH Actions workflow — but the mechanism (gh CLI) is
unavailable in cloud container sessions. This has been true since cloud sessions became the default
execution environment. Every nightly since the cloud transition fires Step 9G and logs "not available."
The KB feed from autopopulate is downstream of tenant knowledge base accuracy (AI chat answers quality).

**Action:**
Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9G section:
Replace `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify` with:
`mcp__github__actions_run_trigger(owner="aferna6-cell", repo="agentnexlify", workflow_id="kb-autopopulate.yml", ref="main")`
Replace `gh run list --workflow=kb-autopopulate.yml ...` with:
`mcp__github__actions_list(owner="aferna6-cell", repo="agentnexlify", workflow_id="kb-autopopulate.yml", per_page=1)`
Remove the `sleep 30` (no shell sleep available in MCP session — omit and log "status pending").

**Impact:**
Step 9G works in cloud sessions. KB staleness auto-heals when ANTHROPIC_API_KEY is set in GH Actions.
Currently 0% effective → 100% effective for the mechanism.
Category: operational
Effort: S (SKILL.md edit, 2 bash blocks replaced with MCP tool calls)
