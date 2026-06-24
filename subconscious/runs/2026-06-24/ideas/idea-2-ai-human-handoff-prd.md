# Idea 2: Write AI-to-Human Handoff PRD/Spec

## Summary
Brain loop-status: "buildable backlog exhausted" after #367. Next product milestone is AI-to-human handoff — flagged "Critical, all industries" in `docs/dev-knowledge/customer-gaps.md`. Write `specs/ai-human-handoff_spec.md` to unblock the next build sprint.

## Evidence
- 0dc4839: brain "buildable backlog exhausted" after #367 (13 verticals)
- `docs/dev-knowledge/customer-gaps.md`: AI-to-human handoff = Critical, all industries
- 13 verticals active (roofing, home cleaning, veterinary added #367) — each needs fallback when chatbot confidence drops
- Referral pipeline complete (#371) — growth infrastructure done; product quality is the next lever
- No spec exists at `specs/ai-human-handoff_spec.md`

## What "done" looks like
`specs/ai-human-handoff_spec.md` containing:
- User stories: tenant admin sets escalation threshold; widget user triggers human escalation; context forwarded automatically
- Trigger conditions: low-confidence AI response, explicit user request ("talk to a person"), appointment type requiring custom discussion
- Delivery channels: SMS (Twilio), email (Resend), tenant configurable
- Scope: widget → backend → notification; NO new DB tables in v1 (use existing conversations + leads)
- Non-goals: real-time chat handoff, live agent dashboard (v2)
- Acceptance criteria + success metrics

## Impact
Sets the entire next build sprint. Without a spec, the backlog stays "exhausted" and the loop cycles idle.

## Effort
MEDIUM — 1-2 hours spec writing. Implementation is a separate sprint.

## Category
Product direction / customer experience
