# Debate Log — Run 70 (2026-06-27-pm)

**Context:** Widget drift RETIRED per run_70_mandate. 6th consecutive failure (runs 65-70). Topic permanently retired. First free-choice winner in 6 runs.

**Top 3 for debate:** Idea 01 (AI-to-Human Handoff v1), Idea 02 (Zapier security fix), Idea 03 (Plan-name guard)

**Eliminated before debate:**
- Idea 04 (Email sequences split): M-effort, moratorium-blocked, no new forcing function. Parking lot.
- Idea 05 (SMS Compliance Dashboard): S-M effort, nice-to-have visibility. Bonus B, not winner material vs 72-day gap.

---

## Round 1: Challenge — AI-to-Human Handoff v1 (Idea 01)

**Challenger:** This is the 8th time this idea has been recommended (runs 4, 21, 29, 38, 42 as sprint planning, 65 bonus, 68 bonus, now 70 winner). Seven prior recs without implementation. Why will run 70 be different?

**Defense:** Different mechanism. Prior recs (runs 29/42) were GH issues + sprint planning. Runs 65/68 were bonus actions (not winner, less urgency). Run 70 promotes it to THE winner for the first time with a clear forcing function: widget drift is retired (no competitor blocking the winner slot), os_outbound_mirror.py exists (delivery layer ready), and run 4 is now 72 days old — governance demands action on oldest pending.

**Challenger:** Moratorium still active (true_pending ~6 > max_pending_approvals:2). M-effort. How is this not moratorium-blocked like email_sequences?

**Defense:** AI-to-Human Handoff v1 is the REASON to exit moratorium, not a blocker to wait on. The moratorium exit path (from governance.json `implementation_lag_warning.note`): widget drift fix → plan-name guard (nightly) → AI-to-Human Handoff → email split → cleanup sprint → moratorium exits. AI-to-Human Handoff is item 3 in the exit sequence. Recommending it now plants the flag for the human's next sprint choice.

**Verdict Round 1:** SURVIVES. Forcing function is real (72 days, infrastructure ready). Moratorium doesn't bar recommendations — it bars implementation until pending count drops. Recommendation is correct; human chooses timing.

---

## Round 2: Challenge — Zapier Security Fix (Idea 02)

**Challenger:** GH #107 is 57+ days open, HIGH security, S-effort. Why does a 1-day AI-to-Human feature beat an S-effort security fix?

**Defense (Idea 02):** S-effort, AUTONOMOUS-EXECUTABLE, pre-existing GH issue with security label. Legitimate claim.

**Defense (Idea 01):** The parking_lot note explicitly says "Route via issue-to-pr-loop, NOT subconscious winner queue." Zapier fix is already tracked and tagged for issue-to-pr-loop. It doesn't need the subconscious winner slot — it has a dedicated delivery mechanism. AI-to-Human Handoff has no such alternative queue.

**Challenger:** Issue-to-pr-loop hasn't touched GH #107 in 57+ days. Why trust it now?

**Defense:** Issue-to-pr-loop handles new commits that trigger the loop; GH #107 may not have had a recent trigger event. But this is the issue-to-pr-loop's failure to fix, not the subconscious's job to circumvent by taking over the winner slot. The parking_lot routing decision was made at run 16 with explicit reasoning — don't override it now.

**Verdict Round 2:** Idea 02 WEAKENED. Route to issue-to-pr-loop. Not a subconscious winner. Parking lot routing stands.

---

## Round 3: Challenge — Plan-Name Guard (Idea 03)

**Challenger:** XS effort, AUTONOMOUS-EXECUTABLE, Bonus A from 5 consecutive runs. Why not make this the winner? Clean, fast, unblocks future runs.

**Defense:** Two blockers: (1) Sequencing — requires check_project_invariants.py to exit 0 first (widget drift must be fixed by human before this can run). Widget drift fix is human-only and is now retired to `docs/reminders/widget-drift-URGENT.md`. (2) Value — XS invariant guard vs 72-day Critical customer gap. Impact ordering is clear.

**Challenger:** The widget drift fix is now a human manual action (30-second cp). Once human executes it, plan-name guard can run autonomously that same night. Maybe this should be the winner with plan-name guard as Bonus A?

**Defense:** Designating plan-name guard as winner implies it's the highest-priority recommendation. It isn't. AI-to-Human Handoff (72-day Critical gap, 7 industries) is the highest priority. Plan-name guard belongs in Bonus A / improvement-backlog. Both can coexist: human fixes widget drift → nightly runs plan-name guard autonomously → human starts AI-to-Human sprint. No conflict.

**Verdict Round 3:** Idea 03 WEAKENED → Bonus A. Correct placement. Not the winner.

---

## Synthesis

| Idea | Rounds won | Verdict |
|------|-----------|---------|
| Idea 01: AI-to-Human Handoff v1 | 2/2 defended | **WINNER** |
| Idea 02: Zapier security fix | 0/1 defended | WEAKENED → issue-to-pr-loop |
| Idea 03: Plan-name guard | 0/1 defended | WEAKENED → Bonus A |
| Idea 04: Email sequences split | Not debated | Parking lot |
| Idea 05: SMS Compliance Dashboard | Not debated | Bonus B |

**Winner: Idea 01 — AI-to-Human Handoff v1**
**Confidence: HIGH**
**Category: customer_value**
**Autonomous: No — human required**
