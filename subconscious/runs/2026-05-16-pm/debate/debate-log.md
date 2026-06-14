# Debate Log — 2026-05-16-pm (Run 20)

## Top 3 Ideas Debated (ranked by impact)
1. Idea 1: Governance Threshold Reduction + GH Milestone
2. Idea 4: Tag Runs 7+8+14 as ai-ready GH Issues
3. Idea 2: Repeat Run 19 SKILL.md Recommendation

---

## Round 1: Idea 1 — Governance Threshold Reduction + GH Milestone

### Challenge

- **Evidence strength:** Run 19 winning-concept.md §"After SKILL.md Updated" explicitly names this
  action: "If SKILL.md NOT updated by run 20: governance action: reduce max_pending_approvals 3→2 +
  create GH milestone." SKILL.md not updated confirmed. Evidence is airtight — mandate fires.

- **Is this highest leverage?** The threshold change (3→2) is future-prevention only. It does nothing
  to clear the current 5-item backlog. Are we addressing the right problem or just adding governance?

- **What could go wrong?** Lowering threshold to 2 means moratorium fires almost immediately after
  any 2 items accumulate. Could create excessive moratorium cycling on normal feature work. Is 2 too
  aggressive?

- **Prior rejection pattern?** "Moratorium Governance Self-Enforcing Threshold" sat in parking lot
  from run 8 (ROI 1.6). Run 14 explicitly noted: "governance parameter changes lower priority than
  clearing moratorium." The idea has been deprioritized twice.

- **Completeness concern:** Reducing the threshold doesn't exit the current moratorium — pending is
  still 5 after the change. Is this action sufficient?

### Defend

- The run 19 governance condition is a binding commitment by the system to itself. Not honoring it
  undermines the self-governance mechanism's credibility. A system that won't enforce its own rules
  becomes a system that's ignored.

- The threshold reduction and the parking-lot idea (run 8) are different: run 8 was "auto-trigger
  moratorium" (a mechanism change). Run 20 is "lower the trigger point" (a configuration change). The
  prior deprioritization was about a different scope.

- The GH milestone is NOT future-prevention — it's the current-situation action. A milestone with 4
  issues, effort estimates, and implementation sketch links is the most human-actionable form of the
  pending backlog. Human approver doesn't need to understand governance.json or subconscious/ to take
  action. This is qualitatively different from GH #169 ("moratorium is happening") — it says "do
  these 4 things in this order."

- The two together (threshold + milestone) address both: prevent recurrence AND exit current state.
  The governance spec says "max_pending_approvals + milestone" — not one or the other.

### Verdict: SURVIVES
Binding governance mandate from run 19 makes this the correct action. Milestone is the highest
human-actionable escalation mechanism available. Threshold reduction is a governance document
configuration change with bounded risk (2 is still reasonable; moratorium was designed to fire
early). WINNER candidate.

---

## Round 2: Idea 4 — Tag Runs 7+8+14 as ai-ready GH Issues

### Challenge

- **Evidence strength:** issue-to-pr-loop is documented as running every 15 min in SKILL.md. BUT:
  git log shows zero `[issue-to-pr-loop]` production commit tags since May 5. If the loop has been
  running and not producing commits, it's either not running, blocked, or has nothing to process.
  Creating ai-ready issues assumes loop is operational — unconfirmed.

- **Is this highest leverage?** If loop IS running: this is brilliant — moratorium exits autonomously,
  zero human effort. If loop is NOT running: effort wasted. Binary outcome with unconfirmed precondition.

- **What could go wrong?** Loop creates a PR for Widget Sync Guard. Pre-push hook runs. If
  check_project_invariants.py (run 8, still unwired) finds violations, the PR may fail. But human
  reviews PRs anyway — this isn't catastrophic, just noisy.

- **Prior run judgment:** Run 19 explicitly WEAKENED this idea: "WEAKENED this run (loop-running
  uncertainty). Promote to run 20 winner if SKILL.md update doesn't produce sustained GH pressure
  within 48h." Since SKILL.md wasn't updated, the loop produced no pressure. The promotion condition
  reads: "if SKILL.md update doesn't produce sustained GH pressure" — but SKILL.md was never updated.
  The condition was about the mechanism failing, not the mechanism never starting. Loop uncertainty
  remains the decisive blocker.

- **Scope concern:** Creating ai-ready issues is an implementation action. This recommendation requires
  the human to create 3 specific GH issues with specific labels and bodies. Is "create these GH issues"
  a sufficiently atomic, actionable recommendation?

