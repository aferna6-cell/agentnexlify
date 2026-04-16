# Winning Concept — Cycle 1

**Title:** AI-to-Human Handoff (Explicit Trigger, v1)

**Category:** growth / ux

**Date:** 2026-04-04 (pm)

---

## One-Sentence Hypothesis

When a website visitor explicitly asks to speak with a human in the chat widget, the platform captures that request, notifies the business owner via SMS/email, flags the conversation as priority in the dashboard inbox, and responds to the visitor with "We'll have someone follow up with you shortly" — closing the #1 open customer gap across all 7 simulated industries.

---

## Why This Won

### Evidence Strength: 5/5
- Explicitly rated "Critical" in customer-gaps.md — the only "Critical" designation in the entire gaps table
- Affects all 7 simulated industries (plumber, dental, salon, lawyer, fitness, restaurant, real estate)
- Infrastructure already exists (conversations table, team inbox, webhooks, SMS via Twilio)
- Competitors (GoHighLevel AI Employee, Phonely, Toma) cite this as a primary differentiator
- Product-market fit ceiling for Lawyer (7/10) and Real Estate (6/10) is directly limited by this gap

### Debate Outcome: Objections Resolved
- **"No team to hand off to"** → resolved by reframing as async follow-up, not synchronous live agent
- **"False positive detection"** → resolved by scoping to explicit triggers only (user says the words); no AI confidence heuristics in v1
- **"Widget regression risk"** → resolved by minimizing widget-side change (one button, one API call) and running smoke tests before merge

### Scope (Right-Sized)
- v1 is deliberately narrow: explicit trigger only, async notification, conversation flag
- No live agent connection, no queue management, no SLA tracking
- 1.5–2 days of implementation
- All follow-up complexity (AI confidence triggers, v2 live chat) deferred

---

## Implementation Sketch

### Backend Changes
1. **Migration 082** — Add `handoff_requested_at TIMESTAMPTZ` (nullable) to `conversations` table
2. **New endpoint** `POST /api/widget/request-handoff` — accepts `{session_id, client_id, message}`
   - Updates `conversations` row: `status = 'handoff_requested'`, `handoff_requested_at = now()`
   - Sends SMS to tenant's owner_phone (via existing Twilio service) if phone configured
   - Sends email to owner_email (via existing Resend service)
   - Fires outbound webhook event `conversation.handoff_requested` (via existing webhook service)
   - Returns `{success: true, message: "We'll have someone follow up with you shortly"}`
3. **Detection in widget_helpers.py** — `_is_handoff_request(message: str) -> bool` function using keyword list: ["speak to a human", "talk to a human", "connect me", "real person", "speak to someone", "human agent", "live chat"]

### Widget Changes (minimal)
1. When AI response detects handoff intent (via backend flag in response), show confirmation button overlay
2. Button click fires `/api/widget/request-handoff`
3. Widget shows "We'll have someone follow up with you shortly" and hides the input field

### Dashboard Changes
1. Conversations with `status = 'handoff_requested'` show a yellow "Handoff Requested" badge
2. Sort: handoff conversations appear at the top of the inbox (existing sort order already supports this via status)
3. No new page needed — the existing conversations inbox handles it

---

## Skill/Agent Assignment

| Step | Agent | Tool |
|------|-------|------|
| Migration 082 | schema-guardian | migration-workflow skill |
| Backend endpoint + detection | backend-dev | feature-build skill |
| Widget UI (button + message) | widget-specialist | widget-test skill |
| Dashboard badge | frontend-dev | feature-build skill |
| End-to-end validation | qa-tester | widget-test skill |

Delegation order: schema-guardian → (backend-dev + widget-specialist) in parallel → frontend-dev → qa-tester

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Handoff requests captured in `conversations` table | ≥ 95% success rate |
| Owner notification delivered (SMS or email) | ≥ 90% delivery rate |
| Dashboard badge visible within 2s of request | 100% |
| No regression in existing chat lead capture flow | All existing widget tests pass |
| Widget smoke test: handoff request correctly handled | New test passes |

---

## What This Unlocks

After v1 ships:
- Lawyer product-market fit: 7/10 → 8/10
- Real estate product-market fit: 6/10 → 7/10
- Sales pitch becomes: "Our AI handles 80% of queries and automatically escalates the other 20% to you"
- v2 (next cycle candidate): AI-confidence-based trigger + estimated response time shown to visitor
