# Current Task Backlog — AgentNexLiFy

Updated: 2026-04-10 (automated morning routine)

## Today's Top 3 Priorities

1. **ROTATE compromised admin API key in Railway** — DAY 7 of exposure. Key committed in 9c87335, scrubbed in d4463d7. Still live in Railway. Agent: **devops** / Human action required. **CRITICAL.**
2. **QA the 81-file auto-commit (tenant_scope adoption)** — Commit 11363a1 landed overnight touching 60+ routers. Cross-tenant leak risk if any router lost its tenant scoping. Agent: **qa-tester**.
3. **Apply migrations 077-100** — 24 pending migrations blocking features (autopilot plan, onboarding wizard, RLS fixes, no-show recovery, daily briefing, AI lead qualification, AI document drafting). Agent: **schema-guardian**.

## Active Tasks

### Priority 0 — Security (Immediate Action Required)

- [ ] **ROTATE compromised API key in Railway** — Key committed in 9c87335, scrubbed in d4463d7. Key is still live. DAY 7 of exposure — **CRITICAL**. Agent: **devops** / Human. (Carried from Apr 5)

### Priority 0 — Resolved: Uncommitted Work

- [x] **94 uncommitted files committed** — Auto-commit 11363a1 (2026-04-09 20:05) landed 81 files (773 insertions, 548 deletions). Tenant_scope adoption + import cleanup. **QA needed** — see Priority 1.

### Priority 0 — Schema (Critical / Pre-Launch Blocker)

- [ ] **Apply migration 090 (autopilot plan)** — autopilot subscriptions fail at DB level. Created 2026-04-06.
- [ ] **Apply migration 093 (fix RLS policies)** — migration 091's auth.uid() policies are semantically broken. Created 2026-04-07.
- [ ] **Apply migrations 097-098** — no-show recovery columns, daily briefing toggles, pre-chat form. Created 2026-04-08.
- [ ] **Apply migrations 099-100** — AI lead qualification fields, AI-drafted documents. Created 2026-04-09.
- [ ] **Apply migrations 094-096 (schema reconciliation + hardening)** — Production columns, conversation memory, FK canonicalization. Created 2026-04-07.
- [ ] **Apply migrations 077-079 (onboarding blockers)** — Blocks wizard for new signups. Created 2026-04-01.
- [ ] **Apply migrations 083-092** — waitlist, scoring configs, password reset, A/B tests, automation rules, campaign analytics, admin tracking, reminder tracking. Agent: **schema-guardian**.

### Priority 1 — Critical / QA

- [ ] **QA 81-file auto-commit (11363a1)** — tenant_scope adoption across 60+ routers. Cross-tenant leak = critical. Agent: **qa-tester**. (NEW — Apr 10)
- [ ] **QA tenant_scope.py end-to-end** — Centralized tenant scoping touching 20+ routers. Bug = cross-tenant leak. Agent: **qa-tester**.
- [ ] **QA marketing infrastructure** — A/B tests, automation rules, marketing dashboard. Zero QA. Agent: **qa-tester**.
- [ ] **Verify security fixes (2ab39dd, d7572eb, e2dbf36, 29aca88)** — 25+ security patches. Agent: **qa-tester**.
- [ ] **QA Apr 8-9 fix batch** — 13+ bug fixes across 3 fix commits (noshow cache, session_id, header injection, async blocking, hardcoded URLs). Agent: **qa-tester**.
- [ ] **Extend pre-commit hook** — Flag `except Exception: pass` and `except Exception: continue` (not just bare `except:`). Agent: **devops**.
- [ ] **QA Managed Agents integration** — New feature (lead qualification + document drafter). Smoke tests pass but no production QA yet. Agent: **qa-tester**.

### Priority 2 — Verification & Testing

- [ ] **Apply migrations 065-070** — client_accounts, waitlist(old), scoring_configs(old), invoice unique, email bounce, pipeline automations. 14+ days stale.
- [ ] **E2E test onboarding wizard** — 6-step wizard shipped 2026-04-01. Needs QA.
- [ ] **Verify expired JWT token handling (6d10cf5)** — 401 interceptor + proactive expiry check.
- [ ] **Production verification of March 25 features** — Revenue analytics, pipeline automations, webhook deliveries, password reset: **14+ days unverified.**
- [ ] **Audit `.get() or ""` operator precedence pattern** — 3 fixed, likely more.
- [ ] **Review 8 silent .catch(() => null) patterns** — AdminAnalyticsPage (6), MarketingDashboardPage (1), LocalSEOPage (1). Down from 13 — 5 fixed in f0a1c37. Promise.all resilience pattern — audit remaining. Agent: **frontend-dev**.

