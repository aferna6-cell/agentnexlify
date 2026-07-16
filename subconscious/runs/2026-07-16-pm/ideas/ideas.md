# Ideas — Run 96 (2026-07-16-pm)

## Evidence Base
- appointment_completion.py ABSENT from backend/services/ — run 95 winner not implemented by nightly
- Agent OS sprint: 7 PRs in 3 days (#457-#463): research worker, routing memory, opportunity suggestions UI, draft expiry sweep, explicit recipient fix, loop-health endpoint
- admin_loop_health.py (22710b3) shipped — 214 lines, 261 tests, no frontend yet
- GH #399: OPEN Day 14+ (AUTOPILOT_GH_TOKEN expired, 30 ai-ready issues blocked)
- GH #413: REFERRAL_REWARD_ENABLED=1 NOT SET, Day 25+, 4 autonomous comments, 0 human responses
- GH #403: OPEN, KB autopopulate 72+ days stale
- Keys Koffee: Day 25+, still 0 business_hours rows
- Booking URL fix (6cc3419) + status filter fix (f143de5) landed 2026-07-16 — first real bookings now technically possible
- os_opportunities.py extended with opportunity suggestion rules (PR #462) — deterministic cold-lead + overdue-invoice patterns

---

### Idea 1: Wire appointment_completion.py (Carry-forward — run 95 winner missed)
**Evidence:** appointment_completion.py absent from backend/services/. GH #454 open (filed nightly-2026-07-16). Full implementation sketch in subconscious/runs/2026-07-16/winning-concept.md. Booking chain unblocked: 6cc3419 (booking URL) + f143de5 (status filter fix) both confirmed in git log. First real bookings now possible. Without auto-complete, confirmed appointments sit forever → zero review requests, rebook prompts, or aftercare automations.
**Action:** Write backend/services/appointment_completion.py (async function auto_complete_past_appointments, 30-min grace period, trigger_event("appointment_completed")). Wire into appointment_reminders.py scheduler. Add 3 regression tests to backend/tests/test_appointment_completion.py.
**Impact:** Completes the booking-to-automation chain. Every booking generates review requests, rebook prompts, aftercare — direct revenue retention impact. Timing optimal: first bookings imminent.
**Category:** customer_value

---

### Idea 2: Build BotHealthPage.jsx — frontend for admin_loop_health endpoint
**Evidence:** admin_loop_health.py (22710b3, 2026-07-16) ships /api/admin/loop-health: drafts pending count/age, opportunity suggestions pile-up, Agent OS usage, inbound bridge status, error accumulation. 261 tests, production-ready. No frontend page exists. AdminFunnelPage (PR #417) established the pattern: new backend endpoint → matching frontend dashboard. Agent OS sprint (7 PRs) massively expanded the Agent OS surface — admin visibility into loop health is now critical.
**Action:** Build frontend/src/pages/BotHealthPage.jsx consuming GET /api/admin/loop-health. Show 5 vitals: pending drafts (count + oldest age), opportunity suggestions queued, Agent OS active tenants, inbound bridge status, error accumulation rate. Add to sidebar as "Loop Health" under Admin section.
**Impact:** Ops visibility — admin can detect stalled loops without hand-run SQL. Directly motivated by 2-week GH #399 stall going unnoticed.
**Category:** customer_value / operational

---

### Idea 3: Post Day-14 escalation on GH #399 — quantify 30-issue opportunity cost
**Evidence:** GH #399 OPEN Day 14+ (AUTOPILOT_GH_TOKEN expired). 30 ai-ready issues blocked. Agent OS sprint shows developer velocity is high (7 PRs in 3 days) — the bottleneck is the secret rotation, not dev capacity. admin_loop_health.py (22710b3) would detect this via stalled loop metrics. Lead Source Analytics dashboard and SMS Compliance Dashboard are the two most visible queued items.
**Action:** Post Day-14 escalation comment on GH #399 with opportunity-cost framing: "Day 14: 30 ai-ready issues blocked. At estimated 2h per issue = 60 engineering-hours queued behind one Railway env-var update. Top blocked: Lead Source Analytics dashboard (#385), SMS Compliance Dashboard. admin_loop_health endpoint (22710b3) now monitors this — loop vitals will show stalled-autopilot signal going forward."
**Impact:** Highest-probability trigger for human action. Previous Day-13 escalation (run 95 bonus) is on the issue. Adding velocity/cost context increases urgency. Autonomous via mcp__github__add_issue_comment.
**Category:** operational

---

### Idea 4: Add os_opportunities referral_activation rule — surface referral in Agent OS suggestions
**Evidence:** os_opportunities.py PR #462 ships deterministic opportunity rules (cold leads, overdue invoices) → os_backlog_requests entries → Agent OS suggestion cards UI (OpportunityCards.jsx). REFERRAL_REWARD_ENABLED=1 still pending Day 25+. 4 GH comments on #413 with 0 human responses. A 5th GH comment channel has diminishing returns. Agent OS suggestion cards appear directly in the tenant admin flow.
**Action:** Add referral_activation check to os_opportunities.py: query referral_rewards table for any row with client_id matching a live tenant; if rows exist and REFERRAL_REWARD_ENABLED env is not "1", file os_backlog_requests row with reason="opportunity" and title="Activate referral program — migration live, one env-var flip".
**Impact:** Surfaces activation in tenant admin's normal review flow. However: env-var check inside os_opportunities.py is non-standard (service is DB-query-only currently). Mechanism mismatch may make this harder than it looks.
**Category:** customer_value

---

### Idea 5: Add Step 9F to nightly SKILL.md — KB autopopulate staleness check
**Evidence:** GH #403 OPEN (KB autopopulate stalled 72+ days). kb_autopopulate_stale_days = 72+. Nightly SKILL.md has Steps 9B/9C/9D/9E but no 9F for KB staleness. The kb-autopopulate.yml GitHub Action (run 82 winner) was created but GH #403 suggests it failed. Run 95 weakened Step 9F as "GH #403 already tracked" — but GH #403 has had 0 resolution in 13+ days. An automated daily staleness check adds monitoring that doesn't depend on human GH #403 resolution.
**Action:** Add Step 9F block to .claude/skills/nightly-commit-review/SKILL.md: check knowledge-base/log.md last-entry timestamp; if >7 days stale, add escalation comment on GH #403 with staleness count in days and last-run date. Same class as Steps 9C/9D/9E (AUTONOMOUS-EXECUTABLE SKILL.md edit).
**Impact:** Automated daily KB health monitoring. Prevents silent 72-day gaps. AUTONOMOUS-EXECUTABLE via nightly channel.
**Category:** operational
