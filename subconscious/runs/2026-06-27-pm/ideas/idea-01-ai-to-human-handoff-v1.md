# Idea 01: AI-to-Human Handoff v1 (Explicit Trigger)

**Category:** customer_value
**Effort:** M (~1 day, reduced from 1.5-2d by os_outbound_mirror.py)
**ROI:** 3.2 (Critical gap, all 7 industries, infrastructure now ready)
**Age:** 72 days pending (run 4, 2026-04-16)
**Autonomous:** No — human required

## Evidence

- Run 4 winner (2026-04-16) — 72 days pending as of run 70
- `docs/dev-knowledge/customer-gaps.md`: AI-to-Human Handoff listed as CRITICAL gap, all 7 industries, Medium effort
- `os_outbound_mirror.py` merged PR #188 (2026-05-27) — 152 tests, handles SMS + email outbound delivery
- Council sprint (9 commits, 2026-06-24 to 2026-06-27) proves human is actively building
- run 38 direction already has full implementation sketch via Agent OS infrastructure
- Scope shrinks from 1.5-2 days (run 4 estimate) to ~1 day (os_outbound_mirror.py eliminates delivery layer build)

## What

When a user in the widget chat says "talk to a person", "real person", "human", "speak to someone", or similar:
1. Detect trigger string in `backend/routers/widget_chat.py` or AI response parser
2. Write `handoff_requests` table row (conversation_id, client_id, timestamp, trigger_phrase, status='pending')
3. Notify business owner via SMS + email using `os_outbound_mirror.py`
4. Widget shows: "Request received — someone will follow up shortly"
5. Dashboard: new "Handoff Requests" indicator (badge on sidebar)

## Files to Touch

- `migrations/155_handoff_requests.sql` — new table
- `backend/routers/widget_chat.py` — detect trigger, write handoff_requests, call outbound mirror
- `backend/services/handoff_service.py` — new file, business logic
- `frontend/src/pages/ConversationsPage.jsx` — add handoff badge/indicator
- `widget/agentnexlify-widget.js` + `frontend/public/widget/` — "Request Human" button (optional v1 scope)

## Why Now

1. 72-day gap — oldest pending direction in governance. Moratorium forces a choice.
2. os_outbound_mirror.py is the missing piece. Run 4 estimate was high because delivery layer didn't exist.
3. Council sprint proves development velocity is high (9 fixes in 4 days).
4. Customer gaps doc confirms critical for ALL 7 industries — broadest impact in backlog.
5. Atomic: single-session implement (does not require Agent OS full deployment).

## Risk

- `handoff_requests` table needs migration (must be numbered 155 or next available)
- `os_outbound_mirror.py` interface must be confirmed before calling it
- Widget change requires byte-identical sync to `landing-page-v2/` (defer to v2 — widget button is optional v1 scope)
- Moratorium-blocked (true_pending ~6 > max_pending_approvals:2) — needs human sprint to exit moratorium first OR moratorium override

## Debate Position

**STRONGEST candidate.** First new winner since widget drift loop began (runs 65-70). Infrastructure ready. 72-day gap is the longest-standing item. Critical all industries. ~1 day scope.
