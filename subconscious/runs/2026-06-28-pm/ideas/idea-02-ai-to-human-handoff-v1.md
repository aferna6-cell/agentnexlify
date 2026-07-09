# Idea 02 — AI-to-Human Handoff v1

**Category:** Customer Value  
**Effort:** M (1.5-2 days)  
**Confidence:** MEDIUM  
**Status:** 7+ prior recommendations without implementation (run 4 → run 70 = 74 days)  
**Moratorium interaction:** Adds pending_approval. Moratorium must be respected.

---

## The Gap

Identified in `docs/dev-knowledge/customer-gaps.md`:
> AI-to-Human Handoff = Critical, all 7 industries

When the widget AI cannot answer a question — or the customer asks for a human — there is no path to escalation. Conversation dead-ends.

74 days listed as Critical. Zero implementation.

---

## What to Build

### Trigger Detection (widget_chat.py)
Detect handoff phrases in customer messages:
- "speak to someone", "talk to a human", "real person", "call me"
- Low-confidence AI response (e.g., confidence < 0.5 from qualifier)
- Customer sends message 3+ times without satisfaction signal

### Handoff Record (leads table + handoff_requests)
On trigger:
- Set `lead.status = 'needs_follow_up'`
- Write to `handoff_requests` table: lead_id, trigger_phrase, conversation_id, created_at
- Mark conversation as handoff_requested

### Notification (os_outbound_mirror.py)
Notify business owner:
- SMS via Twilio: "Customer [name] on your chat needs human follow-up"
- Email via Resend: summary of conversation + link to lead
- `os_outbound_mirror.py` already handles SMS/email — routing only needed

### Dashboard Indicator
`LeadsPage.jsx` — badge on lead when `status = 'needs_follow_up'`

---

## Why This Is Competitive

GoHighLevel's AI Employee does this. We don't. Every industry where AI can't handle everything (all 7) loses a lead at the handoff gap.

---

## Why It Has Not Been Implemented

- M-effort in a sprint-constrained environment
- Infrastructure was missing (os_outbound_mirror.py shipped 2026-05-27 — now present)
- Pre-commit blocked (now resolved after this run's mandate action)

---

## Debate Considerations

SURVIVES WEAKENED. Valid gap, valid implementation path. Moratorium means it adds to pending count. Correct for parking lot: recommend as follow-on after SMS Compliance Dashboard.

Not winner this run — 74-day non-implementation record despite 7 prior recs indicates friction elsewhere. M-effort + moratorium = queue it properly.
