# Idea 2 — Fix Step 9G: Replace gh CLI with mcp__github__actions_run_trigger

**Category:** workflow_efficiency / operational
**Effort:** XS (single block edit in SKILL.md)
**Confidence:** HIGH

## Problem

Step 9G in `.claude/skills/nightly-commit-review/SKILL.md` triggers KB autopopulate via:
```
gh workflow run kb-autopopulate.yml
```

`gh` CLI is unavailable in headless cloud sessions (Claude Code on web/Routines).
Result: KB autopopulate self-healing is BROKEN — fires but does nothing.

Evidence:
- KB autopopulate: 22 days stale (threshold: 7 days) — reported in 2026-09-17.md
- GH #403 received comment 22d stale update (Step 9G logging works, but trigger fails silently)
- gh CLI not in PATH in this environment (confirmed by subconscious execution context)

## Implementation

Single edit in `.claude/skills/nightly-commit-review/SKILL.md`, Step 9G block.

Change from:
```bash
gh workflow run kb-autopopulate.yml --ref main
```

Change to:
```python
# Replace gh CLI call with MCP tool
mcp__github__actions_run_trigger(
    repo="aferna6-cell/agentnexlify",
    workflow_id="kb-autopopulate.yml",
    ref="main"
)
```

The MCP GitHub tool is available and authorized in this session.
All other Step 9G logic (staleness check, comment on GH #403) stays unchanged.

## Expected outcome

- KB autopopulate triggers correctly from nightly session
- KB goes from 22d stale → 0d stale within a few hours of trigger
- GH #403 receives proper "triggered" confirmation comment
- Brain connector staleness check (Step 9C) is independent — not fixed here

## Notes

Step 9G is a SKILL.md-only fix. No CLAUDE.md changes, no production code, no schema changes.
Risk: XS. Reversible in one edit. The MCP call is more reliable than gh CLI in cloud context.
