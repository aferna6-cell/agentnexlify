# Debate Log — Run 15 (2026-05-06-pm)

## Moratorium Check

**Pending at run start:** 4 (runs 4, 7, 8, 14) — exceeds max_pending_approvals threshold of 3.
**Moratorium: RE-TRIGGERED.** Run 14 lifted the moratorium (2026-05-05) but adding run 14's winner brought pending back to 4. This run operates in moratorium mode: priority is reducing the queue, not adding new items.

---

## Top 3 Ideas Ranked by Impact

1. Fix Zapier plan_status auth bypass (new, security, S-effort)
2. Wire check_project_invariants.py into pre-commit (closes run 8, queue relief, S-effort)
3. AI-to-Human Handoff v1 (oldest pending 20+ days, Critical customer gap, moratorium protocol)

---

## Idea A: Fix Zapier plan_status auth bypass (Issue #107)

### Challenge
1. **Path not confirmed.** bug-patterns.md cites `backend/services/zapier_auth.py` — this file does not exist. The bug pattern was written from a nightly review analysis, not a direct file read. "Skeleton — confirm exact path before remediation" is quoted in the bug report itself.
2. **Adoption unknown.** If Zapier integration isn't widely used by tenants, the blast radius of the bypass is small. Fixing it adds developer time without proportional customer impact.
3. **Queue discipline.** Moratorium mode says: reduce the pending queue, don't add new items. A security fix bypasses the approval queue (bug fix category), so this isn't strictly a queue concern — but recommending it as the run winner shifts focus away from queue reduction.
4. **Redundant recommendation.** Issue #107 is already filed and tracked. The nightly review loop handles bug escalation. Does the subconscious need to re-escalate?

### Defend
1. **Security bugs rank above queue discipline.** An auth bypass is never acceptable regardless of adoption level. The `fill-instructions-before-guessing` rule applies: the path needs verification, but the bug exists. The fix pattern is correct.
2. **S-effort.** One Supabase filter clause + one regression test. Does not require structural approval.
3. **Revenue leak.** Cancelled tenants accessing the API = real cost with zero revenue. As Zapier adoption grows this becomes critical.
4. **Not in approval queue.** Security bug fixes bypass the subconscious pending queue. Recommending it doesn't worsen moratorium.

### Verdict: **SURVIVES — but as an escalation in the backlog, not the run winner**
The path needs confirmation before any code change (`fill-instructions-before-guessing.md` rule). The recommendation is: grep the codebase for `_get_api_key_client`, confirm the actual file, then fix. This is an urgent bug fix, not a structural improvement requiring subconscious approval. Escalate via nightly review / GH issue #107, not as run winner.

---

## Idea B: Wire check_project_invariants.py into pre-commit (run 8 close)

### Challenge
1. **Already proposed.** This was run 14's bonus step yesterday. Re-recommending something from yesterday implies the system is stuck.
2. **Will recommending help?** If the human didn't do it as a bonus step alongside the main winner, why would making it the primary winner change behavior?
3. **S-effort = should already be done.** If it's 5 minutes, the human could have done it immediately after run 14. The fact that it's not done suggests something else is blocking it (context, workflow, awareness).
4. **Doesn't improve moratorium much.** Closing run 8 drops pending from 4→3 — exactly at the threshold. One more item added = moratorium again.

### Defend
1. **Bonus steps are second-class.** Run 14 led with the eval harness CI winner; the bonus step was buried. Making it the primary winner puts it front and center.
2. **Zero implementation risk.** check_project_invariants.py PASSES all 6 checks. No false positives. No sprint risk. Adding this to pre-commit is a clean, proven operation.
3. **Queue discipline.** Closing run 8 reduces pending 4→3. This is the moratorium protocol: reduce the queue, don't add items. Every S-effort queue closer is the right moratorium move.
4. **The #1 production bug class.** client_id, status, areas_of_interest naming errors caused 3+ production bugs. This guard is the permanent fix.
5. **Concrete spec:** 10-line bash block, fully specified in run 14's winning-concept.md. Implementation time: 5 minutes.

### Verdict: **SURVIVES — strong candidate for winner**
Moratorium mode mandates queue-closing recommendations. This is the S-effort queue closer. Evidence is solid. Implementation risk is zero. The only weakness is "already proposed yesterday" — but that weakness disappears if we accept that bonus steps need their own spotlight.

---

## Idea C: AI-to-Human Handoff v1 (run 4, 20+ days pending)

### Challenge
1. **No new evidence.** Run 4 was recommended on 2026-04-16 with the same evidence: Critical cross-industry, infrastructure exists. Nothing has changed in 20 days to strengthen or weaken the case. Recommending without new evidence violates the brief's "evidence first" principle.
2. **Structural reluctance.** 20 days without implementation suggests this is not being actively prioritized. Repeating the recommendation won't change the priority decision.
3. **Moratorium just lifted.** Run 14 lifted the moratorium yesterday. Re-triggering it for an M-effort item immediately after lifting creates an unhelpful cycle.
4. **M-effort in low-activity period.** 7 commits in 3 days = light activity. An M-effort feature (1.5-2 days) requires a dedicated implementation session that hasn't materialized in 20 days.
5. **Weakened vs. queue-closers.** The moratorium protocol should prioritize queue-closing S-effort items (runs 7, 8) before M-effort feature work.

### Defend
1. **Governance mandate.** max_pending_age_days = 14. Run 4 is at 20+ days. The governance config exists precisely to escalate stale pending items.
2. **Critical customer gap.** customer-gaps.md rates it Critical, cross-industry. 7 industries affected. This is revenue-generating work, not debt cleanup.
3. **Infrastructure is ready.** Conversations table, webhooks, Twilio, Resend — all in place. The blocker is implementation time, not dependencies.

### Verdict: **WEAKENED — add as moratorium warning in backlog**
Valid escalation concern but M-effort + no new evidence + moratorium just lifted 1 day ago = wrong choice for run winner. Moratorium flag: if run 4 reaches 30 days unimplemented, trigger a full moratorium session dedicated to this item. Note in backlog prominently.

---

## Synthesis

**Survivors:** Idea B (Wire check_project_invariants.py) — STRONG SURVIVES
**Escalated separately:** Idea A (Zapier auth bypass) — path confirmation needed, urgent bug fix
**Weakened:** Idea C (AI handoff) — moratorium warning, not winner

**Winner: Wire check_project_invariants.py into pre-commit (run 8 close)**

Rationale:
- Moratorium re-triggered (4 pending > 3). Moratorium mode = close queue, don't add items.
- Run 8 close reduces pending 4→3 (exactly at threshold — healthy state).
- Zero implementation risk: script passes all 6 checks.
- S-effort: 10-line bash block, fully specified in run 14's winning-concept.md (bonus step section).
- Closes oldest code_health pending item (11 days).
- Guards #1 production bug class permanently.

**Confidence: HIGH**
Evidence: (1) check_project_invariants.py confirmed PASS all 6 checks; (2) moratorium governance requires queue closure; (3) full implementation spec available from run 14 bonus step; (4) no blocking dependencies; (5) pre-commit Check 9 is last current check — slot is clean.
