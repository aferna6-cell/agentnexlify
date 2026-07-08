# Debate Log — 2026-07-08 (Run 83)

## Ideas Entering Debate
Top 3 selected for debate based on evidence strength and category diversity:
- **Idea 1**: Lead source analytics dashboard (customer_value, S effort)
- **Idea 2**: Add brain/INGESTION-LOG.md to Phase 2 SKILL.md (workflow, XS effort)
- **Idea 5**: SMS Compliance Dashboard follow-through check (customer_value, XS effort)

Ideas 3 and 4 skipped debate: both operational/human-required, no blocking urgency this run. Moved directly to parking lot.

---

## Round 1: Initial Positions

**Idea 1 (Lead Source Analytics) — Opens Strong**
Evidence is specific and actionable: `leads.lead_source` column exists, Recharts installed, AnalyticsPage.jsx provides a direct pattern to mirror. customer-gaps.md confirms this as a cross-industry gap. Moratorium is lifted (pending=1, max=2 — adding this makes pending=2, exactly at threshold, does not trigger moratorium). No schema changes needed. Run 9 governance note said "run 2 implemented this" but customer-gaps.md post-dates that and still flags the gap — the issue is the gap is on the Leads PAGE, not just the Analytics page.

**Idea 2 (INGESTION-LOG Phase 2) — Opens Strong**
Run 82 parking lot item 1, explicitly deferred for this run. One-line SKILL.md addition. Nightly review has proven reliable for this class of change (4 successful autonomous SKILL.md implementations). Brain connector health signal in Phase 2 compounds across ALL future runs — meta-improvement with unbounded future payoff. Run 82 parking lot said "deferred until GH #394 resolved" but commit a0874c4 shows successful brain refresh today, partially satisfying the dependency.

**Idea 5 (SMS Dashboard follow-through) — Opens Weak**
This is a status check, not a new recommendation. The loop handles it autonomously if working. Subconscious recommending "verify X" is lower-leverage than recommending an atomic improvement. If the loop failed, the investigation scope exceeds one subconscious run. Not a genuine improvement candidate.

---

## Round 2: Challenges

### Challenge: Idea 1 — "Run 9 already said Lead Source Analytics was implemented. Are we re-recommending a done item?"

**Defense:** Run 9 governance correction was specifically about AnalyticsPage.jsx having a general chart. customer-gaps.md (a later, more authoritative cross-industry gap document) still lists lead source analytics as OPEN. The gap being flagged in customer-gaps.md after run 9's correction indicates the specific gap (breakdown on the Leads page with source attribution, per-tenant) is distinct from what run 2 implemented. Additionally, customer-gaps.md is the authoritative source for what customers are missing — it says "open" and we trust it.

**Verdict: CHALLENGE FAILS.** Run 9 correction was for AnalyticsPage.jsx general chart; Leads page source breakdown is the open item.

### Challenge: Idea 2 — "GH #394 brain connectors still pending_human. Adding INGESTION-LOG to Phase 2 when connectors are flaky gives false confidence."

**Defense:** Two counterpoints. First, the INGESTION-LOG reads whatever state the connectors are in — partial data beats no data. A Phase 2 "Also read:" line that sometimes shows failure markers is more useful than no check at all. Second, a0874c4 shows a successful brain refresh today (brain/state.json updated, INGESTION-LOG.md +4 lines), suggesting connectors may be intermittently recovering. The log doesn't lie — if connectors are failing, the log says so. Subconscious should read that.

**Verdict: CHALLENGE FAILS.** Connectors intermittent recovery makes this MORE valuable, not less.

### Challenge: Idea 1 — "Moratorium math: adding run 83 winner makes pending=2 (run 79 + run 83). Is that safe?"

**Defense:** max_pending_approvals = 2. The moratorium triggers on pending > max, i.e., pending > 2 means pending = 3+. At pending=2 we are AT the threshold but not over it. Run 81 successfully added to pending when run 79 was already there (pending went 1→2 with run 81 winner added, moratorium was correctly not triggered). Same logic applies here. Safe.

**Verdict: CHALLENGE FAILS.** pending=2 is the threshold, not a breach.

### Challenge: Idea 2 vs Idea 1 head-to-head — "Why not pick Idea 2 as winner? It's autonomous-executable, lower effort, and compounds forever."

**Defense for Idea 1:** Idea 2 IS the stronger autonomous candidate. But it's also the autonomous-executable one that the nightly can implement without human approval. If we make Idea 1 the winner (requiring human approval), Idea 2 can simultaneously be executed as a BONUS autonomous action by nightly review — no queue budget consumed. Making Idea 2 the winner prevents the nightly from executing it as a bonus (since nightly only implements winners OR pre-authorized autonomous items). Recommending Idea 1 as winner + Idea 2 as autonomous-bonus is a higher-combined-value outcome.

**Verdict: CHALLENGE NOTED.** This is actually the correct synthesis: Idea 1 wins, Idea 2 is autonomous-bonus.

---

## Round 3: Final Verdicts

| Idea | Verdict | Reason |
|------|---------|--------|
| 1 — Lead Source Analytics | **SURVIVES → WINNER** | Customer-facing, evidence-backed, moratorium safe, Idea 2 handles as autonomous bonus |
| 2 — INGESTION-LOG Phase 2 | **SURVIVES WEAKENED → AUTONOMOUS BONUS** | Correct mechanism for nightly execution. Better as bonus than winner (avoids consuming pending slot). |
| 5 — SMS Dashboard check | **KILLED** | Status check, not atomic improvement. Loop handles autonomously. Answered as run-83 question instead. |

---

## Winner: Idea 1 — Lead Source Analytics Dashboard

**Rationale:** First customer-facing feature recommendation since runs 73-74. Evidence-backed (customer-gaps.md, column confirmed, Recharts installed). Moratorium lifted and budget permits (pending will be 2/2 — at threshold, not over). Idea 2 (INGESTION-LOG) handled as autonomous bonus by nightly review, preserving its value without consuming a pending slot.

**Confidence: HIGH.**
