# Current Task Backlog — AgentNexLiFy

Updated: 2026-04-06 (automated evening review)

## Tomorrow's Top 3 Priorities

1. **Apply migration 090 (autopilot plan CHECK constraint)** — Actively causing DB errors on autopilot subscription creation. Zero-risk migration (just adds a value to CHECK). Apply immediately. Agent: **schema-guardian**.
2. **Apply remaining pending migrations (065-070, 077-079, 083-089, 091-092)** — 18 total pending is unsustainable. Prioritize: 077-079 (onboarding blockers), 091 (RLS for new tables), then the rest. Agent: **schema-guardian**.
3. **QA marketing infrastructure** — A/B testing, automation rules, marketing dashboard, weekly growth endpoint all shipped today with no QA. End-to-end test the full marketing flow. Agent: **qa-tester**.

## Active Tasks

### Priority 0 — Schema (Critical / Pre-Launch Blocker)

- [ ] **Apply migration 090 (autopilot plan)** — autopilot subscriptions fail at DB level. Created 2026-04-06. Agent: **schema-guardian** → apply immediately.
- [ ] **Apply migration 077 (widget knowledge_base)** — blocks onboarding wizard KB injection. Created 2026-04-01. Agent: **schema-guardian**.
- [ ] **Apply migration 078 (business_type constraint)** — blocks new signups for 17 industries. Created 2026-04-01. Agent: **schema-guardian**.
- [ ] **Apply migration 079 (wizard_events)** — blocks wizard funnel analytics. Created 2026-04-01. Agent: **schema-guardian**.
- [ ] **Apply migration 091 (RLS for 086-089)** — new tables have no RLS until this is applied. Created 2026-04-06. Agent: **schema-guardian**.

### Priority 1 — Critical / Blocking

- [ ] **Apply migrations 065-070** — client_accounts, waitlist, scoring_configs, invoice unique, email bounce, pipeline automations. 14+ days stale. Duplicate files at 066/067/068 were renumbered to 083/084/085 on 2026-04-05. Agent: **schema-guardian**.
- [ ] **Apply migrations 083-089, 092** — waitlist, scoring configs, password reset, A/B tests, automation rules, campaign analytics, admin tracking, reminder tracking. Agent: **schema-guardian**.
- [ ] **QA marketing infrastructure (shipped 2026-04-06)** — A/B testing (ABTestsPage, ab_tests router), automation rules (AutomationRulesPage, automation_rules router), marketing dashboard (MarketingDashboardPage, marketing_analytics/campaigns routers), weekly growth endpoint. Zero QA so far. Agent: **qa-tester**.
- [ ] **Verify security fixes (2026-04-06)** — 29 vulnerabilities patched (95199cf) + audit findings (1ef217d). Check for regressions. Agent: **qa-tester**.

### Priority 2 — Verification & QA

- [ ] **End-to-end test onboarding wizard** — 6-step wizard shipped 2026-04-01. Needs QA: real signup flow, JWT parsing race condition, /onboarding route guard, KB generation, widget embed code. Agent: **qa-tester**.
- [ ] **Verify expired JWT token handling (6d10cf5)** — 401 interceptor + proactive expiry check added today. Test: let JWT expire, confirm redirect to login. Agent: **qa-tester**.
- [ ] **Production verification of March 25 features** — Revenue analytics, pipeline automations, webhook deliveries, password reset flow: **12+ days unverified.** Agent: **qa-tester**.
- [ ] **Audit `.get() or ""` operator precedence pattern** — 3 fixed, likely more. Run: `grep -rn '\.get(.*) or .*==' backend/`. Agent: **qa-tester**.
- [ ] **Reduce silent frontend catches (4 truly silent, 62 total)** — onboarding.js, ClientLoginPage.jsx, MarketingCampaignsPage.jsx, WizardStepEmbed.jsx. Agent: **frontend-dev**.

### Priority 3 — Knowledge & Documentation

- [ ] **Enrich auto-logged bug patterns (#30-41 + #42-45)** — 16 skeleton entries need human enrichment for root cause details. Carried forward since 2026-03-24.

### Priority 4 — Carried Forward

- [ ] **Two-way email sync** — still pending from previous backlog
- [ ] **Fix 16 test isolation failures** — partially addressed by d1a36c6 (12 files patched), may still have remaining failures
- [ ] **Automated routine reliability** — March 26 evening and March 27 morning both failed due to usage limits. Morning routine did not run today (2026-04-06). Consider scheduling adjustments or retry mechanism.

## Completed (Recent) — 2026-04-06 (Evening Auto)

- [x] **Marketing infrastructure shipped** — A/B testing, automation rules, marketing dashboard, weekly growth endpoint, campaigns analytics (5c3f520, 40f0870)
- [x] **Platform admin analytics** — admin analytics page, promotions management, tenant tracking columns (9c87335)
- [x] **Security: 29 vulnerabilities fixed** — backend, frontend, and migrations (95199cf)
- [x] **Audit findings addressed** — secret leak, broken inserts, filter sanitization, rate limits (1ef217d)
- [x] **Expired JWT handling** — 401 interceptor + proactive expiry check (6d10cf5)
- [x] **Stalled campaign detection fixed** — now uses sending_started_at (72ed91e)
- [x] **Autopilot plan constraint** — migration 090 created (31761c0) — pending apply
- [x] **Test quality gates** — JS coverage scripts, diff coverage gates, mutation testing, ESLint test quality plugin (5eb7054, b5d8bcd, ce02631, 17c4656)
- [x] **Graphify knowledge graph** — full codebase indexed (6521cea)
- [x] **Subconscious self-improvement** — lead source analytics chart added (555b547)
- [x] **7 new migrations created** — 086-092

## Completed (Recent) — 2026-04-03 (Morning Auto)

- [x] **4 bug fixes documented in bug-patterns.md** — IDOR in auto_populate_kb, operator precedence in restaurant check, widget CSS visibility, null-state guard.
- [x] **Daily log created** — docs/daily-logs/2026-04-03.md with health check results.

## Overall Progress

- 24 commits today (5 fixes, 6 features, 1 security, 4 test/quality, 8 auto-commits)
- 105 files changed today
- **18 pending migrations (065-070, 077-079, 083-092)** — critical, growing unsustainably
- 4 silent frontend catches (unchanged)
- 0 bare excepts, 0 dangerous imports
- Widget files in sync
- **Hot zones today:** backend/main.py, backend/config.py, frontend/src/components/App.jsx — high churn across multiple commits

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
