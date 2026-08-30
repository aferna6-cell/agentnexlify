# Idea 01 — Step 9K: Stale Subconscious Draft PR Audit

## Category
workflow_efficiency

## Summary
Add Step 9K to nightly-commit-review SKILL.md: audit open `subconscious/*` PRs nightly, warn when ≥3 stale (>30d), escalate when ≥5 or any PR exceeds 60d.

## Evidence
- 23 historical run directories in `subconscious/runs/` (grep count)
- governance.json confirms ≥3 open subconscious PRs since run 102
- Run 113 mandate: "if >=3, Step 9K is run 113 winner" — condition confirmed
- Nightly log 2026-08-30: Step 9J ran but 9K absent — subconscious PRs unaudited
- `mcp__github__list_pull_requests` already used in Step 9J — no new tool required
- Step 9C/9I already post GitHub comments — escalation pattern established

## Carry-Forward Status
- Run 113: recommendation (1st carry-forward from run 106 proposal)
- Run 114 mandate: autonomous-executable fires at 1st carry-forward

## Implementation
Edit `.claude/skills/nightly-commit-review/SKILL.md` — insert Step 9K after Step 9J block (line 424):

```
9K. (Subconscious PR Audit) List open PRs → filter head.ref starts with "subconscious/" →
    compute age_days → if stale_count≥3 OR critical_count≥1: warn in report + list PRs →
    if stale_count≥5 OR critical_count≥1: post comment on oldest PR
```

## Risk
LOW — additive step, no existing behavior modified, uses established GitHub MCP tools

## Confidence
HIGH (governance-mandated, condition confirmed, same channel as 6 prior Step 9x wins)
