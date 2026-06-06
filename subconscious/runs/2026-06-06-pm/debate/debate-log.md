# Debate Log — Run 2026-06-06-pm (Run 52)

Top 3 ideas ranked by impact, each challenged and defended.

---

## Idea 1: Add post-fix re-scan to nightly SKILL.md

### Challenge Round 1: Is the evidence strong enough?

**Challenge:** Only 1 confirmed occurrence (nightly 2026-06-05). Could be coincidence. The nightly tonight may apply Item A from scratch anyway (fresh cycle, pre-condition already met). Why change the SKILL.md for one occurrence?

**Defend:** Not coincidence — it's structural. The nightly SKILL.md has a deterministic sequence: (1) scan pending_autonomous pre-conditions, (2) review commits, (3) apply LOW-risk fixes, (4) verify. Step 1 runs BEFORE step 3. If a fix in step 3 changes a pre-condition, step 1 has already passed and won't re-fire. This is a structural ordering problem, not a one-off. Every future scenario where Fix X unblocks Autonomous Item Y will hit the same gap.

The nightly log is conclusive: "Verification: check_project_invariants.py → all 6 checks PASS, exit 0" appears in the log AFTER the em-dash commit. "Standing Items: Item A (Check 10)" appears in the SAME log. The nightly knew both facts simultaneously and still didn't act.

Tonight's fresh nightly WILL apply Item A (pre-condition met from start). But that doesn't fix the structural gap.

**Verdict Round 1:** Challenge partially addressed. Evidence is structural, not coincidental.

### Challenge Round 2: Is this the highest-leverage thing to do right now?

**Challenge:** The moratorium has 15 pending items. The most impactful thing is closing them. This SKILL.md fix is meta — improving the improvement system. Wouldn't working directly on the pending items (PR #183, email split) produce more value?

**Defend:** The moratorium persists because human commitment is the bottleneck for MEDIUM/HIGH items, and the autonomous channel handles LOW-risk items. Improving the autonomous channel directly compounds: every future LOW-risk autonomous item executes 1 cycle faster. Item A (Check 10) applies tonight instead of tomorrow. Item B (check-widget-sync.sh) may cascade from tonight's run if run 50 scope extension fires.

