# Current Task Backlog — AgentNexLiFy

Updated by the automated morning/evening routines and interactive sessions.

## Top Priorities

1. Document 6 undocumented bug fixes in bug-patterns.md
2. Build webhook test endpoint (backend + frontend)
3. Write integration tests for critical paths

## Active Tasks

### Priority 1 — Documentation Gaps
- [ ] Document recent bug fixes in bug-patterns.md (6 missing entries)

### Priority 2 — Feature Work
- [ ] Webhook test endpoint — POST /api/webhooks/{id}/test + dashboard button
- [ ] Hosted business page — public page at /biz/{slug}
- [ ] Stripe subscription management in dashboard

### Priority 3 — Tests
- [ ] Test signup flow with duplicate email
- [ ] Test chat endpoint with empty message body
- [ ] Test lead capture with partial info

### Priority 4 — Content
- [ ] Welcome email for new signups
- [ ] Help articles: embed widget, read dashboard

### Priority 5 — Optimization
- [ ] Frontend bundle code-splitting (893KB)
- [ ] Clean up legacy widget files (widget/nexlify-chat.*)

## Completed (Recent)

- [x] Fix international phone capture in widget (2026-03-12)
- [x] Fix appointment timezone display in Calendar + TodayAppointments (2026-03-12)
- [x] Twilio validation, HTTPS webhooks, rate limiting (2026-03-11)
- [x] SMS rate limit from live DB, TeamPage guard (2026-03-11)
- [x] Sequence builder wrong stages, Google Calendar dedup (2026-03-11)
- [x] Harden API endpoints — input validation, error sanitization (2026-03-11)
- [x] Wrong model IDs, invalid plan fallback, deprecated asyncio (2026-03-11)
- [x] Payment failure email notification + live schema audit (2026-03-11)
- [x] Exception handling cleanup, automation template bug (2026-03-11)
- [x] Pre-commit and pre-push hook improvements (2026-03-11)

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