### Priority 3 — Knowledge & Documentation

- [ ] **Enrich auto-logged bug patterns (#30-41)** — 12 skeleton entries still need human enrichment. Carried since 2026-03-24.
- [ ] **Enrich bug patterns (#58-69)** — 12 skeleton entries from Apr 7-8 fix commits. Need root cause details.
- [ ] **Enrich bug patterns (#72-78)** — 7 new skeleton entries from Apr 9 evening. Auto-logged, need human review.

### Priority 4 — Carried Forward

- [ ] **Two-way email sync** — still pending from previous backlog (3+ weeks)
- [ ] **Fix 16 test isolation failures** — partially addressed, may still have remaining failures
- [ ] **Automated routine reliability** — March 26 evening and March 27 morning both failed; April 6 morning did not run.
- [ ] **Create migration-gate hook** — Block new feature commits when pending migration count > 15. Suggested by evening review pattern analysis.

## Completed (Recent) — 2026-04-09

- [x] **Morning health check** — all clear (0 dangerous imports, 0 bare excepts, widget sync OK, build PASS 5.82s)
- [x] **Documentation gap scan** — no gaps in bug-patterns or schema-log
- [x] **Daily log created** — docs/daily-logs/2026-04-09.md
- [x] **Task backlog updated** — this file (morning)
- [x] **Claude Managed Agents infrastructure** — Full integration with Anthropic Managed Agents API (6f59c42)
- [x] **AI Lead Qualification agent** — Claude-powered lead scoring on paid plans (765adbe, migration 099)
- [x] **AI Document Drafter agent** — Generate quotes/invoices/proposals (a4ffee7, migration 100)
- [x] **Claude Code security hardening** — Trail of Bits sandbox + permission deny rules (b42e3c1, 9c478d0)
- [x] **Fix: noshow followup tenant-cache bug** — b34e0c6 (bug #70)
- [x] **Fix: pipeline email XSS** — b34e0c6 (bug #71)
- [x] **Fix: session_id confusion in managed agents** — 91651b0 (bug #72)
- [x] **Fix: HTTP header injection via Content-Disposition** — 91651b0 (bug #73)
- [x] **Fix: daily_briefing swallowed exceptions** — 91651b0 (bug #74)
- [x] **Fix: score_all_leads() blocking event loop** — f0a1c37 (bug #75, CRITICAL)
- [x] **Fix: widget lead scoring blocking async** — f0a1c37 (bug #76)
- [x] **Fix: hardcoded production URLs in 4 routers** — f0a1c37 (bug #77)
- [x] **Fix: missing HEAD on /version endpoint** — f0a1c37 (bug #78)
- [x] **Frontend: added console.warn to 5 swallowed .catch() blocks** — f0a1c37
- [x] **Regression tests: bug-patterns #70 + #71** — 100d275
- [x] **Regression tests: noshow toggle-off** — 4782b89
- [x] **Regression tests: daily briefing SMS formatter** — 4f5e47b
- [x] **Evening review + bug-patterns #72-78 documented** — this session
- [x] **Schema-log verified** — migrations 099-100 accurate
- [x] **Task backlog updated** — this file (evening)

## Previous Completed — 2026-04-08

- [x] 6 fix commits landed (route shadow, unawaited async, Railway build, race condition, CSV mapping, 22+ swallowed exceptions)
- [x] 2 feature commits (daily briefing SMS + no-show recovery; recovery stats dashboard + pre-chat form builder)
- [x] 27 backend tests added (auth, widget, booking, tenant isolation, schema integration)
- [x] E2E smoke tests added (widget revenue path)
- [x] Dead code sweep (3 services + 30 unused API functions removed)
- [x] Vendor chunk extraction (xyflow + dompurify → cacheable chunks)
- [x] CLAUDE.md refactored into 9 path-scoped rules
- [x] Sentry error monitoring added
- [x] Migrations 097-098 created
- [x] Bug patterns #64-69 documented
- [x] Schema-log updated through 098

## Overall Progress (2026-04-10 Morning)

- **Last commit:** 11363a1 (chore: auto-commit Claude edits, 2026-04-09 20:05)
- **Codebase status:** Clean (auto-commit 11363a1 resolved 94-file backlog)
- **Health check:** All green (frontend build 4.45s, widget sync OK, 0 bare excepts, 0 dangerous imports)
- **Silent frontend catches:** 8 (stable — same as Apr 9 evening)
- **Bug patterns total:** 78 (no new overnight)
- **Pending migrations:** 24 (unchanged — none applied overnight)
- **SECURITY INCIDENT DAY 7:** admin API key — rotate in Railway immediately
- **Key concern:** QA the 81-file auto-commit for cross-tenant safety

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