The human-required items (PR #183 merge, email split) are already captured in active_directions and won't move until the human acts — regardless of what the subconscious recommends. Recommending them again is mechanical, not high-leverage.

This fix is the highest-leverage thing the SYSTEM can do today.

**Verdict Round 2:** Confirmed. Highest-leverage for the autonomous system.

### Challenge Round 3: What could go wrong?

**Challenge:** If the second pass re-scans after fixes, could it execute items in the wrong order? Could it trigger an item whose pre-condition appeared to be met (e.g., check_project_invariants exits 0) but was actually not stable? Could it cause a double-commit?

**Defend:** Scope guardrails prevent catastrophic failures. The same scope rules apply in the second pass as in the first — only `pending_autonomous + autonomous_executable: true` items within LOW-risk scope execute. The pre-condition for Item A is `check_project_invariants.py exits 0` — that's deterministic and stable (not a transient condition). Double-commit is impossible because Item A's action (adding 3 lines to pre-commit) is idempotent and the nightly would check "does Check 10 exist in pre-commit?" before adding.

**Verdict Round 3:** Risks are low and mitigated by existing scope guardrails.

### Overall Verdict: **SURVIVES → WINNER**

Strong structural evidence. Highest-leverage autonomous action. Low risk. AUTONOMOUS-EXECUTABLE (SKILL.md edit, same class as runs 40/43 implemented by nightly).

---

## Idea 2: Merge PR #183 (billing fix, run 51 winner)

### Challenge Round 1: Is this new enough to be a run 52 winner?

**Challenge:** Run 51 (yesterday PM) already recommended this. No new framing. No new evidence. Subconscious run 52 recommending the same thing as run 51 without new evidence is a mechanical repetition — the pattern that governance penalizes (run 35 rejected_paths: "recommendation loop exhausted at 5 consecutive runs"). Is the system just playing a broken record?

**Defend:** There IS one piece of new evidence: the nightly 2026-06-05 ran and did NOT apply Item A despite pre-condition being met. This demonstrates the autonomous chain is not as reliable as assumed. Every day without PR #183 merge extends the moratorium. But the framing hasn't changed: it's still "human does 10-min review."

The broken-record concern is valid. Run 51 was the first time the "merge existing PR" framing appeared. 1-run penalty before weakening is harsh. But the point stands: repeating this as the winner adds a pending count entry and occupies active_directions space without moving the bottleneck (human commitment).

**Verdict Round 1:** Challenge sustained. No new evidence, no new framing. This is better as a bonus action, not a winner.

### Challenge Round 2: Does this address the right problem?

**Challenge:** The human hasn't merged PR #183 in 24 hours. Why would run 52 recommending it change anything? The subconscious recommending human actions that the human consistently doesn't execute is the moratorium pattern. 51 runs showed that mechanism has limited effectiveness. Is the subconscious doing anything different here?

**Defend:** The subconscious can't force human action — it can only surface and escalate. But at some point, repetition without new forcing function is noise not signal. Run 51 is still the active recommendation. Run 52 should work on something the SYSTEM can move.

### Overall Verdict: **WEAKENED → bonus action**

Already captured as run 51's active_direction. No new forcing function. System should focus on what it can execute autonomously.

---

## Idea 3: Tag GH #107 (Zapier security) as ai-ready

### Challenge Round 1: Is the evidence strong enough?

**Challenge:** Issue filed 37 days ago but parking lot note explicitly says "route via issue-to-pr-loop, NOT subconscious winner queue." No new evidence of exploitation. No new urgency signal. Cancelled tenants with un-revoked Zapier API keys is a low-probability attack vector — Zapier keys are typically managed at the integration level. Is there evidence this is actively being exploited?

**Defend:** No exploitation evidence. But security gaps don't announce themselves before exploitation. The fix is small (add plan_status filter), the route is correct (issue-to-pr-loop not subconscious), and the action is 2 minutes. Parking lot ROI 2.5.

### Challenge Round 2: Is this the highest-leverage thing to do right now?

**Challenge:** The subconscious mission is to pick ONE winner per run. Tagging a GH issue with `ai-ready` is a 2-minute action that any commit could do — it doesn't require a dedicated subconscious run. During an active moratorium with 15 pending items, using the winner slot on a GH label change is a poor allocation.

**Defend:** Small actions compound. But the winning slot is precious and this doesn't address the core bottleneck (moratorium, autonomous system reliability, billing gap).

**Verdict Round 2:** Challenge sustained.

### Challenge Round 3: Has this been tried before?

**Challenge:** Parking lot note says "route via issue-to-pr-loop" — it's been punted consistently since run 16. This is the first time it's in the debate. But GH issue #107 presumably already exists and presumably the issue-to-pr-loop could pick it up based on issue content alone. Is adding `ai-ready` actually necessary?

**Defend:** issue-to-pr-loop uses the `ai-ready` label as a trigger. Without it, GH #107 won't get picked up. So the label is the enabler. But the action is so small it could be done as a bonus action in any run.

### Overall Verdict: **WEAKENED → parking lot**

Valid security gap. Route via issue-to-pr-loop. But not winner-tier during moratorium when higher-leverage items exist. Recommend as bonus action in any human session.

---

## Synthesis

| Idea | Verdict | Disposition |
|------|---------|-------------|
| Post-fix re-scan to nightly SKILL.md | **SURVIVES** | → **WINNER** |
| Merge PR #183 (billing fix) | **WEAKENED** | → Bonus A (already active_direction run 51) |
| Tag GH #107 Zapier as ai-ready | **WEAKENED** | → Parking lot / Bonus B |
