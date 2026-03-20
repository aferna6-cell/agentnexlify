# Current Task Backlog — AgentNexLiFy

Updated by the automated morning/evening routines and interactive sessions.

## Tomorrow's Top 3 Priorities (2026-03-21)

1. **Verify Cycles 104-115 in production** — 12 feature commits need E2E verification (documents, invoices, onboarding, widget changes)
2. **Fix test_login_and_chat.py** — 50 test errors from widget module split (pre-existing since Cycle 97)
3. **Dental-aware appointment reminders** — Highest-impact gap from dental simulation

## Active Tasks

### Priority 1 — Verify Recent Features
- [ ] Verify DocumentsPage renders, create/send works
- [ ] Verify invoice item templates (Saved Items dropdown)
- [ ] Verify deposit amount + partial payment recording
- [ ] Verify recurring invoice toggle on create form
- [ ] Verify onboarding wizard: hours step, services input, textback toggle
- [ ] Verify widget booking "Reason for Visit" field
- [ ] Verify "Email to Developer" button on WidgetPage
- [ ] Verify "Request Review" button on LeadDetailDrawer
- [ ] Verify emergency lead detection scoring
- [ ] Verify dental FAQs auto-generated on dental signup

### Priority 2 — Quality & Refactoring
- [ ] Fix test_login_and_chat.py (50 errors from widget split)
- [ ] Split api.js into domain modules (critical hotspot)
- [ ] Split main.py router registration (critical hotspot)
- [ ] Add contract tests for api.js flows
- [ ] Configure Cloudflare Browser Rendering env vars

### Priority 3 — Feature Backlog (from simulations)
- [ ] Dental-aware appointment reminders
- [ ] Rebook automation (6-month dental cleanings)
- [ ] Patient intake form preset (dental/healthcare)
- [ ] Insurance fields in leads
- [ ] HIPAA compliance messaging
- [ ] Service-based slot duration
- [ ] Social media platform OAuth (direct posting)

## Completed Today (2026-03-20)

### Evening Review
- [x] Bug-patterns.md: added Field import bug entry
- [x] Health check: all green (0 dangerous imports, 0 bare excepts, widget synced, build passes, 172 tests pass)
- [x] No new commits today (build loop ran yesterday evening)

### Morning (Automated)
- [x] Morning startup doc generated
- [x] 3 new bug-patterns entries from Cycles 114-115

### Yesterday (2026-03-19) — 15 commits, Cycles 102-115
- [x] 12 critical bug fixes (Cycle 102)
- [x] Forms embed + pipeline refactor (Cycle 103)
- [x] Signup phone/website + plumber simulation (Cycle 104)
- [x] Industry FAQs on signup (Cycle 105)
- [x] Click-to-call + SMS follow-up (Cycle 106)
- [x] Emergency detection + email embed + review request (Cycle 107)
- [x] Business hours in onboarding + booking reason (Cycle 108)
- [x] Services list + textback + security hardening (Cycle 109)
- [x] Invoice item library (Cycle 110)
- [x] Deposit/partial payments + recurring invoices (Cycle 111)
- [x] Documents backend + migration 061 (Cycle 112)
- [x] Documents frontend + sidebar (Cycle 113)
- [x] 11 tests + route fix + Field import fix (Cycle 114)
- [x] Dental simulation + FAQs + dead code (Cycle 115)

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
