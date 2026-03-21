# Current Task Backlog — AgentNexLiFy

Updated by the automated morning/evening routines and interactive sessions.

## Tomorrow's Top 3 Priorities (2026-03-22)

1. **Verify Cycles 116-125 in production** — 10 feature commits need E2E verification (service types, pipeline presets, AI summaries, form presets, etc.)
2. **Simulate another business type** — Salon or fitness studio walkthrough
3. **Split api.js into domain modules** — Critical hotspot (~35 touches in 7 days)

## Active Tasks

### Priority 1 — Verify Recent Features
- [ ] Verify service types CRUD + public endpoint
- [ ] Verify pipeline presets auto-seed for different business types
- [ ] Verify AI conversation summary on lead cards
- [ ] Verify form presets (dental intake, medical, contractor)
- [ ] Verify insurance fields in LeadDetailDrawer
- [ ] Verify dental-aware reminders + rebook automation
- [ ] Verify webhook schema endpoint (14/14 events documented)

### Priority 2 — Quality & Refactoring
- [ ] Split api.js into domain modules (critical hotspot)
- [ ] Split main.py router registration (critical hotspot)
- [ ] Fix 11 remaining test isolation failures

### Priority 3 — Feature Backlog
- [ ] Two-way email sync
- [ ] White-label client login
- [ ] Social media platform OAuth
- [ ] Service type selector in widget booking form UI

## Completed Today (2026-03-21) — 10 cycles, 10 commits

### Build Loop (Cycles 116-125)
- [x] Fixed 65 broken tests — 237 now pass (Cycle 116)
- [x] Dental-aware appointment reminders for 9 business types (Cycle 117)
- [x] Rebook automation: dental 180d, salon 42d, medical 365d, fitness 30d (Cycle 117)
- [x] Form presets: dental intake, medical intake, contractor estimate (Cycle 118)
- [x] HIPAA-aware AI system prompt for healthcare businesses (Cycle 118)
- [x] Insurance fields on leads: migration 062 (Cycle 119)
- [x] Real estate agent simulation: 8 gaps documented (Cycle 120)
- [x] 5 new real estate FAQs on signup (Cycle 120)
- [x] Industry pipeline presets for 6 types + 9 aliases (Cycles 121, 124)
- [x] Complete webhook schema: 14/14 events documented (Cycle 122)
- [x] Lead source tracking: booking, missed_call sources (Cycle 122)
- [x] AI conversation summary on lead cards + generate endpoint (Cycle 123)
- [x] CLAUDE.md: 8 missing tables added to schema docs (Cycle 123)
- [x] Service types for booking: migration 063 (Cycle 125)

### Milestones
- ALL dental simulation gaps closed (7/7)
- ALL plumber simulation gaps closed (15/15)
- 3 customer simulations completed (plumber, dental, real estate)
- 4 migrations applied (059-063)
- 237 tests passing (recovered 65 from widget split)

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
