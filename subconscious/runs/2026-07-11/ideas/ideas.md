# Ideas — Run 88 (2026-07-11)

## Evidence Summary

- **0 production code commits** in last 3 days (2026-07-09+): all ops/brain/subconscious docs
- **Booking Enabled Audit blocked × 2**: nightly-2026-07-11 confirmed Supabase MCP unavailable in headless session; this subconscious session also lacks Supabase MCP (only GitHub MCP available)
- **Issue-to-pr-loop stalled Day 7**: 40 ai-ready issues queued, 2 stalled >24h (GH #385 SMS Compliance 10 days, GH #409 Lead Source Analytics 1 day). Dual blocker: AUTOPILOT_GH_TOKEN expired (#399) + ANTHROPIC_API_KEY not in Actions (#403)
- **Brain connectors recovered**: 4fc15f0 (2026-07-11) = successful brain refresh from GitHub + Supabase
- **0 real bookings** in 17 days since launch (2026-06-23). Run 87 mandate to audit booking_enabled status: UNEXECUTED
- **Run 88 mandate explicitly calls** for tenant_availability check as secondary hypothesis if booking_enabled=true

---

### Idea 1: File "Booking Funnel Diagnostic" GH Issue — Package Both SQL Queries for Human Execution
**Evidence:** Booking Enabled Audit blocked for 2nd consecutive run by Supabase MCP gap. 0 real bookings × 17 days. Run 87 winner + run 88 mandate both point to this. Two hypotheses: (a) booking_enabled=false, (b) tenant_availability missing business hours. GitHub MCP IS available this session — can file the issue now.
**Action:** File GH issue via mcp__github__issue_write with title "ACTION REQUIRED: Booking Funnel Diagnostic — 0 bookings in 17 days" containing both SQL queries (booking_enabled check + tenant_availability check) and exact UPDATE statements if needed. Labels: `revenue`, `human-action-required`, `diagnostic`. Human runs in Supabase dashboard in <5 minutes.
**Impact:** Converts 2-run-blocked autonomous audit into human-executable 5-minute diagnostic. First real booking could happen same day as fix.
**Category:** customer_value

---

### Idea 2: File P0 Consolidated Pipeline Escalation — Dual-Blocker Day 7
**Evidence:** Step 9D confirmed Day 7 stall. GH #399 (AUTOPILOT_GH_TOKEN) filed 2026-07-09, still open. NEW: nightly-2026-07-11 identified ANTHROPIC_API_KEY not set in Actions as SECOND distinct blocker (GH #403). 40 ai-ready issues queued. Issue-to-pr-loop last ran pre-2026-07-04.
**Action:** Add Day 7 escalation comment to GH #399 explicitly linking both blockers. If GH #403 exists, link it. If GH #403 is missing, file it with labels: `critical`, `human-action-required`, `operations`. Title: "AUTOPILOT: ANTHROPIC_API_KEY missing in GH Actions — issue-to-pr-loop day 7 stalled."
**Impact:** 40 queued features unblocked. Both fixes take ~5 min each.
**Category:** operational

---

### Idea 3: Diagnose Supabase MCP Availability Gap in Headless Sessions
**Evidence:** Nightly: "Supabase MCP connector is installed (org level) but not enabled in this chat session." Same in subconscious session. brain/Sources/connector-github-issues.md confirms brain sync via Supabase succeeded (4fc15f0) — so Supabase connectivity exists at infra level. The gap is MCP session configuration, not connectivity.
**Action:** Check .mcp.json for Supabase entry + SUPABASE_ACCESS_TOKEN env var. Diagnose whether the Supabase MCP is available in the nightly GH Actions environment. Propose fix: either inject SUPABASE_ACCESS_TOKEN via GH Actions secrets or document that Supabase queries must be routed through human-action GH issues permanently.
**Impact:** Enables autonomous booking audit + all future DB diagnostic steps (9F and beyond).
**Category:** operational / workflow

---

### Idea 4: Add Step 9F to nightly SKILL.md — Tenant Availability Hours Check
**Evidence:** Run 88 mandate: "if booking_enabled=true, check tenant_availability for business hours." Run 87 win introduced Step 9E pattern. Steps 9A-9E all implemented in 1 nightly cycle. Pattern is highly reliable for SKILL.md additions. 0 bookings × 17 days has 2 root cause hypotheses — only Step 9F checks the second.
**Action:** Add Step 9F block to .claude/skills/nightly-commit-review/SKILL.md after Step 9E. Step checks tenant_availability table (or widget_configs.booking_hours) for real tenants. If missing hours → file GH issue with tenant_availability seed SQL.
**Impact:** Closes second monitoring gap in booking funnel. Autonomous when Supabase MCP available.
**Category:** workflow
**Caveat:** Blocked by same Supabase MCP gap as audit. If MCP unavailable in nightly sessions, Step 9F will also silently skip.

---

### Idea 5: Referral Reward Pre-Gate Diagnostic
**Evidence:** Run 87 parking lot. Referral system live (commits 57f2bb4d, 29ed1d43). customer-gaps.md has no referral tracking entry. 3b30505 (2026-07-09) audits G3 voice scope + agent_os voice-gate fix. No referral-reward issue open. 7 real leads, referral rewards never triggered.
**Action:** Check backend/services/referral*.py for plan gating. Verify referral rewards are reachable for chatbot ($19.99/mo) plan. If gated behind agent_os only, file GH issue noting that the referral program excludes 50%+ of potential referrers.
**Impact:** Potential revenue multiplier if referral program reaches chatbot-tier users.
**Category:** customer_value
**Caveat:** Requires code read, not blocked by Supabase MCP gap. Lower urgency than booking funnel.
