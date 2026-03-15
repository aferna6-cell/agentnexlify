# Current Task Backlog — AgentNexLiFy

Updated by the automated morning/evening routines and interactive sessions.

## Top Priorities (2026-03-15)

1. **Apply migrations 033-038 to live Supabase** — 6 new migrations from Cycles 30-38, features broken in prod without them
2. **Clean up legacy widget files** — widget/ has stale nexlify-chat.js, nexlify-chat.src.js, README.md not in frontend/public/widget/
3. **Verify Cycles 34-38 end-to-end** — 5 feature cycles shipped yesterday, need live DB validation

## Active Tasks

### Priority 0 — Apply Now
- [ ] Apply migrations 033-038 in live Supabase (action_items, shared_inbox, team_presence, snippets, response_metrics, chat_flows)
- [ ] Clean up legacy widget files (widget/nexlify-chat.js, widget/nexlify-chat.src.js, widget/README.md)

### Priority 1 — Quality & Stability
- [ ] Fix analytics.py deprecation: `regex=` → `pattern=` in Query() calls (lines 313, 384, 475)
- [ ] Replace 5 silent frontend catches (App.jsx, BillingPage.jsx, Availability.jsx, Dashboard/OnboardingChecklist.jsx, Automations/SequenceBuilder.jsx)
- [ ] Investigate `tests/test_auth_endpoints.py::TestRegister::test_duplicate_email_returns_409` hanging under pytest
- [ ] E2E test: snippets CRUD + snippet picker in shared inbox
- [ ] E2E test: chat flow builder + flow engine in widget
- [ ] E2E test: response metrics tracking + analytics dashboard

### Priority 2 — Feature Follow-Up
- [ ] Tag definitions UI rendering in SettingsPage (state/handlers exist, JSX section may be incomplete)
- [ ] Configure Cloudflare Browser Rendering env vars (`CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`)
- [ ] E2E test: action items extraction + dashboard widget + full page
- [ ] E2E test: shared team inbox — assignment, reply, presence indicators
- [ ] E2E test: website crawl → website_content → widget prompt enrichment

### Priority 3 — Reliability
- [ ] Add contract tests for high-churn `api.js` flows (billing, webhooks, settings, content, tags)
- [ ] Re-run scheduler setup so routines pick up new CLI resolution
- [ ] Test one manual morning/evening scheduled run

### Priority 4 — Content / Docs
- [ ] Help article: "How to configure your AI assistant"
- [ ] Help article: "Understanding your analytics dashboard"

## Completed (Recent)

- [x] Chat flow engine in widget + architecture docs — Cycle 38 (2026-03-14)
- [x] AI snippet suggestion + chat flow builder backend — Cycle 37 (2026-03-14)
- [x] Analytics dashboard upgrade — Cycle 36 (2026-03-14)
- [x] Snippet picker + response time tracking — Cycle 35 (2026-03-14)
- [x] Snippets + enhanced lead capture — Cycle 34 (2026-03-14)
- [x] Shared team inbox complete — Cycle 33 (2026-03-14)
- [x] Shared team inbox — assignment, internal notes — Cycle 32 (2026-03-14)
- [x] Action items complete — Cycle 31 (2026-03-14)
- [x] Action items + tag filtering + tag analytics — Cycle 30 (2026-03-14)
- [x] AI conversation tags, AI job writer, job listings in widget — Cycle 29 (2026-03-13)
- [x] Job board module — Cycle 28 (2026-03-13)
- [x] Menu display in widget + restaurant ordering — Cycle 27 (2026-03-13)
- [x] Orders dashboard + order notifications — Cycle 26 (2026-03-13)
- [x] Menu auto-import + orders table — Cycle 25 (2026-03-13)
- [x] Restaurant menu management — Cycle 24.5 (2026-03-13)

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
