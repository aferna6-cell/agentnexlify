# Idea 4 — AI-to-Human Handoff v1 (Critical Gap, 75+ Days Pending)

## Category
Customer Value

## Evidence
- customer-gaps.md: "AI-to-Human Handoff" listed as CRITICAL, all industries
- Age: 75+ days pending (appeared in run 4 and run 38)
- Effort estimate: Medium
- Impact: HIGH — #1 requested feature by beta tenants
- Competition: GoHighLevel, Birdeye, Podium all have human escalation flows
- No code changes in last 3 days suggest this is genuinely stuck

## Problem
Widget conversations currently have no path for a human to take over mid-conversation. If the AI can't help, the user hits a dead end. Tenants lose leads at the exact moment of intent.

## Recommendation
v1 scope:
- Chat message: "Would you like to speak with someone?" → yes → SMS/email alert to tenant
- Backend: POST /api/conversations/{id}/request-human (sets status = 'human_requested')
- Widget: show "connecting you to our team" state
- No real-time handoff needed for v1 — async notification is sufficient

## Effort
M — backend endpoint + widget flow change + tenant notification trigger

## Risk
HIGH — widget JS change requires byte-identical sync + human approval per CLAUDE.md invariant #4

## Status
HUMAN-REQUIRED — cannot be autonomous; widget change requires human approval
