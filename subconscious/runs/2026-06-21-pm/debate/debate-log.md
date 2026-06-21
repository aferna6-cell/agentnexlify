# Debate Log — 2026-06-21-pm (Run 65)

## Top 3 Ideas (ranked by impact)

1. Combine GH #308 + GH #292/#293 into one PR (exits 7-cycle loop)
2. Fix GH #308 alone (mandate winner)
3. Plan-name presence guard in check_project_invariants.py (AUTONOMOUS-EXECUTABLE)

---

## Idea 1: Combine GH #308 + GH #292/#293 — "Two Production Bugs, One PR"

### Challenge Round 1: Mandate compliance
The run 64 mandate says GH #292/#293 unimplemented → GH #308 is the winner. This combined idea includes BOTH, which technically makes #308 the primary — mandate honored. But is bundling two unrelated bugs into one PR a bad practice? Mixed PRs obscure review and make git blame harder.

### Defense Round 1
Both bugs are in distinct, non-overlapping files with no shared logic. idempotency.py + stripe_webhooks.py (payment) vs sms_rate_limiter.py + api_key_auth.py + billing_reconciliation.py (plan gating). The PR title can be "Fix two production bugs: webhook idempotency + plan-name dicts" — reviewer can assess each independently. b3279b0 (today, Jun 21) fixed two completely unrelated bugs (stale MRR plan names + widget patch-leak) in one commit — precedent exists in this repo. One approval drops pending from 2 to 0 for both moratorium-override items.

### Challenge Round 2: Is "activation energy" really the bottleneck?
7 cycles without implementation — have we confirmed that approval friction is the actual bottleneck? It could be: (a) developer bandwidth, (b) fear of touching billing/payment code, (c) simply deprioritization. Combining doesn't fix bandwidth or prioritization.

### Defense Round 2
Precedent from moratorium history: runs 23-24 switched from "sprint PR" to "create a skill" when the bottleneck shifted from content to tool availability. The 7-cycle loop here has a different character — both bugs have complete, unambiguous sketches (lines/diffs known). Activation energy hypothesis is supported by: the moratorium-sprint skill worked when it bundled actions into a single invocation. A combined PR removes one context-switch (switching from fixing #308 to switching to fixing #292/#293). The human only needs to open one editor session, one PR, one review cycle.

### Challenge Round 3: Is this too novel? Alternating mandate has governance precedent — will breaking it set bad norms?
The alternating mandate was designed to prevent either bug from being permanently suppressed. Combining them honors BOTH mandates simultaneously. Governance: run 24 introduced a skill when 10 consecutive recs stalled — precedent for mechanism change at threshold. We're at 7 cycles. NEW mechanism = combined PR. Not a violation; an evolution.

### Verdict: SURVIVES — winner candidate

---

## Idea 2: Fix GH #308 alone (mandate winner)

### Challenge Round 1: Pattern history
GH #308 was winner in runs 59, 61, 63. Unimplemented all three times. This is the 4th time it's designated winner. Nominating it again under the same framing changes nothing about the implementation gap.

### Defense Round 1
Mandate is mandate. Without mandate enforcement the system drifts. GH #308 is genuinely the higher-severity bug: payment recovery failure means every customer whose card was fixed post-dunning may not have had payment retried. Each missed retry = revenue lost permanently (30-day dunning window closes). GH #292/#293 is breakage but doesn't lose existing revenue — it just degrades new-tenant experience.

### Challenge Round 2: But three consecutive cycles as designated winner without implementation
The 4th nomination in the same framing produces the same non-result. The MECHANISM is what's broken, not the diagnosis.

### Defense Round 2
The diagnosis is correct, the implementation is valuable, and mandate integrity matters. Including it as the PRIMARY in Idea 1 (combined PR) honors this.

### Verdict: WEAKENED — valid but subsumed by Idea 1 (combined PR). If Idea 1 adopted, #308 is the primary bug in the combination. If Idea 1 rejected, this becomes the fallback winner.

---

## Idea 3: Plan-name presence guard in check_project_invariants.py

### Challenge Round 1: Sequence dependency
Check 7 must come AFTER GH #292/#293 is fixed, or the check would permanently fail pre-commit. If recommended as winner before #292/#293, it blocks all commits on the dev machine until the plan dicts are also fixed. Sequence: fix dicts first, add guard second.

### Defense Round 1
Sequence is not a blocker — it's a constraint. If the combined PR (Idea 1) fixes both bugs together AND adds Check 7 in the same branch, the guard lands at the right moment. Alternatively, label it AUTONOMOUS-EXECUTABLE — nightly review can add it the night after #292/#293 lands. The parking lot entry (since run 61) already has this sequencing noted.

### Challenge Round 2: How much does this actually help? check_project_invariants.py already passes — the guard's value is for the NEXT repricing. Is that worth winning over an active production bug?

### Defense Round 2
b3279b0 (today) is the evidence: test drift happened at repricing. Without the guard, the NEXT repricing will create another 7-cycle alternating loop for different file names. The guard is cheap to add (~10 lines), autonomous, and permanent. But it is correctly sequence-blocked behind #292/#293.

### Verdict: SURVIVES → Parking lot / Bonus B (sequencing makes it wrong to pick as standalone winner before dicts are fixed). AUTONOMOUS-EXECUTABLE after combined PR lands.

---

## Summary

| Idea | Verdict | Disposition |
|------|---------|-------------|
| 1. Combined PR (GH #308 + #292/#293) | SURVIVES | WINNER |
| 2. Fix GH #308 alone | WEAKENED | Fallback if Idea 1 rejected |
| 3. Plan-name guard Check 7 | SURVIVES | Bonus B (AUTONOMOUS-EXECUTABLE after winner) |
| 4. Fix kb-autopopulate.sh | Not debated | Parking lot (ROI 1.8, lower priority vs active bugs) |
| 5. Post-repricing audit | Not debated | Bonus C (cheap research, pairs with combined PR) |

## Governance Note

RUN 65 MANDATE honored: GH #292/#293 unimplemented → GH #308 is the primary bug in the combined winner. The combined PR mechanism is a governance evolution (precedent: run 24 mechanism change at 10-cycle threshold; we are at 7 cycles). RUN 66 MANDATE: if combined PR still unimplemented → escalate via a GitHub issue tagged `ai-ready` with both fix sketches inline — lowest-activation-energy path for autonomous loop execution.