### Defend

- Loop-running uncertainty is real but doesn't invalidate the recommendation. Even if loop isn't
  running today, ai-ready issues don't expire. They remain for the loop to pick up when it fires.

- The precondition check is trivial: `git log --oneline --grep 'issue-to-pr-loop' --since='7 days ago'`.
  Human can confirm in 30 seconds before acting on the recommendation.

- Run 19 said "promote if SKILL.md produces no sustained pressure" — no pressure was produced (SKILL.md
  not updated). Could be read as promoting this to winner.

### Counter-defense

- Run 19's framing was about the escalation mechanism failing after being tried. SKILL.md was never
  updated, so the escalation mechanism was never even attempted. The "loop uncertainty" objection from
  run 19 still stands — new evidence hasn't resolved it.

- Idea 1 (governance mandate) takes strict precedence over Idea 4 (conditional promotion). The mandate
  was unconditional ("if SKILL.md not updated → governance action"). The promotion was conditional
  ("if SKILL.md update produces no sustained pressure" — but SKILL.md was never tried).

### Verdict: WEAKENED
Loop-running uncertainty unresolved. Conditional promotion from run 19 doesn't clearly fire (SKILL.md
not tried, not failed). Remains parking lot. Promote explicitly when loop confirmed running via git log.

---

## Round 3: Idea 2 — Repeat Run 19 SKILL.md Recommendation (Third Escalation)

### Challenge

- **Evidence strength:** SKILL.md confirmed not updated. Evidence is clear. BUT: the recommendation
  has been made twice (runs 18, 19) without implementation. What new mechanism makes run 20 different?

- **Is this highest leverage?** Most direct path to the escalation loop. But third consecutive same
  recommendation with no implementation change. Same mechanism produces same result.

- **Freeze threshold risk:** If Idea 2 is recommended a third time and ignored, it hits
  freeze_threshold=3. This would permanently suppress the SKILL.md recommendation, which is wrong —
  the recommendation remains valid. The freeze mechanism would fire incorrectly.

- **Too similar to active direction?** Run 19's active_direction IS exactly this recommendation.
  Repeating it as run 20 winner provides no new escalation mechanism.

- **Pattern comparison:** Widget Sync Guard was recommended 4 consecutive times before governance
  switched winner. SKILL.md meta-fix has been recommended twice. Pattern: at 2+ consecutive same-
  mechanism recs without implementation, switch to a different escalation lever.

### Defend

- The SKILL.md update is still valid — 10 min, pre-written sketch, highest daily ROI. Urgency is
  higher with each missed day. GH #169 proves mechanism works when triggered.

- Some recommendations take 3+ attempts before implementation (JS Silent Catch took 10 runs). The
  recommendation should persist until implemented.

### Counter-defense

- JS Silent Catch was recommended persistently because the moratorium protocol requires repeating the
  OLDEST pending item. SKILL.md update is run 19 (day 0). It's NOT the oldest pending item. The
  moratorium protocol would prioritize runs 4 and 7 (oldest S-effort) over run 19.

- Including SKILL.md update as Bonus Step 0 in Idea 1's implementation sketch preserves the
  recommendation without making it the primary winner. Same net effect, avoids freeze risk.

### Verdict: KILLED as standalone winner
Subsumed by Idea 1 as Bonus Step 0. Three consecutive same-mechanism meta-fix recs without
implementation signals the mechanism needs to change. GH milestone provides the new mechanism
(GitHub-native, no subconscious/ knowledge required). Repeating the SKILL.md recommendation
alone has zero new force.

---

## Synthesis

| Idea | Verdict | Reason |
|------|---------|--------|
| Idea 1: Governance Threshold + Milestone | SURVIVES → **WINNER** | Binding run 19 mandate; milestone = new human-actionable mechanism |
| Idea 4: ai-ready GH Issues | WEAKENED → parking lot | Loop-running unconfirmed; conditional promotion doesn't clearly fire |
| Idea 2: Repeat SKILL.md | KILLED as winner | Third consecutive; mechanism unchanged; subsumed into Idea 1 Bonus Step 0 |
| Idea 3: Milestone Only | Not debated | Dominated by Idea 1 (same milestone + threshold at no extra cost) |
| Idea 5: Run 4 Sprint Allocation | Not debated | Out-of-moratorium scope; valid parallel track for later |
