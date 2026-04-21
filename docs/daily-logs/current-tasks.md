# Current Task Backlog — AgentNexLiFy

Updated: 2026-04-21 08:00 EDT (automated morning routine)

## Today's Top 3 Priorities

1. **ROTATE compromised admin API key in Railway** — DAY 18 of exposure. Key committed `9c87335`, scrubbed `d4463d7`. Still live in Railway. **CRITICAL — HUMAN ACTION REQUIRED.** Agent: **devops** / Human.
2. **QA migrations 108, 109, 110 applied 2026-04-20** — photo-quote widget tables (`tenant_pricing_rules`, `quote_requests`, `tenant_quote_usage`), drive-kb integrations (`tenant_integrations`, `integration_sync_log`, `kb_section_hashes`), zapier api keys (`tenant_api_keys`). Agent: **schema-guardian** + **qa-tester**.
3. **Verify issue-to-pr loop stability** — 4 patches on `scripts/automation/issue-to-pr.sh` 2026-04-20 (611c052, 0632799, 4d2b4be, be135eb). Add smoke-test harness + dry-run end-to-end. Agent: **devops** + **qa-tester**.

## Active Tasks

### Priority 0 — Security (Immediate Action Required)

- [ ] **ROTATE compromised API key in Railway** — Key still live. DAY 18 of exposure. Agent: **devops** / Human.
- [ ] **Reattach HEAD to main + push 2026-04-17 work** — Verify `git branch --show-current == main` and `git status` clean. (Carried)

### Priority 0 — Schema (Pre-Launch)

- [ ] **Verify migration 102 applied in prod** — `marketing_addon_*` columns on `tenants`. Log entry says "status unknown — backfill only". Agent: **schema-guardian**.
- [ ] **Verify migrations 103/104/105 applied in prod** — Flags + enrichment source. Agent: **schema-guardian**.

### Priority 1 — Critical / QA

- [ ] **QA migrations 108/109/110 production paths** — photo-quote, drive-kb, zapier api keys. Agent: **schema-guardian** + **qa-tester**. (New 2026-04-21)
- [ ] **QA migrations 106 + 107 production paths** — AI usage budget reservation, refund idempotency, dunning event log, cancellation event history. Agent: **schema-guardian** + **qa-tester**. (Carried)
- [ ] **QA invariants expansion (fac6124)** — conversations.tenant_id guard added to `check_project_invariants.py`. Exercise CI path; confirm auto-hook fails a synthetic bad commit. Agent: **qa-tester**. (New 2026-04-21)
- [ ] **QA branding_helpers.py extraction (5f7117f)** — Reverse-dep fix. Ensure widget chat helpers still resolve branding correctly. Agent: **widget-specialist**. (Carried)
- [ ] **QA widget_chat_helpers shim removal (d2ab107)** — Middle-hop shim dropped (Rule 8 no half-migrations). Verify all old import paths resolve via new layout. Agent: **backend-dev**. (Carried)
- [ ] **QA widget_helpers god-class split (6cf4646)** — 1,673-LOC split into 3 modules. Cross-origin embed + booking + lead capture need prod smoke. Agent: **widget-specialist**. (Carried)
- [ ] **QA conftest TESTING + JWT secret env fix (9812fee, 0d94833)** — Verify full backend pytest green in CI. Agent: **qa-tester**. (Carried)
- [ ] **QA business-type personalization (ad88397)** — Industry-aware widget + dashboard behavior. Agent: **qa-tester**. (Carried)
- [ ] **QA launch risk guardrails (99f8442)** — AI cost caps, refund audit, dunning events. Agent: **qa-tester**. (Carried)
- [ ] **QA service-layer extraction** — `ff293f4` branding/faq/conversations. Agent: **qa-tester**. (Carried)
- [ ] **QA scheduled_jobs.py split** — 5 modules: appointment/billing/email/lead/review. Cron paths re-verified. Agent: **qa-tester**. (Carried)
- [ ] **QA Stripe marketing addon readiness guard** — `0278eb0` + `0482f7d`. Agent: **qa-tester**. (Carried)
- [ ] **Act on launch-readiness rubric 114/262 NO-GO findings** — Dispute threshold 0.50%. Remaining fix-list needs execution. (Carried)
- [ ] **QA tenant_scope adoption + CORS fix** — 60+ routers, CORS `["*"]`. Cross-tenant leak = critical. Agent: **qa-tester**. (Carried)
- [ ] **QA industry packs** — 14 modules landed `881e026`. Agent: **qa-tester**. (Carried)
- [ ] **QA marketing infrastructure** — A/B tests, automation rules. Zero QA. Agent: **qa-tester**. (Carried)
- [ ] **QA Managed Agents integration** — Lead qualifier + document drafter + field monitor + researcher. Agent: **qa-tester**. (Carried)
- [ ] **QA issue-to-pr loop + autopilot loop** — Shipped `777af3a` + `5ddbbce`. Agent: **qa-tester**. (Carried)
- [ ] **Extend pre-commit hook** — Flag `except Exception: pass` and `except Exception: continue`. Agent: **devops**. (Carried)
- [ ] **Ingest competitor briefs to KB** — 5 research briefs in `research-briefs/`. Manual. (Carried)
- [ ] **Exercise migration duplicate-number pre-commit guard (2a08588)**. Agent: **devops**. (Carried)

