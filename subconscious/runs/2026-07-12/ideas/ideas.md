# Run 90 Ideas — 2026-07-12

## Evidence Summary

Today (run 90, 2026-07-12): Pipeline stalled Day 8 — AUTOPILOT_GH_TOKEN (#399) and ANTHROPIC_API_KEY in
Actions (#403) both expired/missing. 40 ai-ready issues queued. Brain connector RECOVERED (81be6df today
after ~11-day gap). GH #413 (referral reward) filed, awaiting human. GH #412 (booking diagnostic) filed,
0 human comments. 0 real bookings across 19 days; 2/3 tenants technically bookable (PR #404 confirmed).
KB autopopulate 67 days stale, same blocker as pipeline (#403). Step 9E operational. No product code in
3+ days. Supabase MCP unavailable in headless sessions — confirmed x2 (runs 88-89).

Pattern: Human action queue at 4 items (#403, #399, #412, #413), none resolved. Self-referential
monitoring gap confirmed: Step 9E requires Claude API to detect missing Claude API key — if ANTHROPIC_API_KEY
expires in GH Actions, Step 9E can't run to detect it.

---

### Idea 1: GH Actions Secrets Health-Check Workflow
**Evidence:** GH #399 stalled Day 8 (AUTOPILOT_GH_TOKEN expired), GH #403 stalled (ANTHROPIC_API_KEY
missing/never set). Pattern: credentials expire silently, take days to detect. Current cost: 40 ai-ready
issues × avg 4h = ~160h blocked autonomous work + 67-day KB degradation. Root cause of detection gap:
Step 9E runs inside nightly-commit-review which REQUIRES ANTHROPIC_API_KEY — the very key it would be
monitoring. Self-referential blind spot confirmed. Every prior Steps 9B/9C/9D/9E prevented future
same-class failures when implemented.
**Action:** Create `.github/workflows/secrets-health-check.yml` — runs weekly via cron schedule. Checks
`${{ secrets.ANTHROPIC_API_KEY != '' }}` and `${{ secrets.AUTOPILOT_GH_TOKEN != '' }}` using
GITHUB_TOKEN (always present in GH Actions, no dependency on monitored secrets). Optionally pings
Anthropic API + GitHub API to validate keys are live, not just present. Creates GH issue with
`human-action-required` label if either is missing. Deduplication: only creates issue if no open issue
with label `secrets-health-check-alert` exists.
**Impact:** Prevents next credential stall. Detection latency drops from 8+ days to ≤7 days. The
automated pipeline's blast radius shrinks from "complete 8-day shutdown" to "same-day alert."
**Category:** operational

---

### Idea 2: Add Step 9F to nightly SKILL.md — Booking Conversion Tracker
**Evidence:** 0 real bookings 19 days post-launch. 2/3 tenants technically bookable (PR #404 confirmed
MTOptions 20 slots, 914 Exterior 22 slots). Run 88 rejected Step 9F as "premature — hypothesis A
unconfirmed." Run 89 set condition: "add Step 9F if booking_enabled=true confirmed." That condition is
now MET per PR #404 evidence. Steps 9C/9D/9E monitor infrastructure; no step monitors product
conversion outcomes.
**Action:** Add Step 9F block to `.claude/skills/nightly-commit-review/SKILL.md`: (1) check GH #412
for human comments (did owner run the diagnostic SQL?), (2) attempt GET call to backend appointments
API via curl (avoiding Supabase MCP gap), (3) if 0 bookings after 30 days total: file escalation
issue. Celebrate first booking event.
**Impact:** Closes product conversion monitoring gap. Detects first real booking event. Surfaces
funnel vs. discovery failure distinction.
**Category:** workflow

---

### Idea 3: Keys Koffee Business Hours Request GH Issue
**Evidence:** PR #404 explicitly: "Keys Koffee still needs real hours from tenant." 2/3 tenants
bookable; 1/3 blocked on tenant data input. 0 real bookings 19 days. Business hours are the
single unblocked pending step for the third tenant.
**Action:** File GH issue via GitHub MCP: "ACTION REQUIRED: Collect Keys Koffee business hours —
tenant provides hours, populate tenant_availability." Include email template for owner to send to
Keys Koffee contact. Owner sends email, tenant replies with hours, owner enters hours in
dashboard (≤10 min total).
**Impact:** 3/3 tenants fully bookable. Third booking funnel activated. Could produce first
real booking from the Keys Koffee widget.
**Category:** customer_value

---

### Idea 4: Supabase MCP Headless Session Diagnosis GH Issue
**Evidence:** Runs 88 and 89 both failed on `mcp__supabase__execute_sql` — not available in headless
sessions. Nightly-2026-07-11 explicitly confirmed: "Supabase MCP installed at org level but NOT enabled
in headless session." This has blocked: booking_enabled audit, tenant_availability check, referral
reward schema verification. High multiplier — fixing this unblocks all DB-inspection tasks.
**Action:** File GH issue investigating: (a) check `.mcp.json` for supabase server config, (b) verify
if org-level MCP install propagates to headless GH Actions runners, (c) propose fix (add `--mcp-config`
flag, or add supabase MCP to `.github/workflows/` env). Implementation requires investigating Claude
Code headless session MCP loading behavior.
**Impact:** Unblocks all future autonomous DB-inspection tasks in nightly and subconscious.
**Category:** workflow

---

### Idea 5: Weekly Revenue Digest Morning Step
**Evidence:** 4 open human-action items, 0 resolved in 8+ days. Owner is processing many GH issues.
A consolidated weekly revenue status (leads this week, bookings, pipeline status, top P0 action) in
a single issue could reduce cognitive load and increase action rate.
**Action:** Add a weekly morning-digest step that generates a single "Revenue Pulse — Week of [date]"
GH issue summarizing: leads captured, bookings confirmed, referral status, top P0 action.
**Impact:** Reduces context-switching. Might accelerate resolution of pending items.
**Category:** workflow

---

## Top 3 for Debate (by structural impact)

1. Idea 1 — GH Actions Secrets Health-Check Workflow (operational, S)
2. Idea 2 — Add Step 9F Booking Conversion Tracker (workflow, XS)
3. Idea 3 — Keys Koffee Business Hours GH Issue (customer_value, XS)
