# Debate Log — Run 83 (2026-07-08-pm)

Top 3 ideas by impact ranked: Idea 1, Idea 3, Idea 2.
Each runs a full challenge-and-defend cycle before verdict.

---

## Idea 1: Add issue-to-pr-loop health check to nightly SKILL.md as Step 9D

### Challenge
**C1 — Maybe the loop DID run.** Morning digest says "should have triggered" not "confirmed failed." ai-ready label added 2026-07-08 nightly (f958ab7). 15-min poll cycle means loop had at most 1-2 attempts before the morning digest was generated. GH Actions has propagation delay. We may be calling a false alarm.

**C2 — Duplication with Step 9C.** Step 9C already detects brain connector failures from INGESTION-LOG.md. The pattern is the same. Does adding Step 9D really close a monitoring gap or just add another check we might disable later?

**C3 — Effort scope inflation.** "Check for ai-ready issues with no PR in >24h" sounds XS. But autopilot-issue-loop.yml needs to be read, last_run_at needs to be parsed from GH Actions API, and the diagnostic comment needs to be written. Could be S or M effort, not XS.

**C4 — Run 83 mandate partially covers this.** Run 83 mandate already directs the nightly to "verify issue-to-pr-loop opened a draft PR for SMS Compliance Dashboard." If nightly already does this check as a one-off mandate item, why do we need a permanent Step 9D?

### Defend
**D1 — Mandate ≠ ongoing.** Run 83 mandate is a one-shot directive. Step 9D is a permanent health gate. The whole point of Step 9B and Step 9C was to convert one-shot mandate checks into always-on monitoring. Without Step 9D, the next stalled ai-ready issue will go undetected until someone notices manually.

**D2 — Propagation delay is real but bounded.** 15-min poll cycle × 2 attempts = 30 minutes max before first trigger. Morning digest generated ~6-8h after label was applied (label at nightly ~2:37 AM, digest at ~8 AM). Loop had 5+ hours and 20+ attempts to open a PR for #385. "Should have triggered" over 5+ hours is a real signal, not propagation noise.

**D3 — False alarm risk is low, missed alarm risk is high.** Step 9C brain connector was failing for 4+ days before run 79 detected it. KB autopopulate was broken 63 days. Same pattern threatens to recur here. Duplication criticism overstates overlap — Step 9C watches INGESTION-LOG.md (brain connectors), Step 9D watches GH Issues + GH Actions (ai-ready pipeline). Different systems, same monitoring philosophy.

**D4 — Scope inflation manageable.** GH Actions API is already queried by Step 9C (brain connector check). The pattern exists. Reuse it. Check: `autopilot-issue-loop.yml` last run time from GH Actions list_workflow_runs. Threshold: >4h since last run = stalled. Effort stays XS if we implement tightly.

### Verdict: **SURVIVES — WINNER**

Strongest idea in the set. The evidence is unambiguous: step pattern works (9B, 9C both caught real failures), the monitoring gap is confirmed (issue-to-pr-loop failure mode is undetected), and the implementation is concrete. Confidence: **MEDIUM-HIGH**. One uncertainty: we don't yet know for certain whether the loop stalled (vs slow to trigger). But if Step 9D exists, we find out within 24h rather than in a week.

---

## Idea 3: Lead source analytics dashboard — /api/leads/source-analytics + Recharts bar chart

### Challenge
**C1 — Wrong priority when the delivery pipeline is broken.** ai-ready #385 has no PR confirmed. Brain connectors are down day 8. KB is 63 days stale (first scheduled run today). If the loop that's supposed to build features is stalled, adding more ai-ready issues to the queue doesn't help. Fix the pipe before adding more tasks to it.

**C2 — Parking lot since run 2 = weak signal of real demand.** This has been deferred 80+ runs. If it were truly high-impact, someone would have asked for it. customer-gaps.md calls it "Low effort, HIGH impact" but the source of that rating is unclear. Without a tenant actively requesting it, this is intellectual interest, not market pull.

**C3 — Blocks a human session.** Lead source analytics requires a backend endpoint + frontend page + migrations. That's compound-engineering scope. Nightly can open the GH issue, but building it requires human code review and a worktree PR. If issue-to-pr-loop is stalled, tagging a second ai-ready issue before fixing the loop is adding backlog to a broken queue.

**C4 — No new evidence this run.** Run 83 evidence is entirely about monitoring gaps (brain connectors, KB autopopulate, issue-to-pr-loop). No customer request for lead source analytics surfaced in morning digest, bug-patterns.md, or nightly log. Proposing it now is a pattern continuation, not evidence-driven.

