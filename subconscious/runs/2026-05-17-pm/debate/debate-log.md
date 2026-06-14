# Debate Log — 2026-05-17-pm (Run 22)

Top 3 by impact: Idea 1 (autopilot restart), Idea 2 (check_project_invariants), Idea 3 (Handoff GH issue).

---

## Idea 1: Restart autopilot-issue-loop + Tag S-effort items as ai-ready

### Challenge
1. **Is the loop actually configured?** Zero evidence the issue-to-pr-loop has EVER run in production. `git log --oneline --grep="issue-to-pr-loop"` returns nothing in 12 days. Recommending "restart" implies it was running — was it? Recommending a vague "verify and enable" sends the human into an unknown configuration rabbit hole.
2. **Moratorium protocol conflict:** S-effort items (runs 7+8+14+19) are each <20 min. Telling the human to configure a CI/CD system to auto-implement them costs more time than just doing the 4 items directly.
3. **Run 21 explicitly killed ai-ready tags** as an idea because "Loop confirmed dormant." Run 22 reviving the same idea with "restart first" is a variation — not new evidence.
4. **Cascade risk:** If loop is misconfigured (rate limits, missing GH_TOKEN, stale branches), the human wastes 30+ min on setup before any S-effort item is implemented. Net time: longer than doing the items manually.
5. **Execution force unclear.** Recommending "restart + tag" produces zero artifacts in this session. The human must act on 2 separate things (loop config + GH labels) before any benefit materializes.

### Defend
- Run 21 backlog explicitly mandates this: "Run 22 governance action: Restart autopilot-issue-loop.yml + add ai-ready label to S-effort items."
- If loop is running: 4 items auto-cleared in one poll cycle. Payoff: 4x leverage on human time.
- The distinction from run 21's killed idea is real: run 21 killed "tagging for a dormant loop." Run 22 adds "restart FIRST" — sequential not simultaneous.
- Issue-to-pr-loop SKILL.md exists at `.claude/skills/issue-to-pr-loop/SKILL.md`. The loop was designed for this exact scenario.

### Counter-challenge
The defend argument assumes the loop is restartable and will work once restarted. No evidence either way. The loop has never been observed running based on git log. The `loop dormant` finding from runs 16-21 was based on zero production commits, not on confirming the loop is misconfigured vs simply not triggered. High uncertainty.

**If the human wants to pursue autopilot restart, the prerequisite is FIRST confirming `.github/workflows/issue-to-pr.yml` exists and is correctly configured — that investigation itself is outside this recommendation's scope.**

### Verdict: **WEAKENED** — Valid governance mandate but high execution uncertainty. Better as parking lot alongside winner than as winner itself. Recommend human verify loop config as parallel action.

---

## Idea 2: Wire check_project_invariants.py into pre-commit hook

### Challenge
1. **Run 8 was already this recommendation, 22 days ago.** If the human didn't do it then, why would run 22's recommendation produce different behavior?
2. **Pending count: 7→6.** One item off 7 is not moratorium exit (need ≤3). This makes minimal structural progress.
3. **The meta-issue is not pre-commit gaps — it's implementation velocity.** Recommending a code-health item when the system is completely stalled on all 7 pending items doesn't address the root cause.
4. **Low drama.** Adding 2-3 lines to a pre-commit hook is the least consequential action in the backlog. Is the highest-ROI run 22 recommendation really "add a line to a script"?

