# Idea 5 — Step 9D Enhancement: Auto-comment on Stalled ai-ready Issues After 14 Days

## Category
workflow_efficiency

## Evidence
- Nightly 2026-09-11 Step 9D: 3 ai-ready issues stalled >24h with no linked PR:
  - #728 (fix agent-os CRM guard) — 10 days old, no PR
  - #669 ([security] 95 routers missing block_demo_role) — 22 days old, no PR
  - #660 (scoring_config.py missing block_demo_role) — 27 days old, no PR
- Issue-to-PR loop has been stalled (GH Actions dark since 2026-07-20 per CLAUDE.md)
- Current Step 9D reports stalled issues but takes no action to nudge them
- #669 and #660 are security issues — 22-27 day window on security patches is CVE risk

## Proposal
**Enhance Step 9D in SKILL.md:**

```
9D-nudge: For each ai-ready issue stalled >14 days with no linked PR:
  Search existing comments: look for last autonomous nudge comment timestamp
  If no nudge in past 7 days:
    add_issue_comment(issue_number=N,
      body='Automated nudge: issue has been ai-ready for [D] days with no linked PR. Issue-to-PR loop status: [check autopilot-issue-loop.yml last run]. This is blocking [security/feature] delivery. Human review or loop restart recommended.'
    )
    Log: 'Step 9D: nudged issue #N ([D] days stalled)'
```

## Expected Impact
- Security issues (#669, #660) get visible escalation after 14 days
- Dedup guard (7-day comment threshold) prevents spam
- Human gets GH notification on their issue — most reliable attention mechanism
- Applies to all future stalled ai-ready issues automatically

## Autonomous-executable
YES — SKILL.md edit, add_issue_comment via mcp__github__add_issue_comment (already used in Step 9C/9D).
