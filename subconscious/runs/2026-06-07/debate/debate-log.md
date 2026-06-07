# Debate Log — Run 52 (2026-06-07)

Top 3 ideas debated by impact. Each runs 3 rounds of Challenge / Defend / Verdict.

---

## Idea 1: Remove Stale Item A Blocker from SKILL.md:69

### Round 1
**Challenge:** Is the stale blocker note actually the cause of Item A not firing? The nightly ran twice since 8db33df (6/5) with 0 autonomous items. Maybe there's another failure mode — the pre-condition check itself might be failing for a different reason.

**Defend:** Direct evidence chain: SKILL.md:69 says "Execute when script passes clean" immediately after the stale blocker sentence. The nightly log (2026-06-07) shows "Issues found: None. Action: None required" for commits — it did NOT attempt Item A at all. If the nightly had attempted Item A and the pre-condition (script exit code) failed, it would have logged a blocker and opened a MEDIUM issue. No such issue was filed. This means the nightly is skipping Item A without even attempting the pre-condition check — consistent with reading the blocker sentence as a signal to skip entirely. Additionally, run 50 confirmed "check_project_invariants.py exits 0" on 2026-06-05.

**Verdict after Round 1:** SURVIVES — causal chain is solid.

### Round 2
**Challenge:** This is a SKILL.md edit to an existing file. The proven autonomous channel is for CREATING new SKILL.md files, not editing existing ones. The human must make this edit. Given 37-day moratorium pattern of human inaction, is this any different from any other S-effort recommendation that hasn't been implemented?

**Defend:** The key difference: this is a 1-line deletion in a 170-line file (~1 min). Every other S-effort recommendation had either code complexity (3-line bash patch with unfamiliar syntax) or required finding the right location. This is: open SKILL.md, find line 69, delete one sentence, save. The evidence is crystal-clear and the action is unambiguous. Furthermore, the result is autonomous execution of Item A tonight — the 46-day item gets done WITHOUT the human writing any code. The human's only contribution is enabling the autonomous chain by removing a stale note.

**Verdict after Round 2:** SURVIVES — minimal friction, clear instruction.

### Round 3
**Challenge:** What if check_project_invariants.py fails for a new reason when the nightly actually runs it? The blocker was em-dash violations — those are fixed. But other invariants exist (client_id, status, areas_of_interest checks). If any new code landed in the last 2 days with a violation, the pre-commit will correctly fail, and the nightly will log a MEDIUM issue. This is expected behavior, not a failure mode.

**Defend:** This is a feature, not a bug. If a new violation exists, the pre-condition check catches it and the nightly files an issue. The whole point of Check 10 is to surface violations. Whether Item A fires tonight or files an issue for a new violation, both outcomes are correct.

**Verdict after Round 3:** SURVIVES → WINNER

---

## Idea 2: Fix auth.ts Timing-Safe Token Comparison (GH #206)

### Round 1
**Challenge:** The nightly review itself said "No auto-fix (auth code — requires human approval)." This means it requires human execution. Given the moratorium pattern (37 days, human inaction is the documented bottleneck), proposing a human-required fix means it will likely sit as pending item #16. Is the security benefit worth adding to the backlog?

**Defend:** The auth fix is genuinely new (GH #206 filed today). The implementation is clear (3-line TypeScript change with null guard). The Agent OS engine just expanded the agent-service surface significantly. And this is an improvement the human could execute in 5 minutes in this same session. Unlike 40-day-old pending items, this is fresh and visible.

**Verdict after Round 1:** SURVIVES (barely).

### Round 2
**Challenge:** The timing attack is theoretically interesting but practically low-risk right now. Railway private networking means the agent-service is not reachable from the public internet. A timing attack requires ~10,000+ repeated requests to statistically distinguish timing differences. A private network attacker already has significant access. Is this meaningfully lower priority than Idea 1 (which fires autonomously tonight)?

**Defend:** Railway private networking is a deployment-time choice that can change. The check is worth having. But the objection about priority is valid — Idea 1 fires tonight autonomously and unblocks a 46-day pending item. Idea 2 requires human action and addresses a mitigated risk. On pure priority, Idea 1 wins.

**Verdict after Round 2:** WEAKENED.

### Round 3
**Challenge:** If this recommendation is made as a winner, it adds pending item #16 to the moratorium pile. Idea 1 as winner doesn't add a new pending item — it instead ACTIVATES an existing one. Idea 2 as winner adds debt; Idea 1 pays debt.

**Defend:** No strong defense against this framing. The right path for GH #206 is to flag it as Bonus B in the winner's implementation sketch — the human who edits the SKILL.md in 1 minute could also fix auth.ts in 5 minutes in the same session. Not the winner.

**Verdict after Round 3:** WEAKENED → Bonus B in winner's implementation sketch. Route to issue-to-pr-loop for autonomous fix via ai-ready label.

---

## Idea 3: Add Item B Block to nightly-commit-review SKILL.md

### Round 1
**Challenge:** Item B requires: (1) create scripts/check-widget-sync.sh, (2) modify scripts/hooks/pre-push, (3) fix CLAUDE.md Invariant #4. The LOW-risk autonomous scope says "Bash additions to scripts/hooks/pre-commit" — not pre-push. Is pre-push modification in scope?

**Defend:** The nightly SKILL.md LOW scope covers pre-commit additions explicitly. Pre-push is a different hook. The SKILL.md doesn't explicitly authorize pre-push modifications. If the Item B block instructs pre-push modification and the nightly attempts it, it might succeed or might be treated as MEDIUM (out of explicit scope). This ambiguity is a real risk.

**Verdict after Round 1:** WEAKENED — scope ambiguity on pre-push.

### Round 2
**Challenge:** Idea 1 is strictly better — it activates an already-documented, in-scope autonomous action. Idea 3 requires the human to also write the Item B block content (or copy it from run 50 winning-concept.md), and the subsequent nightly execution has scope ambiguity. More complexity, same human effort required.

**Defend:** Item B is genuinely valuable (43-day gap, CLAUDE.md Critical Rule enforcement). But this objection is about timing and priority vs Idea 1, not about correctness. Item B can be Bonus A in Idea 1's implementation sketch — the human making the 1-line deletion for Item A can also add the Item B block in the same 2-minute edit.

**Verdict after Round 2:** WEAKENED → Bonus A in winner's implementation sketch.

### Round 3
**Challenge:** If Idea 1 fires Item A autonomously tonight, pre-push hook modification remains manual. Idea 3 as winner would still require human to add the block + handle scope ambiguity. Too much for a winner vs atomic Idea 1.

**Defend:** Conceded.

**Verdict after Round 3:** WEAKENED → relegated to Bonus A. Do not choose as primary winner.

---

## Final Verdicts

| Idea | Verdict | Disposition |
|------|---------|-------------|
| Idea 1: Remove stale Item A blocker (SKILL.md:69) | SURVIVES → **WINNER** | Primary recommendation |
| Idea 2: Fix auth.ts timing-safe comparison | WEAKENED | Bonus B in winner sketch |
| Idea 3: Add Item B block to SKILL.md | WEAKENED | Bonus A in winner sketch |
| Idea 4: Merge PR #183 | Not debated (rejected_paths run 51 repeat, no new evidence) | Critical standing action |
| Idea 5: Migration 131 prod verification | Not debated | Bonus C (open GH issue) |
