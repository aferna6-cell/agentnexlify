# Current Task Backlog — AgentNexLiFy

Updated by the automated morning/evening routines and interactive sessions.

## Top Priorities (2026-03-14)

1. **Commit and push all uncommitted work** — 20 files, 3 features, infrastructure updates sitting uncommitted
2. **Apply migrations 025-032 in live Supabase** — 8 pending, features broken in prod without them
3. **Fix frontend silent catches + analytics.py deprecation** — quality/reliability cleanup

## Active Tasks

### Priority 0 — Ship Now
- [ ] Commit all uncommitted changes (tag definitions, AI job writer, job listings in widget, infrastructure)
- [ ] Apply and verify migrations 025-032 in live Supabase
- [ ] Push to Railway/Vercel

### Priority 1 — Quality & Stability
- [ ] Fix analytics.py deprecation: `regex=` → `pattern=` in Query() calls (lines 313, 384, 475)
- [ ] Replace 5 silent frontend catches (App.jsx, BillingPage.jsx, Availability.jsx, Dashboard/OnboardingChecklist.jsx, Automations/SequenceBuilder.jsx)
- [ ] Investigate `tests/test_auth_endpoints.py::TestRegister::test_duplicate_email_returns_409` hanging under pytest
- [ ] E2E test: tag auto-categorization flow (widget chat → background categorize → conversations.tags)
- [ ] E2E test: AI job writer endpoint → job form population
- [ ] E2E test: job listings visible in widget chat responses

### Priority 2 — Feature Follow-Up
- [ ] Tag definitions UI rendering in SettingsPage (state/handlers exist, JSX section may be incomplete)
- [ ] Configure Cloudflare Browser Rendering env vars (`CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`)
- [ ] E2E test: website crawl → `website_content` storage → widget prompt enrichment
- [ ] Re-run scheduler setup so routines pick up new CLI resolution
- [ ] Test one manual morning/evening scheduled run

### Priority 3 — Reliability
- [ ] Add contract tests for high-churn `api.js` flows (billing, webhooks, settings, content, tags)
- [ ] Clean up legacy widget files (`widget/nexlify-chat.js`, `widget/nexlify-chat.src.js`)

### Priority 4 — Content / Docs
- [ ] Help article: "How to configure your AI assistant"
- [ ] Help article: "Understanding your analytics dashboard"

## Completed (Recent)

- [x] AI conversation auto-categorization in widget (2026-03-13, uncommitted)
- [x] Tenant tag definitions CRUD — backend + frontend + migration 032 (2026-03-13, uncommitted)
- [x] AI job writer endpoint + frontend UI (2026-03-13, uncommitted)
- [x] Job listings in widget system prompt (2026-03-13, uncommitted)
- [x] Daily routine infrastructure: common.sh, health-check.sh, scheduler fixes (2026-03-12, uncommitted)
- [x] Content Studio — full module (2026-03-12)
- [x] Reputation Manager — reviews, AI drafting, auto requests, analytics (2026-03-12)
- [x] Team permissions enforcement on all write endpoints (2026-03-12)
- [x] Lead assignment to team members (2026-03-12)
- [x] AI response tuning with thumbs up/down (2026-03-12)
- [x] Stripe subscription management inline (2026-03-12)
- [x] 97 tests passing (2026-03-12)
- [x] Frontend code-splitting pass (2026-03-12)
- [x] Migration 032 documented in schema-log.md (2026-03-13)

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
