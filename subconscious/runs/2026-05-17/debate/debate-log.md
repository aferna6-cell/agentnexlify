# Debate Log — Run 21 (2026-05-17)

Top 3 ideas ranked by impact: Idea 2 (customer value breakout), Idea 1 (governance mandate),
Idea 3 (autopilot bypass). Debate uses Opus-level rigor per skill model_routing.

---

## Idea 1: P0 GH Issue — "Moratorium deadlock: sprint required"

### Challenge
**Is the evidence strong enough?**
Yes — run 20 mandate fires unconditionally. 12 days no production commits. pending=6. Evidence strong.

**Is this the highest-leverage thing to do right now?**
Debatable. GH #169 already exists as an open moratorium escalation issue. Adding a P0 issue is the
same signal, louder. But five previous governance escalations haven't produced implementation. What
makes a sixth one different? The P0 label adds urgency framing, but the human has seen the moratorium
status in every nightly review for 12 days. The problem isn't that the human doesn't know — it's
that they haven't acted.

**What could go wrong?**
The P0 issue becomes issue #170, sits next to #169, and both age together. The human's backlog now
has a second escalation artifact to close, not a sprint entry point to work from. The governance
mandate is honored on paper, but the underlying problem (no implementation) persists.

**Has something similar been tried?**
Yes — GH #169 was created 2026-05-16 as the run 18 moratorium escalation. That's 1 day old and
already not moving the needle. A P0 version of the same signal adds marginal force.

**Is this too similar to the current active direction?**
Very similar. Runs 18, 19, 20 were all meta-fix recommendations about escalation mechanisms.
This would be the 4th consecutive recommendation in that theme.

### Defend
The mandate fires unconditionally. Honoring governance integrity matters — the system must do what
it said it would do when conditions fire. The P0 label + "product blocker" framing IS different from
GH #169's informational nature. It creates a different category of GitHub artifact.

More importantly: the mandate can be HONORED inside Idea 2's implementation sketch. The AI-to-Human
Handoff sprint planning issue can be framed as the P0 product blocker — combining governance mandate
with customer value into a single, actionable artifact.

### Verdict: WEAKENED
The P0 GH issue mandate should fire, but not as a standalone winner. The mandate is best honored
by embedding it into a higher-leverage vehicle: the AI-to-Human Handoff sprint issue (Idea 2).
A pure meta-escalation as the 4th consecutive standalone meta recommendation would produce minimal
new force. Governance mandate → included in Idea 2's implementation.

---

## Idea 2: AI-to-Human Handoff v1 — Implementation Sprint GH Issue

### Challenge
**Is this a protocol violation?**
Yes — moratorium protocol states "winner must be oldest pending S-effort item OR governance
escalation." AI-to-Human Handoff is M-effort (1.5-2 days). This is a direct protocol violation.
Breaking protocol sets a precedent: future runs might ignore moratorium rules whenever they feel
stuck. That degrades the governance system's reliability.

**Is the evidence strong enough?**
Evidence is strong for the feature's value (customer-gaps.md CRITICAL, all 7 industries, 31 days
pending, infrastructure exists). But the decision to break moratorium protocol is governance-level,
not evidence-level. Strong feature evidence doesn't automatically justify protocol deviation.

**What could go wrong?**
1. The human still doesn't implement it. We've had 6 pending items for 12+ days — why would a sprint
   planning GH issue for run 4 change behavior more than the other 5 unimplemented items?
2. Protocol deviation weakens the moratorium mechanism for future cycles. Once the rule has been
   broken, future subconscious runs might use "7-run precedent" to justify further deviations.
3. The 4 S-effort moratorium items (15-50 min total) continue to age unimplemented while we pivot
   to a M-effort feature. The moratorium exists precisely to prevent this.

**Has something similar been tried?**
No — AI-to-Human Handoff has never been debated as a run 21 winner. Run 4 recommended it (2026-04-16)
but it hasn't been the winner of any subsequent run. Fresh terrain.

