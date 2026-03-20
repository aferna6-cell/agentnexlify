# Current Task Backlog — AgentNexLiFy

Updated by the automated morning/evening routines and interactive sessions.

## Tomorrow's Top 3 Priorities (2026-03-20)

1. **Verify Cycles 104-108 in production** — 5 feature commits today (phone/website signup, FAQ generation, click-to-call, emergency detection, business hours onboarding) need E2E verification
2. **Split api.js into domain modules** — 28 touches in 7 days, highest frontend hotspot; continued churn increases merge conflict risk
3. **Configure Cloudflare Browser Rendering env vars** — auto-crawl feature (Cycle 104) depends on this being configured

## Active Tasks

### Priority 1 — Verify Recent Features
- [ ] Verify Cycle 104: phone/website collection at signup + auto-crawl trigger
- [ ] Verify Cycle 105: industry-specific FAQ auto-generation
- [ ] Verify Cycle 106: click-to-call + SMS follow-up from lead drawer
- [ ] Verify Cycle 107: emergency lead detection, email embed, one-click review request
- [ ] Verify Cycle 108: business hours in onboarding + booking reason field

### Priority 2 — Quality
- [ ] Add contract tests for api.js flows
- [ ] Configure Cloudflare Browser Rendering env vars
- [ ] Split api.js into domain modules (28 touches in 7 days — hotspot)
- [ ] Split main.py router registration (32 touches in 7 days — hotspot)
- [ ] Verify older features in production

### Priority 3 — Feature Backlog
- [ ] Social media platform OAuth (direct posting)
- [ ] Real SERP data integration (SEMrush/Ahrefs)
- [ ] Competitor analysis dashboard
- [ ] Automated social media posting scheduler
- [ ] Documents & E-Signatures

## Completed (Recent)

### 2026-03-19 — Cycles 102-108
- [x] Verified all migrations 045-058 applied to live Supabase (Cycle 102)
- [x] Deleted `backend/routers/_widget_legacy.py` (Cycle 102)
- [x] Fixed SettingsPage.jsx silent catches (Cycle 102)
- [x] Fixed 12 critical bugs: Smart Lists, Forms, Invoices, Pipeline, Inbox (Cycle 102)
- [x] Forms HTML embed endpoint + pipeline uses backend API (Cycle 103)
- [x] Input validation fix (team.py Pydantic model) + N+1 query fix (campaign recovery) (Cycle 104)
- [x] Collect phone + website at signup, auto-crawl + SMS (Cycle 104)
- [x] Auto-generate industry-specific FAQs on signup (Cycle 105)
- [x] Click-to-call + SMS follow-up from lead detail drawer (Cycle 106)
- [x] Emergency lead detection, email embed, one-click review request (Cycle 107)
- [x] Business hours in onboarding + booking reason field (Cycle 108)
- [x] Added 6 new entries to bug-patterns.md (4 morning + 2 evening)
- [x] Updated architecture-decisions.md (3 new entries from Cycle 104)

### Previous Completed
- [x] Custom fields UI, billing matrix, upgrade prompts (Cycle 101)
- [x] CSAT, booking URL, FK fix, website_url (Cycle 100)
- [x] Facebook connect, webhook events (Cycle 99)
- [x] Omnichannel channel manager, inbox filter (Cycle 98)
- [x] Widget.py split (Cycle 97)
- [x] Public booking, two-way SMS, review automation (Cycle 96)

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
