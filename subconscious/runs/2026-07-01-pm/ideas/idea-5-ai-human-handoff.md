# Idea 5 — AI-to-Human Handoff (Customer Gap)

**Category:** customer_value  
**Effort:** M  
**Type:** HUMAN-REQUIRED  
**Score:** 5/10

## Problem

`docs/dev-knowledge/customer-gaps.md` lists AI-to-Human Handoff as CRITICAL, affecting all industries. Users want to escalate from AI chat to a live human agent (SMS, email, or phone transfer) when the widget can't resolve the query.

Open since run 4. 76+ days without implementation. 7 previous recommendation cycles — all failed delivery.

## Proposal (same as prior runs)

Backend: `POST /api/chat/handoff` endpoint that:
1. Sets `conversations.status = 'human_handoff'`
2. Sends Twilio SMS alert to tenant phone number
3. Returns handoff confirmation to widget

Frontend: handoff status indicator in dashboard live-chat view.

Widget: "Connect me to a person" button (triggers handoff flow).

## Debate Record

This idea has been killed in 7 consecutive debate rounds on grounds:
- Requires Twilio integration beyond current widget scope
- M-effort touches backend + frontend + widget simultaneously (3 surfaces)
- Moratorium active — pending_approvals prevents adding another human-required item
- No new customer escalation in evidence this run

## Decision: KILLED in debate (again)

Pattern: idea keeps surfacing because customer-gaps.md marks it CRITICAL. But CRITICAL + stalled = pattern of scope mismatch, not urgency.

**Recommendation for governance**: after run 77, if not implemented, mark `ai_human_handoff` as `frozen` in governance.json with note: "Requires dedicated sprint planning, not subconscious cycle." Remove from customer-gaps.md CRITICAL status or add `subconscious_skip: true`.
