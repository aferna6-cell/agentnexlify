# Run 85 — Debate Log (2026-07-09-pm)

Top 3 ideas challenged and defended. One winner emerges.

---

## Idea A: Lead Source Analytics Dashboard

### Challenge
"83 runs in the parking lot for a reason — if this were high-value, wouldn't the user have asked for it directly? The source column likely has null/empty for all 7 real leads anyway, making the chart meaningless. And GH #399 being 'fixed' doesn't mean the loop is *healthy* — we saw 30 consecutive failures; how do we know it's actually working now?"

### Defense
- Parking lot = bandwidth constraint, not low value. The user explicitly put it on the parking lot list in `customer-gaps.md` and the mandate says "revisit as run 85 winner" — that's a direct instruction.
- Source nulls: even if all 7 leads have null/empty source, the chart renders that as "Direct/Unknown" — which IS actionable data (no UTM tracking = no source attribution → fix is upstream UTM setup, not downstream chart).
- Loop health: dfa8201 added PAT preflight validation + github.token fallback. Even if AUTOPILOT_GH_TOKEN expires again, the loop now falls back instead of dying. The structural fix is in place.
- Implementation risk is L (Low). Recharts installed, source column exists, one endpoint + one chart. The issue-to-pr-loop delivers this without consuming subconscious capacity.

### Verdict: **SURVIVES → WINNER**
Evidence: mandate instruction, 83-run deferral resolved, GH #399 structurally fixed, L effort, direct customer value signal.

---

## Idea B: Step 9E Already Pending — Re-Recommendation Risk

### Challenge
"Step 9E was run 84's winner and is `pending_autonomous` in governance. Run 85 recommending it again is a no-op at best and a governance loop violation at worst. The nightly-2026-07-10 should implement it. Why waste a subconscious cycle re-recommending something already in the pipeline?"

### Defense
- True that Step 9E is in the pipeline. Recommending it again would be governance pollution.
- However: the stale Item A text (lines 67–79 in nightly SKILL.md) IS a real problem — not Step 9E itself but the cleanup around it. Could be framed as a separate XS cleanup.
- BUT: even the cleanup is an XS task easily handled by the nightly runner as a LOW-risk SKILL.md edit. Spending a subconscious cycle on it is over-engineering.

### Verdict: **ELIMINATED**
Re-recommending a pending_autonomous item violates governance. The stale Item A cleanup is LOW enough for the nightly runner, not the subconscious.

---

## Idea C: Booking Flow Diagnosis on Real Tenants

### Challenge
"The audit says 'trace the booking flow on a real tenant end-to-end' — that's exactly what this idea proposes. Isn't the follow-up action explicitly called out in the audit?"

### Defense
- Yes, the audit explicitly says "Follow-up (next session): trace the booking flow." But the audit means a *human-interactive session*, not the subconscious loop.
- The booking flow diagnosis requires:
  1. Querying `booking_enabled` on specific tenants (MCP call — fine)
  2. Tracing the widget → API → DB flow manually (requires interactive session)
  3. Deciding whether to backfill existing tenants (tenant notification risk)
- The subconscious is a *recommendation* system, not an investigator. The correct output is a GH issue flagging the investigation, not a subconscious winner driving a complex trace.
- If put in improvement-backlog.md as a parking lot item with a pre-written GH issue template, the user can open it manually or let the nightly create it.

### Verdict: **ELIMINATED → parking lot**
Too investigational for autonomous action. Becomes parking lot item with GH issue template.

---

## Final Ranking

| Rank | Idea | Verdict |
|------|------|---------|
| 1 | Lead Source Analytics Dashboard | **WINNER** |
| 2 | Booking Flow Diagnosis | parking lot |
| 3 | Step 9E / Stale Item A | already in pipeline |
| 4 | Weekly Funnel Report Scheduler | parking lot (pending script smoke test) |
| 5 | Warm Lead Recovery Email | parking lot (email deliverability risk) |