### Defend
1. **The human is PRESENT RIGHT NOW.** This is run 22's unique forcing function. Runs 1-21 produced recommendations and then the human was absent. Right now they're in the session. The most actionable recommendation is the one implementable in THIS session — ~5 minutes.
2. **No blockers exist.** Script passes 6/6 checks. Pre-commit is the integration point. 2-3 lines. Zero external dependencies. No migrations, no GH Actions, no AWS, no Twilio. The probability of this specific recommendation being implemented in the next 5 minutes is ~80%.
3. **Compound effect.** Every moratorium item drops pending by 1. Going from 7 to 6 doesn't exit moratorium, but it demonstrates the implementation loop CAN work. One implementation since May 5 resets the zero-momentum narrative.
4. **Run 8 wasn't implemented because the human wasn't engaged.** The context for run 22 is different: the human is running the subconscious interactively. Active session = active approver.
5. **Evidence is fresh.** May 17 nightly review confirms: pre-commit has 9 checks. check_project_invariants.py passes all 6 tests. Em-dash blocker cleared on May 5 (8f680e8). This is ready to wire.

### Counter-challenge on "human is present"
This argument applies to ALL ideas. The human being present doesn't specifically favor check_project_invariants over Zapier or Handoff. Why this one?

**Response:** Because it's 5 minutes. The Handoff feature is 1.5 days. Zapier requires reading zapier_auth.py and writing a regression test. check_project_invariants is 2-3 lines in a file that already exists and passes today. The human being present is a window — use it for the narrowest possible action that clears a real backlog item. Capture the win.

### Verdict: **SURVIVES → WINNER.** Most atomic, zero blockers, human-present window. Highest probability of implementation in this session. Run 8's 22-day dormancy was absence; run 22's context is presence.

---

## Idea 3: Create AI-to-Human Handoff GH issue (run 21 repeat)

### Challenge
1. **Run 21 already recommended this.** Run 21 winning-concept.md was committed at 642c9a1 today. The human ran the subconscious, got the recommendation, and has not created the GH issue in the hours since. Run 22 recommending the same thing ~12 hours later produces no new forcing function.
2. **Creating a GH issue is administrative overhead, not a feature.** The feature itself (run 4, 32 days pending) is what adds value — not a tracking issue. The issue creation step adds one more artifact to review before anything ships.
3. **The handoff feature recommendation (run 4) already exists as an `active_directions` entry.** The implementation sketch from run 21 is already in `subconscious/runs/2026-05-17/winning-concept.md`. A second GH issue duplicates that information.
4. **Category doesn't match moratorium protocol.** Moratorium requires prioritizing oldest S-effort items. Handoff is M-effort (1.5 days). Recommending it again violates moratorium discipline.

### Defend
1. **GH issue converts subconscious artifact to GitHub-native sprint entry.** The human needs to go to GitHub to assign, label, and add to sprint. The winning-concept.md is only discoverable if the human reads subconscious/. GH issue is discoverable from the normal engineering workflow.
2. **32 days. CRITICAL. All 7 industries.** Evidence is overwhelming. Every day this isn't implemented is a conversion gap.
3. **Run 20 backlog explicitly authorizes parallel track** for AI-to-Human Handoff.
4. **Run 21 winner was committed <12 hours ago.** Not enough time to declare it "failed to produce implementation." The human may act on it later today.

### Counter-challenge
The defend argument for point 4 actually weakens idea 3: if run 21 may still be implemented today, run 22 recommending the same thing is premature. Run 22 should pick something DIFFERENT to add coverage.

**The subconscious compounds by picking new winners each run, not by repeating the same winner two runs in a row.**

### Verdict: **WEAKENED** — Valid feature, wrong vehicle. Repeating run 21 winner in run 22 (same day, same recommendation) violates the "compound" principle. The implementation sketch exists. If the human wants to create the GH issue, they have everything they need from run 21's winning-concept.md. Demote to parking lot.

---

## Summary Table

| Idea | Verdict | Reason |
|------|---------|--------|
| Idea 1: Autopilot loop restart | WEAKENED → parking lot | Execution uncertainty; loop config unverified; manual items faster |
| Idea 2: Wire check_project_invariants.py | **SURVIVES → WINNER** | 5 min, zero blockers, human present, run 8 mandate, highest implementation probability |
| Idea 3: AI-to-Human Handoff GH issue | WEAKENED → parking lot | Same-day repeat of run 21 winner; implementation sketch already exists |
