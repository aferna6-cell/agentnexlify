# Ideas — Run 89 (2026-07-11-pm)

## Evidence Base (Phase 2 summary)

- **GH #412 (run 88 winner):** FILED 2026-07-11T10:15:52Z. Labels: revenue, human-action-required, diagnostic. 0 comments — human has NOT run the diagnostic SQL yet.
- **GH #399 (AUTOPILOT_GH_TOKEN):** OPEN. 3 comments. Not fixed. Loop stalled Day 7+, 30 consecutive failures.
- **GH #403 (ANTHROPIC_API_KEY in Actions):** OPEN. 0 comments. Not fixed. Blocks autopilot-issue-loop AND kb-autopopulate.
- **PR #404 commit (3596009) — CRITICAL:** "2 of 3 paying tenants fully bookable. MTOptions: 20 live booking slots. 914 Exterior: impossible-hours prod data bug CORRECTED to 17:00 (22 slots/day). Keys Koffee needs real hours from tenant. Onboarding now seeds Mon-Fri 9-5 defaults for new tenants. **Migration 162 (referral_rewards) applied to prod: launching referral reward is now a single env-var flip (REFERRAL_REWARD_ENABLED=1).**"
- **PR #405 commit (3b30505):** G3 voice ~60% built (AI speech + 61 tests exist; booking integration, per-tenant provisioning, metering, dashboard all missing). MessagingSettingsCards.jsx agent_os voice gate bug fixed.
- **Brain connectors:** RECOVERED (4fc15f0 2026-07-11).
- **Run 89 mandate status:** (1) GH #412 FILED ✅ (2) Human not run queries yet ❌ (3) booking_enabled likely true for MTOptions+914 Exterior (PR #404) ≈ RESOLVED (4) availability confirmed seeded for 2/3 ≈ RESOLVED (5) GH #399 NOT FIXED ❌ (6) GH #403 NOT FIXED ❌

---

## Idea 1: Post Day-2 Escalation Comment on GH #403 (ANTHROPIC_API_KEY)

**Category:** operational  
**Effort:** XS  
**Autonomous:** AUTONOMOUS-EXECUTABLE via `mcp__github__add_issue_comment`

GH #403 has 0 comments since filed 2026-07-11 (yesterday). GH #399 has daily Step 9D comments. GH #403 — missing ANTHROPIC_API_KEY in Actions — has received none. This issue blocks both autopilot-issue-loop AND kb-autopopulate.yml. A Day-2 comment raises visibility and quantifies impact: 40 ai-ready issues queued, kb-autopopulate last ran 2026-05-05 (67 days), Lead Source Analytics stalled.

**Weakness:** Step 9D already handles #399 daily escalation. #403 comment is the unique value but is auxiliary — not the primary loop mechanism. Best as bonus action.

---

## Idea 2: Referral Reward Activation Pre-Gate Diagnostic (File GH Issue)

**Category:** customer_value  
**Effort:** XS  
**Autonomous:** AUTONOMOUS-EXECUTABLE via `mcp__github__issue_write`

PR #404 confirmed Migration 162 (referral_rewards schema) applied to prod. REFERRAL_REWARD_ENABLED=1 is a single Railway environment variable flip — zero engineering cost, zero schema changes, no PR needed. The system is built and schema-ready. Only a human needs to flip a Railway variable.

Referral programs drive 3-5x CAC reduction in SaaS. Each referred lead costs $0 in acquisition. Referral velocity compounds if real tenants (Keys Koffee, MTOptions, 914 Exterior) share their widget with their customer bases. 7 real leads already captured — each is a potential referrer.

This idea has never been recommended by subconscious (parking lot carry-forward from runs 87-88, always beaten by higher-priority Booking Enabled Audit chain).

**Action:** File GH issue with human-action-required label containing: (1) confirmation Migration 162 is live, (2) single-step activation (Railway env var), (3) expected virality mechanics, (4) safety checklist (referral tracking, reward redemption flow, fraud risk).

---

## Idea 3: Update GH #412 with PR #404 Booking Findings

**Category:** customer_value  
**Effort:** XS  
**Autonomous:** AUTONOMOUS-EXECUTABLE via `mcp__github__add_issue_comment`

PR #404 largely answers the GH #412 diagnostics: MTOptions has 20 live slots (Hypothesis B confirmed false for MTOptions), 914 Exterior's impossible-hours prod bug corrected to 17:00 (Hypothesis B resolved for 914 Exterior). Hypothesis A (booking_enabled) likely also resolved for both given "2 of 3 fully bookable" language.

Keys Koffee still needs real business hours from the tenant. GH #412 body asks human to run SQL — an update comment closing Hypothesis B for 2 of 3 tenants narrows the investigation to Keys Koffee only and reduces human cognitive load.

**Weakness:** Additive to the existing run 88 winner direction. Valuable but not the primary new opportunity. Best as bonus action alongside winner.

---

## Idea 4: File ai-ready GH Issue for Booking Conversion Rate in Weekly Funnel Report

**Category:** customer_value  
**Effort:** XS  
**Autonomous:** AUTONOMOUS-EXECUTABLE via `mcp__github__issue_write`

PR #404 added a weekly owner funnel report. The funnel tracks leads → appointments → (future) bookings. Current metrics do not include booking conversion rate as a percentage. An explicit conversion rate metric would surface the funnel failure point immediately when bookings are 0.

**Weakness:** Issue-to-pr-loop is stalled (GH #399 + #403 unresolved). A new ai-ready issue would queue, not execute. Low immediate impact vs referral reward activation.

---

## Idea 5: File G3 Voice Scope Completion Roadmap GH Issue

**Category:** customer_value  
**Effort:** XS  
**Autonomous:** AUTONOMOUS-EXECUTABLE via `mcp__github__issue_write`

PR #405 confirmed G3 voice ~60% built: AI speech flow exists in calls.py with 61 tests; booking integration never wired in; no per-tenant phone number provisioning; no minutes metering; no calls dashboard UI. Agent_os voice gate bug fixed in MessagingSettingsCards.jsx.

A scoped GH issue packaging the remaining 40% work (booking integration, provisioning, metering, dashboard) would let human prioritize and unblock when the pipeline restores.

**Weakness:** G3 voice is not revenue-immediate. Booking completion and referral reward activation are higher-leverage first movers. Loop is stalled, so ai-ready issue would queue, not execute.
