# Winning Concept — 2026-09-19-pm (Run 125)

## Recommendation
Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9G block: replace the broken `gh workflow run kb-autopopulate.yml` bash command with `mcp__github__actions_run_trigger({owner: "aferna6-cell", repo: "agentnexlify", workflow_id: "kb-autopopulate.yml"})` MCP tool call.

## Why This, Why Now
The `gh` CLI is absent in cloud container sessions — nightly-2026-09-19 confirms Step 9G has been silently failing every run. The KB has been stale for 24+ days as a direct result. An in-session MCP workaround applied 2026-09-18 returned HTTP 204 (success), proving `mcp__github__actions_run_trigger` works in this environment. Run 121 set the autonomous-executable mandate at run 124; this is run 125 — one run overdue. The fix is a single-block edit with no architectural change; the same Step 9G logic (status check, failure comment on GH #403, SUCCESS log line) is preserved, only the invocation mechanism changes.

## Implementation Sketch
1. Read `.claude/skills/nightly-commit-review/SKILL.md` lines 280–350 (Step 9G block)
2. Locate the `gh workflow run kb-autopopulate.yml` bash block
3. Replace it with:
   ```
   result = mcp__github__actions_run_trigger({
     owner: "aferna6-cell",
     repo: "agentnexlify",
     workflow_id: "kb-autopopulate.yml"
   })
   if result.status != 204:
     # comment on GH #403 with failure detail
     mcp__github__add_issue_comment({issue_number: 403, body: "Step 9G: kb-autopopulate trigger failed — status " + result.status})
   else:
     log("Step 9G: kb-autopopulate triggered — SUCCESS")
   ```
4. Verify the edit: re-read the Step 9G block and confirm no `gh workflow run` remains
5. Commit: `git commit -m "nightly: fix Step 9G — replace gh CLI with mcp__github__actions_run_trigger"`

## What This Replaces
Previous active direction: "Step 9G SKILL.md Fix" has been the winning concept since run 121. This run continues the same direction, now one cycle past autonomous-executable threshold. The task-prompt recommend-only constraint means implementation must wait for human approval even though the governance mandate has passed.

## Confidence
**HIGH** — evidence is unambiguous: Step 9G broken (nightly log, `grep` 0 hits for MCP tool), fix proven (in-session MCP call 2026-09-18 status 204), threshold passed (run 124 was the autonomous-executable trigger, this is run 125). Only blocker is the task-prompt recommend-only override.
