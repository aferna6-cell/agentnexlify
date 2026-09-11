# Idea 2 — Step 9G Fix: Replace Broken gh CLI with mcp__github__actions_run_trigger

## Category
workflow_efficiency

## Evidence
- Nightly 2026-09-11 Step 9G: "gh CLI not available in this CCR session — cannot trigger kb-autopopulate.yml workflow directly"
- Same failure in runs 116, 117, 118 nightlies — 4+ consecutive broken Step 9G runs
- KB is now 16 days stale (threshold 7d); every nightly notes staleness but cannot fix it
- mcp__github__actions_run_trigger IS available in CCR sessions (listed in deferred tools)
- kb-autopopulate.yml workflow exists in repo and is manually triggerable (GH Actions UI works; only scheduled cron removed per GH #500)
- Scripts daily/kb-autopopulate.sh exists as backup — but cannot be exec'd in CCR cloud session

## Proposal
**Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9G block:**

Replace the `gh workflow run` call with `mcp__github__actions_run_trigger`:

```
9G. (KB Autopopulate Self-Healing)
    If Step 9F flagged staleness > 7 days:
      Use mcp__github__actions_run_trigger(
        owner='aferna6-cell',
        repo='agentnexlify',
        workflow_id='kb-autopopulate.yml',
        ref='main'
      )
      Log: 'Step 9G: triggered kb-autopopulate.yml via MCP'
    Else:
      Log: 'Step 9G: KB fresh, no trigger needed'
```

## Expected Impact
- Fixes 4+ consecutive nightly failures permanently
- KB stays within 7-day freshness threshold going forward
- Unblocks kb-autopopulate automation (GH #403 closed as resolved)
- Zero human action required once SKILL.md updated

## Autonomous-executable
YES — SKILL.md edit, proven channel. LOW risk: adds MCP call, same workflow as manual trigger.