### Priority 2 — Code Quality & Verification

- [ ] **Reconcile silent_frontend_catch_count glob drift** — morning=0, evening=9 on same script. Fix `scripts/daily/health-check.sh` glob resolution. (Carried)
- [ ] **Fix 3 non-admin silent `.catch(() => null)` patterns** — `MarketingDashboardPage.jsx:96`, `LocalSEOPage.jsx:262`, `AuthContext.jsx:89`. Agent: **frontend-dev**. (Carried)
- [ ] **Implement JS silent catch pre-commit guard** — Subconscious `365d6ea` recommendation. Agent: **devops**. (Carried)
- [ ] **Validate 47 rewritten skills** — `b83577f` + `0f1d23a` Anthropic canonical. Spot-check critical skills. (Carried)
- [ ] **E2E test onboarding wizard** — 6-step wizard shipped 2026-04-01. (Carried)
- [ ] **Verify expired JWT token handling (6d10cf5)** — 401 interceptor + proactive expiry check. (Carried)
- [ ] **Production verification of March 25 features** — Revenue analytics, pipeline automations, webhook deliveries, password reset: **27+ days unverified.** (Carried)
- [ ] **Audit `.get() or ""` operator precedence pattern** — 3 fixed, likely more. (Carried)
- [ ] **QA GitHub autopilot loop** — `5ddbbce`. Agent: **qa-tester**. (Carried)
- [ ] **Remove remaining 5 MTOptions references** — Post-cleanup audit ee35999 noted residual. (Carried)
- [ ] **Remove MTOptions-growth from daily smoke tests** — Done `ce36df7` but verify no remaining references. (Carried)

### Priority 3 — Knowledge & Documentation

- [ ] **Enrich bug pattern for `fac6124`** — Invariants guard conversations.tenant_id. Auto-logged skeleton 2026-04-21. (New 2026-04-21)
- [ ] **Enrich auto-logged bug patterns (#30-41)** — 12 skeleton entries. Carried since 2026-03-24.
- [ ] **Enrich bug patterns (#58-69)** — 12 skeleton entries from Apr 7-8.
- [ ] **Enrich bug patterns (#72-78)** — 7 skeleton entries from Apr 9 evening.
- [ ] **Enrich bug pattern for `9d48907`** — Landing page Vercel routes fix (Apr 14).
- [ ] **Enrich bug patterns for `0278eb0` + `9febf89`** — Stripe + analytics. (Carried)
- [ ] **Enrich bug pattern for `c0aef59`** — widget_helpers patch target fix (Apr 19). (Carried)
- [ ] **Enrich bug pattern for `080098b`** — skills Phase 2+3 (Apr 19). (Carried)
- [ ] **Act on vertical-specialize research findings (`e3963c5`)** — Review deep-dive + open questions. (Carried)
- [ ] **Act on earlier research findings** — CAC/churn, plateau, unit economics. Pricing/positioning decisions pending. (Carried)
- [ ] **Review 4 new research briefs (2026-04-18/19/20)** — TCPA/CAN-SPAM, smb-self-serve, telemetry, white-label-reseller, widget-first, SMB verticals WTP, historical document automation waves. (Carried)
- [ ] **Compile / ingest 2026-04-18 competitor landscape snapshot (`fd6a09e`)** — `/kb-compile`. (Carried)

### Priority 4 — Carried Forward

- [ ] **Two-way email sync** — pending 5+ weeks.
- [ ] **Fix 16 test isolation failures** — partially addressed.
- [ ] **Automated routine reliability** — Apr 17 morning log showed `git pull` failed on detached HEAD. Verify auto-reattach.
- [ ] **Create migration-gate hook** — Block new feature commits when pending migration count > 15.
- [ ] **Split bug-patterns.md** — now >2,035 lines. Hot file, split by month/category.
