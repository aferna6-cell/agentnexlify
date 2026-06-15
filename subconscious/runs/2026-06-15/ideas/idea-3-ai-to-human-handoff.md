### Idea 3: AI-to-Human Handoff v1 — explicit trigger detection + owner notification

**Evidence:** Run 4 winner (2026-04-16), 60 days pending. customer-gaps.md: "Critical for complex queries" across ALL 7 industries. Run 38 (2026-05-28) scoped: os_outbound_mirror.py (PR #188, merged) handles SMS/email — changed implementation from ~3 days to ~1 day. Widget leads that hit edge cases or demand human contact currently hit a wall: the AI loops or apologizes, no human notified, lead lost.

**Action:** Add `_detect_handoff_trigger()` to widget_chat.py: scan for "talk to someone", "real person", "call me", "this isn't helping", etc. On match: write `handoff_requests` table row (lead_id, trigger_phrase, conversation_id, tenant_id), call `os_outbound_mirror.notify_owner()` (SMS + email). Requires migration 150_handoff_requests.sql.

**Impact:** Converts currently-lost leads on complex queries into owner-notified leads. Customer-gap CLOSED for all 7 industries. Highest customer value item in backlog.

**Category:** customer_value
