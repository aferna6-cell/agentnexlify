# Work Backlog

The loop reads this file every cycle and picks the highest-priority incomplete task.
Add tasks anytime — the loop picks them up on the next cycle.

## Features (build these)

- [x] Hosted business page — public page at /biz/{slug} showing business info, widget, booking — already built (migrations 009-010, backend, frontend, settings) verified 2026-03-12
- [ ] Stripe subscription management in dashboard — upgrade/downgrade/cancel
- [x] Webhook test endpoint — let users send a test event to verify their webhook URL — done 2026-03-12
- [ ] Email template editor — visual editor for automation email steps
- [ ] Lead import via CSV — upload leads in bulk
- [ ] Dashboard notification center — in-app notifications for new leads, appointments, etc.
- [ ] Widget file/image upload — let visitors send screenshots or documents in chat
- [ ] Conversation tagging — tag/label conversations for organization
- [ ] Lead merge — combine duplicate leads into one record

## Bugs (fix these)

- [x] Widget not capturing phone numbers with country codes (international format) — fixed 2026-03-12
- [x] Dashboard analytics may show wrong timezone for appointment times — fixed 2026-03-12

## Tests (write these)

- [x] Test signup flow with duplicate email — done 2026-03-12
- [x] Test chat endpoint with empty message body — covered in lead extraction tests 2026-03-12
- [x] Test lead capture with partial info (name but no email) — done 2026-03-12
- [x] Test appointment booking with overlapping time slots — done 2026-03-12 (12 tests: slot gen, overlap detection, lead linkage, appointment creation)
- [x] Test webhook delivery and retry logic — done 2026-03-12 (18 tests: HMAC signing, daily limits, fire_event, delivery + retry)
- [x] Test Stripe webhook signature verification — done 2026-03-12 (7 tests: sig validation, event routing, error handling)
- [ ] Test widget CORS from external domain
- [ ] Test automation sequence execution order

## Content (generate these)

- [x] Welcome email for new signups — done 2026-03-12
- [x] "How to embed the widget" help article — done 2026-03-12
- [ ] "How to read your dashboard" help article
- [ ] Day 2 onboarding email — tips for first conversations
- [ ] Day 7 check-in email — are you seeing leads?
- [ ] 5 social media posts about the product
- [ ] FAQ entries for common widget questions

---

_Mark tasks `[x]` when complete. Add new tasks anytime._
