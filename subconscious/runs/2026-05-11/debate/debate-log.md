# Debate Log — Run 16 (2026-05-11)

**Mode:** Moratorium (pending_approvals = 4 > threshold = 3)
**Debating top 3 ideas by impact**

---

## Idea 1: Widget 3-Copy Sync Guard (run 7, day 17)

### Challenge
Three objections:

**C1: Diminishing returns.** Run 15 recommended this exact item 3 days ago. Zero action was taken. If a recommendation produces no implementation in 3 days, does repeating it help? At what point does repetition indicate a process failure rather than a recommendation quality problem?

**C2: Risk is actually low right now.** Nightly reviews May 9-10 report "widget 3-copy sync PASS" — the 3 copies are currently byte-identical. The guard prevents FUTURE divergence, not a current crisis. With nightly manual coverage, the practical risk window is 24 hours (the nightly review catches it the next day). Is that worth escalating over a new idea?

**C3: Two consecutive moratorium runs with the same winner = system is stuck.** The compounding promise of the subconscious is each run builds on the previous. Runs 15→16 with identical winners is not compounding — it's repeating. Should we break the moratorium with a high-value new idea instead?

### Defend

**D1: Repetition IS the mechanism.** JS Silent Catch was recommended in runs 3, 9, 10, 11, 12, 13 — 6 consecutive moratorium-mode recommendations — before being implemented via 72f8204. The implementation lag is a human attention problem, not a recommendation quality problem. The moratorium protocol was designed to apply sustained pressure until S-effort items are cleared. Abandoning it after 2 runs would reset the pressure and guarantee the backlog grows further.

**D2: Nightly manual coverage is NOT equivalent to automated hook enforcement.** The nightly check catches divergence 12-24 hours after it occurs — after a push has already gone to production. A pre-push hook blocks the divergence BEFORE it reaches the repo. The distinction matters: post-hoc detection vs prevention. With 3 tenants embedding the widget, even 24 hours of broken embeds is a support incident. The guard is prevention, not redundancy.

**D3: Moratorium has a clear exit condition: implement the S-effort items.** Breaking moratorium with a new idea would add a 5th pending item, moving the exit condition FURTHER away. The system is not stuck — it's correctly applying pressure on the highest-leverage unblocked action. "Same winner" is not failure; it's persistence. See JS Silent Catch precedent.

### Verdict: **SURVIVES** → CHOSEN WINNER
Strongest evidence (moratorium mandate + S-effort + no blockers + 17 days pending + implementation sketch complete in run 15). Repetition is not dysfunction — it's the mechanism.

---

## Idea 2: Zapier API key plan_status enforcement (security, issue #107)

### Challenge

**C1: Moratorium forbids new pending items.** Adding this as the winner creates a 5th pending item, moving the exit condition from 4→1 (if S-effort items clear) to 5→1. The moratorium protocol has no carved-out security exception.

**C2: Issue #107 already provides tracking pressure.** The bug is filed, labeled HIGH, assigned. GH issue tracking provides exactly the implementation pressure that a subconscious recommendation would add — without adding to the pending queue. Dual-tracking the same fix in both GH and the subconscious winner queue duplicates overhead without adding value.

**C3: The subconscious winner queue is for structural improvements, not bug fixes.** Zapier plan_status is a code fix with a known solution (one filter predicate + one test). It belongs in the GH issue → PR loop, not in the 4-item human approval queue with weeks-long lead time. Routing it through subconscious slows it down.

### Defend

**D1:** Security matters. A cancelled tenant using Zapier features after cancellation is both a revenue issue and a compliance issue. The 11-day lag on issue #107 suggests it's not getting implemented via the GH issue route either.

**D2:** Fair point, but the GH issue route is more appropriate for this category of fix. If the issue isn't moving, the right escalation is to the issue-to-pr-loop skill, not to the subconscious winner queue.

### Verdict: **KILLED** — moratorium protocol + issue already tracked + wrong queue for a targeted bug fix
Note for parking lot: promote to first non-moratorium winner if issue #107 is still open when moratorium exits.

---

## Idea 3: widget_helpers.py smoke tests (parking lot ROI 2.0)

### Challenge

**C1: Moratorium forbids new items.** Same protocol argument as Idea 2.

**C2: 23 days of production use IS the verification.** The split (6cf4646) has been running in production since April 18. If the split had broken anything — widget chat, lead capture, booking flow — Railway logs would show errors and nightly reviews would have flagged them. The `implemented_unverified` governance status is stale, not dangerous. The real risk expired around day 7 post-deployment.

**C3: Lower leverage than clearing pending items.** Writing smoke tests for 23-day-old production code is cleanup, not prevention. The moratorium window should be spent clearing the 4 pending structural guards, not updating governance status for code that's been proven by production.

### Defend

**D1:** The governance status `implemented_unverified` is misleading to future Claude sessions and agents — they may treat the split as unverified when it isn't. Updating the status is still valuable.

**D2:** Fair. But this can be handled as a governance note update rather than a full subconscious recommendation. It doesn't require human approval.

### Verdict: **KILLED** — moratorium + effectively verified by production + lower leverage than clearing pending queue
Note: update governance status for run 5 from `implemented_unverified` to `implemented_production_verified` in this run's governance update.

---

## Summary

| Idea | Verdict | Reason |
|------|---------|--------|
| Widget 3-Copy Sync Guard (run 7, day 17) | **SURVIVES → WINNER** | Moratorium mandate, S-effort, no blockers |
| Zapier API key plan_status enforcement | **KILLED** | Moratorium, GH#107 already tracked, wrong queue |
| widget_helpers.py smoke tests | **KILLED** | Moratorium, 23 days production = verified |

**Winner: Widget 3-Copy Sync Guard** — moratorium mandate, run 7 re-escalation day 17.
