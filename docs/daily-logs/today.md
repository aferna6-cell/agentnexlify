# Daily Task List — 2026-03-12

## Health Check Results
- Frontend build: PASS (2.90s, 893KB bundle)
- Backend imports: PASS
- Dangerous imports: NONE (widget.py has comment warning only)
- Hardcoded secrets: NONE
- TODOs remaining: 0

## P0: Critical (none today)
All systems healthy.

## P1: Bug Fixes
- [x] Fix widget phone capture for international format (+1-555-123-4567, +44 20 1234 5678)
- [x] Fix dashboard timezone handling for appointment display times

## P2: Feature — Webhook Test Endpoint
- [x] Add POST /api/webhooks/{id}/test that sends a sample event to the webhook URL
- [x] Add "Test" button in dashboard webhook management UI

## P3: Tests for Critical Paths
- [x] Test signup flow with duplicate email (32 tests total, all passing)
- [x] Test chat endpoint with empty message body
- [x] Test lead capture with partial info (name only, no email)
- [ ] Test appointment booking with overlapping time slots

## P4: Content
- [x] Write welcome email for new signups
- [x] Write "How to embed the widget" help article

## P5: Optimization
- [ ] Frontend bundle code-splitting (893KB → target <500KB per chunk)

---
Generated: 2026-03-12 morning session
