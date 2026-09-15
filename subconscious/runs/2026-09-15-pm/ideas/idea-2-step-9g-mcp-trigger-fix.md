# Idea 2 — Fix Step 9G: Use mcp__github__actions_run_trigger Instead of gh CLI

**Category:** workflow_efficiency / operational
**Effort:** S (Step 9G block edit in SKILL.md + verify workflow_dispatch in kb-autopopulate.yml)
**Confidence:** MEDIUM
**Status:** WEAKENED (prerequisite verification needed)

---

## Problem

Step 9G in the nightly skill cannot trigger the KB autopopulate workflow because `gh` CLI is not available in cloud sessions. Today's nightly confirms:

> Step 9G: gh CLI not available in this environment. Cannot trigger workflow run. KB remains stale — manual trigger: `bash scripts/daily/kb-autopopulate.sh` or GH Actions UI.

KB is now 20 days stale (Step 9F fires, Step 9G cannot self-heal).

---

## Proposed Fix

Replace `gh workflow run` with `mcp__github__actions_run_trigger` in Step 9G:

```python
# Current (broken in cloud):
subprocess.run(["gh", "workflow", "run", "kb-autopopulate.yml"])

# Proposed:
mcp__github__actions_run_trigger(
    repo="aferna6-cell/agentnexlify",
    workflow_id="kb-autopopulate.yml",
    ref="main"
)
```

---

## Prerequisites (unverified — this is why WEAKENED)

1. Does `kb-autopopulate.yml` have `workflow_dispatch` trigger enabled?
   - Without it, `actions_run_trigger` returns 422 (workflow not dispatchable)
   - Must verify before implementing

2. Is `mcp__github__actions_run_trigger` available in the nightly session context?
   - Nightly sessions use GitHub MCP server — need to confirm tool availability in that session type

3. Would triggering the GH Actions workflow consume runner minutes?
   - CLAUDE.md notes: "no workflow has a cron and all are dark since 2026-07-20 (GH #500)"
   - If actions are dark, triggering one might fail silently or bill unexpectedly

---

## Verdict: WEAKENED

Park for run 122. Requires:
1. `grep 'workflow_dispatch' .github/workflows/kb-autopopulate.yml` to verify
2. Test `mcp__github__actions_run_trigger` availability in a nightly session context
3. Confirm GH Actions dark status won't block the trigger
