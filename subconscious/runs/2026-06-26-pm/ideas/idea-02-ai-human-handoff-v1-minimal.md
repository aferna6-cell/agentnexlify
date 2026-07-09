# Idea 02 — AI-to-Human Handoff v1 Minimal

**Category:** customer_value  
**Confidence:** MEDIUM  
**Autonomous:** false — REQUIRES HUMAN  
**Effort:** M (~2-3h backend + frontend + widget)

## Summary
AI-to-Human Handoff has been in active_directions since run 4 (2026-04-16, 70+ days). customer-gaps.md classifies it as "Critical for all industries, Medium effort." A minimal v1 adds a "Transfer to Human" button in the widget chat. When triggered, the tenant receives an email/SMS alert with the full conversation transcript so they can follow up directly. No live chat relay required — just the handoff signal + transcript delivery.

## Evidence
- customer-gaps.md: "AI-to-Human Handoff — Critical for all industries, Medium effort — still open after 74 days (run 4, 2026-04-16)"
- Real estate, dental, legal use cases all blocked on this: complex questions that AI can't answer need human escalation
- No new evidence of customer complaints this week (council sprint addressed other gaps)
- Moratorium still active — true_pending ~6, moratorium threshold = 2

## Proposed Action
Backend: Add `POST /api/chat/handoff` endpoint that marks conversation as `handoff_requested`, sends tenant notification (Resend email + optional Twilio SMS) with full transcript.  
Widget: Add "Talk to a Human" button (configurable visibility in widget_configs). Triggers handoff endpoint.  
Frontend: Dashboard conversation list shows handoff flag; tenant can mark as "handled."

## Why Weakened
- Moratorium active (true_pending 6 >> max_pending_approvals 2) — not exempt from constraint
- No new forcing function since run 4 (no customer complaints specifically about this in last 3 days)
- M-effort + requires human approval + schema change (conversations.handoff_status column)
- Would be strong candidate post-moratorium-exit (when check exits 0 + cleanup sprint done)

## Sequencing
Eligible as winner after: (1) run 65 fix implemented (check exits 0), (2) cleanup sprint (true_pending ≤ 2), (3) moratorium exits. Strongest customer-value item in the backlog.