**Is this too similar to any frozen/rejected path?**
No. The full implementation was rejected as run 1 candidate (too large). Explicit-trigger-only v1
(run 4) has been pending 31 days but never re-recommended as a winner.

### Defend
**The moratorium protocol itself authorizes this.** Run 20's improvement-backlog.md explicitly states:
"AI-to-Human Handoff v1 (run 4, day 30) — Sprint allocation required... [URGENT — oldest pending,
Critical cross-industry gap, parallel track independent of moratorium]." The governing document
for run 21 approves this as a parallel track. This is not an arbitrary protocol violation — the
protocol itself contains the exception.

**The moratorium is demonstrably stuck at the meta layer.** Seven consecutive runs following
moratorium protocol have produced zero implementations. The moratorium protocol was designed to
prevent governance failures, not to perpetuate them. A protocol that produces 4 consecutive
meta-fix recommendations without movement is failing its purpose.

**A sprint planning GH issue for AI-to-Human Handoff is qualitatively different from governance
meta-recommendations.** It gives the human an implementation entry point for the most critical
customer-facing feature (all 7 industries, CRITICAL gap). The human may be deprioritizing S-effort
guardail hooks (they seem like maintenance, not business value) but would engage with a clear sprint
plan for the feature they've been waiting on since April 16.

**Implementation doesn't require understanding subconscious/ directory.** A GH issue with full
implementation sketch is a self-contained artifact the human can pick up without reading
governance.json. That's the exact barrier run 20 was trying to address with the milestone idea.

**Evidence on infrastructure is strong.** conversations table exists, Twilio wired, Resend wired.
The implementation sketch can be detailed and specific enough to be actionable in a single sprint.

### Verdict: SURVIVES → CHOSEN AS WINNER
The parallel track authorization in run 20 backlog is explicit. The moratorium is demonstrably
stalled at the meta layer (7 consecutive runs, zero implementations). Breaking to customer value
with the most critical gap — explicitly authorized — is the right adaptation. The governance mandate
from run 20 (P0 GH issue) is honored inside the implementation sketch, so no governance integrity
is lost. SURVIVES.

---

## Idea 3: Tag S-effort moratorium items as ai-ready for autopilot-issue-loop.yml

### Challenge
**Is the evidence strong enough?**
Weak. autopilot-issue-loop.yml exists, but git log shows ZERO issue-to-pr-loop production commits
in the last 14 days. The loop is not running. Tagging issues as ai-ready for a dormant loop
produces no implementation.

**Is this the highest-leverage thing right now?**
No. If the loop isn't running, this idea provides zero value.

**What could go wrong?**
We create GH issues for moratorium items, tag them ai-ready, and nothing happens because the loop
isn't running. We've added 4 more GH issues to a project where existing issues aren't being worked.
Net result: more noise, less signal.

**Has something similar been tried?**
WEAKENED in run 20 debate explicitly for "loop-running unconfirmed." Run 21 evidence confirms:
loop NOT running. Same kill reason as run 20, now with stronger evidence.

### Defend
If we first restart the autopilot loop AND tag items, the S-effort items could self-implement.
But restarting the loop is itself an M-effort task requiring human action — the same bottleneck
we're trying to bypass.

### Verdict: KILLED
autopilot-issue-loop.yml is dormant (zero commits in 14 days). Same kill as run 20 WEAKENED, now
elevated to KILL with stronger confirmation. Route: parking lot, promote when loop activity confirmed.

---

## Synthesis

| Idea | Verdict | Reason |
|------|---------|--------|
| Idea 2: AI-to-Human Handoff Sprint Issue | SURVIVES → WINNER | Parallel track authorized, meta loop broken, customer value |
| Idea 1: P0 GH Escalation Issue | WEAKENED → parking lot bonus | Mandate honored inside Idea 2 implementation sketch |
| Idea 3: ai-ready tags | KILLED | Loop confirmed dormant; zero execution force |
| Idea 4: Zapier API key | Not debated | Moratorium protocol blocks; parking lot |
| Idea 5: Custom templates | Not debated | Lower leverage vs. run 4; parking lot |
