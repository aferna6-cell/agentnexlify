# Idea 3: AI-to-Human Handoff v1

**Category**: customer_value  
**Confidence**: MEDIUM  
**Effort**: M (~1 day, multi-file)  
**Autonomous**: NO — requires product decisions + human implementation  
**Age**: Run 4, 2026-04-16 — 69 days pending as of 2026-06-24

## What is missing

No mechanism for the chat widget to hand off a conversation to a human agent. When a user types "I want to talk to a person" or "let me speak to someone" or asks something the bot cannot handle confidently, the conversation continues with the AI — no escalation path.

Critical gap across all 7 SMB verticals (salon, plumber, dental, legal, contractor, HVAC, restaurant).

## Implementation path (via os_outbound_mirror.py)

Agent OS PR #188 merged 2026-05-27 — `backend/services/os_outbound_mirror.py` handles SMS/email/FB with 152 tests. Changes scope from ~3 days (build plumbing from scratch) to ~1 day (routing decision + trigger detection).

1. **Trigger detection** in `backend/routers/widget_chat.py`: scan message for explicit trigger strings ("talk to a person", "speak to someone", "human agent", "call me", etc.) OR low-confidence widget response (below threshold)
2. **Create `handoff_requests` table** (migration): `id`, `client_id`, `conversation_id`, `lead_id`, `trigger_reason`, `status`, `created_at`
3. **Notify owner** via `os_outbound_mirror.py`: SMS to tenant owner + email fallback (Resend)
4. **Lead status update**: `needs_follow_up` on the leads table
5. **Widget response**: "I've notified [Business Name] and someone will reach out to you shortly."

## Why not winner this run

- M-effort (1 day), requires human approval + implementation
- No new evidence since run 38 (last time this was winner)
- Run 65 has a more urgent blocker (pre-commit blocked)
- Infrastructure readiness hasn't changed since run 38

## Standing action

Run 4 item — 69 days pending. Remains highest-priority customer-value item. Critical for every paid tenant. Should be winner within next 3 runs once pre-commit unblocks and plan-name guard lands.

## Implementation sketch

Full implementation sketch: `subconscious/runs/2026-05-28-pm/winning-concept.md` (run 38 canonical).
