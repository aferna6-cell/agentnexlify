# Idea 4 — AI-to-Human Handoff (Force Accept/Reject via GH Issue)

**Category:** Customer Value
**Effort:** M (3-4 hours — backend router + frontend component + widget event)
**Moratorium impact:** ADDS to human queue — BLOCKED by moratorium
**Evidence:**

- `docs/dev-knowledge/customer-gaps.md` — "AI-to-Human Handoff (Critical, Medium effort)"
- Morning digest: 0 product features shipped in 24h
- Current widget: no escalation path when AI can't answer
- GoHighLevel competitor: has human handoff; this is our feature gap vs #1 competitor

## The Gap

When the chat widget AI can't answer a question or user asks for a human, there is no path. The conversation ends or loops. This is a critical friction point for conversion.

## Proposed Feature

1. Widget: detect frustration signals ("speak to human", "real person", "not helpful") → fire `handoff_requested` event
2. Backend: `POST /api/widget/handoff` — marks conversation, notifies tenant via email/SMS
3. Frontend: Dashboard "Handoff Queue" panel — tenant sees pending human-needed conversations
4. Notification: Resend email to tenant when handoff requested

## Why Parked This Run

- Moratorium: would add new human-required item to queue (already at ~4)
- Effort is M — needs grill-me + PRD before estimate solidifies
- Widget event needs byte-identical update in both locations (complexity)

## Re-evaluate When

True_pending_approvals ≤ 1 and SMS Dashboard shipped. This is the next M-effort customer feature after that.
