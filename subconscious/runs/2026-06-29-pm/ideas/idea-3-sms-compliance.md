# Idea 3 — SMS Compliance Dashboard (Run 70 Winner)

## Category
Customer Value

## Evidence
- Run 70 winner: "SMS Compliance Dashboard — SMSCompliancePage.jsx + 1 backend endpoint"
- Status: pending_approval, requires_human: true (CLAUDE.md: no unsanctioned frontend pages)
- Backend ready: SMS opt-in/opt-out tracking exists in DB
- Age: 1 day old (run 70 was 2026-06-29 — same day as run 71)
- Implementation estimate: M effort, 1-2 hours
- customer-gaps.md: "SMS Compliance" gap open, medium priority

## Problem
Tenants using Twilio SMS have no visibility into opt-in/opt-out compliance state. TCPA requires documented opt-outs. Liability risk growing as SMS volumes increase.

## Recommendation
Escalate to human-priority queue. Backend endpoint exists, frontend page is the missing piece. SMSCompliancePage.jsx should:
- List all leads with SMS opt-in/opt-out status
- Show opt-out timestamp + reason
- Export CSV for compliance records

## Effort
M — SMSCompliancePage.jsx + 1 GET /api/sms/compliance-summary endpoint

## Risk
MEDIUM — new frontend page touches billing-gated feature (agent_os plan only)

## Status
PARKING LOT — 1 day old, no urgency change since run 70. Re-evaluate run 73+.
