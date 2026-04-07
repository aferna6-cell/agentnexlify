# Current Task Backlog — AgentNexLiFy

Updated: 2026-04-07 (automated morning review)

## Tomorrow's Top 3 Priorities

1. **Rotate compromised admin API key in Railway** — Real key `ab0lhhx7UC...` was committed in 9c87335 and scrubbed in d4463d7, but the key is still live in Railway. Must be rotated immediately. Agent: **devops**.
2. **Apply pending migrations (090, 093, 077-079, 083-089, 091-092)** — 19 total pending. Priority order: 090 (autopilot plan — actively breaking), 093 (RLS fix — security), 077-079 (onboarding blockers), 083-089 (batch), 091-092 (audit/reminders). Agent: **schema-guardian**.
3. **QA marketing infrastructure** — A/B testing, automation rules, marketing dashboard, weekly growth endpoint shipped 2026-04-06 with zero QA. Agent: **qa-tester**.

## Active Tasks

### Priority 0 — Security (Immediate Action Required)

- [ ] **ROTATE compromised API key in Railway** — Key committed in 9c87335, scrubbed in d4463d7. Key is still live. This is a security incident — rotate now. Agent: **devops**.

### Priority 0 — Schema (Critical / Pre-Launch Blocker)

- [ ] **Apply migration 090 (autopilot plan)** — autopilot subscriptions fail at DB level. Created 2026-04-06. Agent: **schema-guardian** → apply immediately.
- [ ] **Apply migration 093 (fix RLS policies)** — migration 091's auth.uid() policies are semantically broken. Created 2026-04-07. Agent: **schema-guardian**.
- [ ] **Apply migration 077 (widget knowledge_base)** — blocks onboarding wizard KB injection. Created 2026-04-01. Agent: **schema-guardian**.
- [ ] **Apply migration 078 (business_type constraint)** — blocks new signups for 17 industries. Created 2026-04-01. Agent: **schema-guardian**.
- [ ] **Apply migration 079 (wizard_events)** — blocks wizard funnel analytics. Created 2026-04-01. Agent: **schema-guardian**.

### Priority 1 — Critical / Blocking

- [ ] **Apply migrations 083-092** — waitlist, scoring configs, password reset, A/B tests, automation rules, campaign analytics, admin tracking, reminder tracking, autopilot plan, RLS guards. Agent: **schema-guardian**.
- [ ] **Apply migrations 065-070** — client_accounts, waitlist(old), scoring_configs(old), invoice unique, email bounce, pipeline automations. 15+ days stale. Agent: **schema-guardian**.
- [ ] **QA marketing infrastructure (shipped 2026-04-06)** — A/B testing (ABTestsPage, ab_tests router), automation rules (AutomationRulesPage, automation_rules router), marketing dashboard (MarketingDashboardPage, marketing_analytics/campaigns routers), weekly growth endpoint. Zero QA so far. Agent: **qa-tester**.
- [ ] **Verify security fixes (2ab39dd + d7572eb)** — 19 security/data integrity issues patched overnight. Check for regressions. Agent: **qa-tester**.

### Priority 2 — Verification & QA

- [ ] **End-to-end test onboarding wizard** — 6-step wizard shipped 2026-04-01. Needs QA: real signup flow, JWT parsing race condition, /onboarding route guard, KB generation, widget embed code. Agent: **qa-tester**.
- [ ] **Verify expired JWT token handling (6d10cf5)** — 401 interceptor + proactive expiry check added 2026-04-06. Test: let JWT expire, confirm redirect to login. Agent: **qa-tester**.
- [ ] **Production verification of March 25 features** — Revenue analytics, pipeline automations, webhook deliveries, password reset flow: **13+ days unverified.** Agent: **qa-tester**.
- [ ] **Audit `.get() or ""` operator precedence pattern** — 3 fixed, likely more. Run: `grep -rn '\.get(.*) or .*==' backend/`. Agent: **qa-tester**.
- [ ] **Reduce silent frontend catches (4 truly silent, ~4 total)** — onboarding.js, ClientLoginPage.jsx, MarketingCampaignsPage.jsx, WizardStepEmbed.jsx. Agent: **frontend-dev**.

### Priority 3 — Knowledge & Documentation

- [ ] **Enrich auto-logged bug patterns (#30-41)** — 12 skeleton entries still need human enrichment for root cause details. Carried forward since 2026-03-24.
- [ ] **New patterns (#46-57) added today** — fully documented from commit messages but may benefit from human review.

### Priority 4 — Carried Forward

- [ ] **Two-way email sync** — still pending from previous backlog
- [ ] **Fix 16 test isolation failures** — partially addressed by d1a36c6 (12 files patched), may still have remaining failures
- [ ] **Automated routine reliability** — March 26 evening and March 27 morning both failed; April 6 morning did not run. Consider scheduling adjustments.

## Completed (Recent) — 2026-04-07 (Morning Auto)

- [x] **Morning health check run** — all clear (0 bare excepts, 0 dangerous imports, 0 TODO/FIXME, widget in sync, .env gitignored)
- [x] **12 new bug patterns documented (#46-57)** — overnight security audit commits fully documented in bug-patterns.md
- [x] **Migration 093 documented in schema-log.md** — new corrective RLS migration logged
- [x] **Daily log created** — docs/daily-logs/2026-04-07.md

## Completed (Recent) — 2026-04-06 (Evening Auto)

- [x] **Marketing infrastructure shipped** — A/B testing, automation rules, marketing dashboard, weekly growth endpoint, campaigns analytics (5c3f520, 40f0870)
- [x] **Platform admin analytics** — admin analytics page, promotions management, tenant tracking columns (9c87335)
- [x] **Security: 29 vulnerabilities fixed** — backend, frontend, and migrations (95199cf)
- [x] **Audit findings addressed** — secret leak, broken inserts, filter sanitization, rate limits (1ef217d)
- [x] **Expired JWT handling** — 401 interceptor + proactive expiry check (6d10cf5)
- [x] **Stalled campaign detection fixed** — now uses sending_started_at (72ed91e)
- [x] **Autopilot plan constraint** — migration 090 created (31761c0) — pending apply
- [x] **Test quality gates** — JS coverage scripts, diff coverage gates, mutation testing, ESLint test quality plugin
- [x] **Graphify knowledge graph** — full codebase indexed (6521cea)
- [x] **7 new migrations created** — 086-092

## Overall Progress (2026-04-07 Morning)

- **Overnight commits:** 11 (2 security+fix batches, 1 secret scrub, 1 feature, 2 chore, 1 hooks, 1 discipline, 1 Claudeopedia, 1 wiki viewer)
- **Hot zones (7-day):** backend/main.py (13x), automation_engine.py (11x), widget_chat.py (10x), analytics.py (10x), onboarding.py (10x)
- **19 pending migrations** — growing unsustainably, critical
- **0 bare excepts, 0 dangerous imports, 0 TODO/FIXME**
- **4 silent frontend catches** (unchanged)
- **Widget files in sync** (identical content)
- **SECURITY INCIDENT:** admin API key committed to .env.example — rotate in Railway immediately

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