### Defend
**D1 — customer-gaps.md is authoritative.** Cross-industry, Low effort, the `source` column exists, Recharts installed. This is genuinely the easiest high-value feature in the backlog. Proposing as ai-ready issue costs 2 minutes and doesn't block any monitoring work.

**D2 — Pipeline repair is separate from backlog tagging.** Step 9D (Idea 1) fixes monitoring. Lead source analytics is a separate deliverable. These are parallel, not sequential.

**D3 — 82 runs of deferral is itself a concern.** If the system keeps deferring a "Low effort, HIGH impact" item every run, that's a subconscious failure mode: always choosing infrastructure over product. Customer value runs 2-82 should occasionally win.

### Counter-defense
D3 is partially true but this run has especially strong infrastructure evidence. D2 is true but we already have one winner (Idea 1). Adding a second recommendation would dilute focus. D1 is valid — the feature is real — but a parking lot recommendation keeps it active without flooding the governance queue.

### Verdict: **WEAKENED — Parking Lot**

Feature is real and chronically deferred. But the run 83 evidence doesn't generate net-new urgency for it — it's the same "cross-industry, Low effort" signal that's been in customer-gaps.md since run 2. Issue-to-pr-loop monitoring is more urgent this run. Mark active in improvement-backlog.md. Revisit run 84 if loop health is confirmed and pipeline is clear.

---

## Idea 2: Add brain/INGESTION-LOG.md to subconscious Phase 2 evidence sources

### Challenge
**C1 — Step 9C already covers this.** Nightly SKILL.md Step 9C added in run 80 specifically checks INGESTION-LOG.md for connector failures. The run 80 winner already added double-coverage for brain connector detection. Adding INGESTION-LOG.md to Phase 2 (subconscious evidence) creates triple-coverage with diminishing returns.

**C2 — Subconscious already catches it.** Run 79 detected brain connector failure after 4 days. Step 9C was designed to reduce that to 1-day detection. If Step 9C is running, subconscious Phase 2 doesn't need the same source. Adding the same signal to a different phase doesn't improve detection speed.

**C3 — Phase 2 bloat risk.** Subconscious already reads: git log, bug-patterns.md, customer-gaps.md, knowledge-base/INDEX.md, morning digest, nightly log. Each new source adds to the evidence-gathering burden. INGESTION-LOG.md is an operational health signal, not an improvement signal — Phase 2 is designed for the latter.

**C4 — Idea 1 subsumes the need.** If Step 9D is added (Idea 1 winner), the nightly catches loop failures within 24h. Phase 2 seeing INGESTION-LOG.md 2 runs later doesn't add much.

### Defend
**D1 — Step 9C can be disabled or stall without feedback.** If the nightly itself fails, Step 9C fails silently. Subconscious Phase 2 reading INGESTION-LOG.md is independent and provides a second detection path.

**D2 — Earlier subconscious signal could improve idea quality.** When INGESTION-LOG.md shows failures, subconscious might generate better ideas (connector-specific fixes) than when it sees the failure only through the morning digest summary.

**D3 — XS effort.** Literally adding one line to the SKILL.md Phase 2 evidence list and reading last 10 lines of INGESTION-LOG.md.

### Counter-defense
D1 is valid but thin. If the nightly itself fails, we have bigger problems than INGESTION-LOG.md. D2 is speculative — the brain connector issue is already well-documented; more sources don't improve ideation. D3 is true but low effort isn't sufficient to justify low signal.

### Verdict: **WEAKENED — Parking Lot (Run 84 candidate if Step 9D proves insufficient)**

Step 9C + Idea 1 (Step 9D) cover the brain connector monitoring gap more directly. Adding INGESTION-LOG.md to Phase 2 is redundant given the existing monitoring stack. Real ROI only if Step 9C + Step 9D both fail to catch a future connector outage. Defer to run 84.

---

## Final Ranking

| # | Idea | Verdict | Confidence |
|---|------|---------|------------|
| 1 | Issue-to-pr-loop health check (Step 9D) | WINNER | MEDIUM-HIGH |
| 2 | Lead source analytics dashboard | Parking Lot | — |
| 3 | INGESTION-LOG.md in Phase 2 | Parking Lot | — |
| 4 | Promote PR #387 + batch Dependabot | Operational (human-required, not a subconscious winner) | — |
| 5 | kb-autopopulate.yml monitoring (Step 9D alt) | Strong run 84 candidate | — |

**Winner: Idea 1 — Add issue-to-pr-loop health check to nightly SKILL.md as Step 9D**
