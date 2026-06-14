# Debate Log — 2026-06-14 (Run 58)

## Ranking by Impact
1. Idea 1 — Wire Check 10 (invariant gate, 6 invariants, permanent protection)
2. Idea 2 — Wire Check 13 (from __future__ guard, belt-and-suspenders)
3. Idea 4 — email_sequences god-class split (oldest code-health debt, all prerequisites met)
4. Idea 3 — Governance correction (meta-level, high accuracy value)
5. Idea 5 — WordPress plugin tests (new territory, PHPUnit infra doesn't exist yet)

Top 3 debated: Ideas 1, 2, 4.

---

## Idea 1: Wire check_project_invariants.py into pre-commit as Check 10

### Challenge Round 1
*"Run 22 (wire check_project_invariants to pre-commit) has been pending_autonomous for 51 days.
Nightly review scope was extended in run 43 (4226ef4) to cover pre-commit bash additions.
If the nightly can execute this, why is it still missing after 51 days?"*

### Defense Round 1
The only reason nightly never executed it: check_project_invariants.py was exiting nonzero
(invariant violations present). The SKILL.md makes nightly skip pending_autonomous items that
would produce false positives. Now exits 0 for the first time (confirmed 2026-06-14 live run).
The blocking condition is lifted. Recommending it explicitly creates the written rationale and
governance alignment that triggers nightly's execution path tonight.

### Challenge Round 2
*"Is this the highest-leverage action right now? check_project_invariants.py is already run by
nightly-commit-review at 2:37 AM. Wiring it to pre-commit adds friction for developers who now
get a second invariant check at every commit."*

### Defense Round 2
Nightly fires AFTER code is committed to the branch and may have propagated. Pre-commit fires
BEFORE code is committed — earliest possible detection, zero propagation. The check takes <1
second (stdlib-only Python). Developer friction is minimal; invariant regressions are caught at
source not post-factum. 3234597 invested 50 commits to clear these violations — failing to lock
the gate means the next god-class split or router addition will reintroduce them immediately.

### Challenge Round 3
*"Could something similar have been tried and rejected? Run 26 rejected authorizing nightly to
execute Items A+B concurrently. Is this the same?"*

### Defense Round 3
Run 26 rejected authorizing nightly to execute Items A and B _concurrently_ due to merge
conflict risk with the sprint PR model. That rejection was about parallel execution, not about
whether Check 10 is valid. Check 10 (Item A) as a standalone item was explicitly affirmed in
runs 22, 42, 43 as valid pending_autonomous. No rejection exists for Item A in isolation.

### VERDICT: SURVIVES → WINNER

---

## Idea 2: Wire Check 13 (from __future__ bash pre-commit guard)

### Challenge Round 1
*"check_project_invariants.py already has an AST-based from __future__ check (line 49 of the
Python script). Idea 1 (Check 10) will wire that script to pre-commit, creating an indirect
guard for from __future__. Isn't Check 13 as a separate bash check redundant?"*

### Defense Round 1
check_project_invariants.py's CHECK 2 uses AST parsing — it actually needs Python to compile
the file. Bash grep is simpler and fires as a separate, explicit fail with a clear message.
The two mechanisms are complementary: Python AST = accurate; bash grep = fast first-pass.

### Challenge Round 2
*"If Idea 1 SURVIVES as winner (Check 10 wires the Python script), Check 13 is already
covered via Check 10. Adding it separately makes two checks both gate on the same invariant.
What's the explicit gain over just letting Check 10 cover it?"*

### Defense Round 2
The Python invariant script runs after all checks. Check 13 as bash guard would fire early
in the pre-commit sequence — developers see "from __future__ found in channels_instagram.py"
before running the full Python script. Better UX. Belt-and-suspenders is justified for
CLAUDE.md Critical Invariant #5 (any violation → all Instagram endpoints 422).

### Challenge Round 3
*"But this is exactly what Idea 1's 'bonus action' recommendation already covers: Check 10
as winner + Check 13 as bonus in same commit. Why debate Idea 2 as a standalone winner when
it's a weaker version of Idea 1?"*

### Defense Round 3
No valid defense. Idea 1 strictly dominates Idea 2 by covering 6 invariants vs 1, while also
subsumes Check 13 as a bonus action.

### VERDICT: WEAKENED → Bonus action under Idea 1 (Check 10 = winner, Check 13 = bonus in same commit)

---

## Idea 4: Invoke /god-class-splitter on email_sequences.py

### Challenge Round 1
*"email_sequences.py has been recommended as winner in runs 35 and 41 without implementation.
57 days stale. Moratorium is still active. max_pending_approvals=2. A HUMAN-REQUIRED
recommendation adds 1 to pending_approval count, making moratorium worse not better."*

### Defense Round 1
GH #181 was the stated prerequisite for runs 35/41. GH #181 is NOW FIXED (3234597). God-class-
splitter SKILL.md exists. Post-split-test-repair SKILL.md exists. All 3 prerequisites met for
first time. This run is the earliest moment this idea has no remaining blockers.

### Challenge Round 2
*"Even if prerequisites are met, the moratorium governance rule applies: max_pending_approvals=2.
Adding a MEDIUM-effort human task to the approval queue worsens the pending count. AUTONOMOUS-
EXECUTABLE ideas are strictly preferred during moratorium."*

### Defense Round 2
The moratorium was designed to prevent unbounded pending growth. email_sequences.py has been
GOD-CLASS for 57+ days and represents real blast-radius risk — each email automation feature
touches all 3 concerns in one file. Not recommending it compounds the risk. The moratorium
was triggered by workflow overhead, not by feature-risk accumulation.

### Challenge Round 3
*"If the governance mega-correction (Idea 3) is applied and true pending drops to ≤ 2, the
moratorium may lift this run, making email_sequences split valid. But we don't know the true
pending count without applying Idea 3 first. Recommending Idea 4 before Idea 3 is premature."*

### Defense Round 3
Cannot argue this. The governance state is genuinely uncertain. Recommending a HUMAN-REQUIRED
item before confirming moratorium status is a sequencing error.

### VERDICT: WEAKENED → Standing action (recommend after governance correction confirms moratorium exit)

---

## Synthesis

| Idea | Verdict | Rationale |
|------|---------|-----------|
| Idea 1 (Check 10 — invariant gate) | **SURVIVES → WINNER** | exits 0 confirmed, AUTONOMOUS-EXECUTABLE, 51-day unblocked |
| Idea 2 (Check 13 — from __future__ bash) | WEAKENED → Bonus A | Subsumed by Idea 1 |
| Idea 3 (Governance correction) | Not debated → Applied in Phase 6 | Operational necessity |
| Idea 4 (email_sequences split) | WEAKENED → Standing action | Moratorium gate applies; pending count uncertain |
| Idea 5 (WordPress plugin tests) | Not debated → Parking lot | PHPUnit infra missing; low urgency |
