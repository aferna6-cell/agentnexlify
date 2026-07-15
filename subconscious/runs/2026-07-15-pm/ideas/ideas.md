# Ideas — Run 95 (2026-07-15-pm)

## Evidence Summary

**What changed (3 days):** 15+ commits — massive feature + fix sprint.
- Agent OS: one-click routing picker (#449), real send outcomes (#448), auto-send toggle fix (#447, 5 of 7 agents silently broken), business data in agent prompts (#446)
- Booking: customer reschedule/cancel notifications (#444), voice booking owner alerts (#443), reschedule re-arms reminders (#442), **appointment reminders dead bug fixed** (#441 — filtered on status no appointment has), owner alert on booking (#440)
- **Critical fix: inject real booking URL into AI prompt (#439)** — AI couldn't tell users where to book for 24+ days since booking launched
- Performance: FK indexes + migration 174 (#437), RLS lockdown (#436), threadpool offloads + widget_guard LRU (#435)
- Leads: owner alert on public-form + Messenger lead capture (#445)

**Mandate check:**
- ✅ widget_guard fix implemented (d73072a, OrderedDict line 149, regression test exists)
- ❌ GH #413 REFERRAL_REWARD_ENABLED=1 still NOT set — Day 24+, 0 human responses after 4 autonomous comments
- ❌ Keys Koffee GH #415 not actioned — Day 24+, still 0 business_hours rows
- ❌ GH #399 OPEN Day 13+ — 40 ai-ready issues blocked
- ❌ GH #403 OPEN Day 13+ — KB autopopulate 72+ days dark

**Pattern:** 3 silent failure bugs fixed in 3 days (auto-send toggle, appointment reminders, booking URL). None had tests preventing regression. All lived in production for weeks.

---

### Idea 1: Add regression test for booking URL injection in widget AI prompt

**Evidence:** Commit 6cc3419 "inject real booking URL into AI prompt — unblocks bookings" fixed a 24-day silent failure. The AI widget was not telling users where to book because the booking URL was never injected into the prompt. No test caught this. Pattern of 3 similar silent failures in 3 days (auto-send toggle → appointment reminders → booking URL). bug-patterns.md growing rapidly from same pattern.

**Action:** Add test in `backend/tests/test_widget_chat.py`: when `booking_enabled=True` for a tenant, assert the AI system prompt contains a non-empty booking URL. Mirror how existing tests assert KB content injection. Also assert booking URL is absent when `booking_enabled=False`.

**Impact:** Prevents regression of the most critical booking bug just fixed. Closes testing gap in a class of silent failures that cost 24+ days of broken bookings. Can be committed directly via nightly autonomous code channel.

**Category:** code_health

---

### Idea 2: Add Step 9F to nightly SKILL.md — infra staleness escalation check

**Evidence:** GH #399 (OPEN Day 13+) and GH #403 (OPEN Day 13+) are persistent infrastructure blockers with no human response after existing autonomous comments. Step 9D checks ai-ready issues. Step 9E checks credential expiry. No step checks `human-action-required` issues older than 7 days for escalation priority upgrade (label critical, different notification path).

**Action:** Add Step 9F block to `.claude/skills/nightly-commit-review/SKILL.md`: query issues labeled `human-action-required` open >7 days; post Day 7/14/21 escalating milestone comments; at Day 14 add `critical` label if not present.

**Impact:** Systematic escalation pressure on infrastructure blockers. Autonomous-executable via nightly SKILL.md channel.

**Category:** workflow

---

### Idea 3: File Attribution Dashboard GH issue with ai-ready label

**Evidence:** PR #431 ships attribution.py + migration 172 (attribution data: campaign, source, medium). No AttributionPage.jsx exists. customer-gaps.md lists "Lead source analytics" as cross-industry, Low effort, open since run 2 (83-run parking lot). 7 real leads with unknown acquisition sources. Issue-to-pr-loop blocked but issue queues for when GH #403 fixed.

**Action:** File GH issue for `AttributionPage.jsx` with `ai-ready` label. Spec: GET /api/leads/attribution-breakdown endpoint + BarChart in AnalyticsPage.jsx or separate AttributionPage. Invariants: client_id not tenant_id, no `from __future__ import annotations`, auth required, RLS-aware.

**Impact:** Closes 83-run parking lot item. Queues for loop when GH #403 resolves. Tenant insight into lead acquisition sources.

**Category:** customer_value

---

### Idea 4: BotHealthPage.jsx GH issue with ai-ready label

**Evidence:** PR #431 shipped bot_health.py (new backend service — largest from that PR). Tests 77%→86%. No frontend visibility. Dashboard has AgentOS page but no Bot Health page. Silent failures are the pattern — no visibility means issues go undetected for weeks. bot_health.py provides uptime, error rates, response quality metrics.

**Action:** File GH issue for BotHealthPage.jsx with ai-ready label. Spec: React dashboard page consuming GET /api/bot-health per tenant; uptime tile, error rate chart, recent failures table.

**Impact:** Reduces silent failure detection time from weeks to hours. Tenant-visible bot health transparency. Queue for loop when GH #403/#399 resolved.

**Category:** customer_value

---

### Idea 5: Write scripts/kb-refresh-local.sh to unstick 72-day stale KB

**Evidence:** knowledge-base/log.md last entry 2026-05-05 (72+ days stale). GH #403 blocks kb-autopopulate.yml (ANTHROPIC_API_KEY not in GH Actions secrets). KB used by all tenant AI widget responses. Local Claude CLI is available in this session. scripts/daily/kb-autopopulate.sh already exists but references hard-coded paths.

**Action:** Write `scripts/kb-refresh-local.sh` that wraps kb-autopopulate.sh with the current environment's Claude binary. Execute via nightly review as an autonomous step while GH #403 awaits human fix.

**Impact:** Breaks 72-day KB stale cycle without waiting for human to fix GH #403. AI widget responses improve immediately.

**Category:** operational
