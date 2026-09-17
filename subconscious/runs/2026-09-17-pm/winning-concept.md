# Winning Concept — Run 2026-09-17-pm (Run 121)

**Winner:** Fix Step 9G — Replace `gh workflow run` with `mcp__github__actions_run_trigger`
**Category:** workflow_efficiency / operational
**Effort:** XS (single block edit in SKILL.md)
**Confidence:** HIGH
**Carry-forward count:** 0 (new this run)
**Autonomous-executable threshold:** 3 consecutive carries → run 124 fires at run 124

---

## Problem

Step 9G in `.claude/skills/nightly-commit-review/SKILL.md` triggers the KB autopopulate GitHub Actions workflow. Current implementation:

```bash
gh workflow run kb-autopopulate.yml --repo aferna6-cell/agentnexlify
```

The `gh` CLI is not available in cloud/CCR sessions (where all scheduled Claude Code Routines execute). This has caused Step 9G to **silently fail** for ~30 days (since ~run 107, 2026-08-19).

**Evidence of damage:**
- nightly-2026-09-17: Step 9G ABSENT from output entirely. No mention, no failure, no comment.
- KB last successful run: 2026-08-26 (22 days ago). Threshold: 7 days. STALE.
- GH #403 (KB staleness tracking — human-action-required: set ANTHROPIC_API_KEY in Actions secrets) was last commented on by Step 9F. Step 9G has added zero diagnostic pressure on #403.
- Escalation loop broken: owner is not being reminded that KB autopopulate is failing because Step 9G silently swallows the failure.

**Why this is fixable now:**
- `mcp__github__actions_run_trigger` is confirmed in the deferred tools list for this session type (verified run 121).
- Run 120 governance note said this fix was parked as "unverified tool availability." That uncertainty is resolved.

---

## Implementation

Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9G block.

**Find Step 9G block (approximately lines 324-342):**
```
### Step 9G — KB Autopopulate Self-Healing Trigger
...
```

**Change:**
```bash
# Current (broken in cloud — gh CLI unavailable):
bash -c "gh workflow run kb-autopopulate.yml --repo aferna6-cell/agentnexlify" 2>&1

# New (MCP-based — works in cloud sessions):
# Use mcp__github__actions_run_trigger with:
#   owner: "aferna6-cell"
#   repo: "agentnexlify"
#   workflow_id: "kb-autopopulate.yml"
#   ref: "main"
# Handle result: if trigger succeeds → log "Step 9G: triggered kb-autopopulate.yml"
# Handle failure: log error + add comment to GH #403 with diagnostic
```

**Pseudocode:**
```python
result = mcp__github__actions_run_trigger(
    owner="aferna6-cell",
    repo="agentnexlify",
    workflow_id="kb-autopopulate.yml",
    ref="main"
)
if result.success:
    log("Step 9G: triggered kb-autopopulate.yml via mcp")
else:
    log(f"Step 9G: trigger failed — {result.error}")
    mcp__github__add_issue_comment(
        owner="aferna6-cell", repo="agentnexlify",
        issue_number=403,
        body=f"Step 9G automated update: kb-autopopulate workflow trigger failed. Error: {result.error}. KB last run: {{kb_last_run_days}} days ago (threshold 7d). Action required: verify Actions secrets and workflow config."
    )
```

**Note on expected behavior after fix:**
The kb-autopopulate workflow may still fail if ANTHROPIC_API_KEY is missing from Actions secrets (tracked in GH #403). However:
1. Step 9G will now correctly detect the failure (explicit error vs. silent nothing).
2. A diagnostic comment on GH #403 will fire, restoring escalation pressure.
3. When #403 is resolved (key added), Step 9G will work immediately — no further SKILL.md changes needed.

---

## Verification After Implementation

```bash
grep 'mcp__github__actions_run_trigger' .claude/skills/nightly-commit-review/SKILL.md
grep 'kb-autopopulate' .claude/skills/nightly-commit-review/SKILL.md
```

Both must return results in the Step 9G block. The `gh workflow run` line must be absent or commented out.

Next nightly run: Step 9G should attempt trigger and either succeed (log success) or comment on GH #403 with diagnostic.

---

## Run 122 Mandate

1. Verify `mcp__github__actions_run_trigger` present in Step 9G (grep check)
2. Did Step 9G fire in the next nightly after implementation? Check nightly log for "Step 9G: triggered" or a comment on GH #403.
3. Step 9E: 3rd carry-forward (AUTOPILOT_GH_TOKEN now 76d+ → existing logic fires, but 10-day early warning still absent). Run 122 = autonomous-executable for Step 9E per run 120 escalation path.
4. AUTOPILOT_GH_TOKEN: rotated by owner before 2026-10-02?
5. Brain PAT: rotation GH issue filed?
6. os_tool_executions.py (783L): 5th consecutive mention — escalate to owner via GH issue if not yet done.
