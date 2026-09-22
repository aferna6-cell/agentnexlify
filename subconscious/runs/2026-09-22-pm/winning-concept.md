# Run 126 — Winning Concept

**Winner:** Step 9G SKILL.md Fix — Replace `gh workflow run` with `mcp__github__actions_run_trigger`
**Category:** Workflow Efficiency
**Carry count:** 3 (autonomous-executable since run 124)
**Status:** Recommend (task-prompt constraint: "Do NOT implement. Only recommend.")

---

## Problem

Step 9G in `.claude/skills/nightly-commit-review/SKILL.md` triggers KB autopopulation when the KB is stale (>=2 days). The current implementation uses a bash command:

```bash
gh workflow run kb-autopopulate.yml \
  --repo aferna6-cell/agentnexlify \
  --ref main
```

`gh` CLI is unavailable in CCR (Cloud Code Runtime), the environment where all Claude Code Routines execute. This command silently fails (or errors with "gh: command not found") on every nightly-commit-review run. KB autopopulate has not fired via automation since GH Actions went dark on 2026-07-20 (63+ days). KB is currently 27 days stale (last run 2026-08-26).

---

## Evidence

- `mcp__github__actions_run_trigger` is available and confirmed working in CCR (in-session workaround, run 122, 2026-09-18)
- Morning digest 2026-09-22: KB 27 days stale, cause = "GH Actions dark, no ANTHROPIC_API_KEY secret" + broken Step 9G trigger
- GH #403 (ANTHROPIC_API_KEY) = separate blocker for the actual workflow; Step 9G fix removes the broken trigger independently
- After AUTOPILOT_GH_TOKEN rotation (human-gated, GH #893), KB recovery requires Step 9G to work correctly

---

## Proposed Fix

In `.claude/skills/nightly-commit-review/SKILL.md`, Step 9G block, replace the bash `gh workflow run` invocation with an MCP tool call:

**Remove:**
```bash
gh workflow run kb-autopopulate.yml \
  --repo aferna6-cell/agentnexlify \
  --ref main
```

**Replace with (tool call, not bash):**
```
mcp__github__actions_run_trigger({
  owner: "aferna6-cell",
  repo: "agentnexlify",
  workflow_id: "kb-autopopulate.yml",
  ref: "main"
})
```

Add a comment noting the bash fallback (for non-CCR sessions):
```
# Note: gh CLI unavailable in CCR. Use mcp__github__actions_run_trigger.
# Fallback for interactive sessions: gh workflow run kb-autopopulate.yml --repo aferna6-cell/agentnexlify --ref main
```

---

## Expected Impact

1. Nightly-commit-review Step 9G fires correctly in CCR
2. KB autopopulate workflow triggered on next stale-KB nightly run
3. After AUTOPILOT_GH_TOKEN rotation, KB recovery is unblocked end-to-end
4. KB drift halts; kb-first rule becomes reliable again

---

## Scope

- File: `.claude/skills/nightly-commit-review/SKILL.md`
- Section: Step 9G (search for `kb-autopopulate.yml`)
- Change: replace bash command with MCP tool call
- Blast radius: zero (Step 9G only fires when KB stale >= 2d; MCP call is equivalent action)

---

## Status on Step 9E (P0 Credential Expiry)

Step 9E P0 tier demoted to parking lot this run. Rationale:
- GH #893 filed 2026-09-22: "P0: AUTOPILOT_GH_TOKEN expires 2026-10-02 (10 days) — rotate now"
- Provides human-notification path independently of SKILL.md fix
- 6 consecutive carries (runs 119–125) with no implementation due to task-prompt constraint
- A 7th carry produces no new information
- Step 9E remains in governance.json as autonomous-executable when constraint is lifted

**AUTOPILOT_GH_TOKEN expires 2026-10-02. Human action required. See GH #893.**
