# Debate Log — 2026-06-04 (Run 49)

Top 3 by impact: Idea 1 (atomic em-dash fix), Idea 3 (AI-to-Human Handoff), Idea 4 (email_sequences split).

---

## Idea 1: Fix exactly the 5 JSX em-dash lines (~2 min)

### Round 1 — Challenge

Is 25 minutes really the implementation barrier? We've had 7 interactive sessions in moratorium with the human "present" and nothing got done. Why would a 2-min task behave differently from a 25-min task?

**Defense:** The evidence is in the pattern. Every recommendation that required >15 min went unimplemented. The only items that DID get implemented in this moratorium were:
- Nightly autonomous commits (LOW-risk, zero human activation energy)
- Runs 37 and 43 (Check 11 bash block, SKILL.md extensions — short additive writes)
The commitment curve breaks somewhere between 5 and 25 minutes. Idea 1 targets below that threshold.

### Round 2 — Challenge

Why recommend the em-dash fix alone when CLAUDE.md personality.md already bans em-dashes as a rule? The nightly review could be updated to auto-fix this class of violation. No human needed.

**Defense:** The nightly review's autonomous scope is verified NOT to extend to JSX/TSX file edits — nightly touches only bash scripts, SKILL.md files, and workflow YAML. JSX UI copy edits would require human intent verification (content accuracy matters). Extending nightly scope to UI copy editing is a significant governance change with more risk than the 2-min human fix. The simpler path is the correct one.

### Round 3 — Challenge

Fixing em-dashes without Item B leaves the widget sync guard still missing. Moratorium won't exit from Item A alone.

**Defense:** This is true but irrelevant to whether Idea 1 is the right recommendation. Moratorium exit requires MULTIPLE items resolved; recommending the smallest one first is legitimate sequencing. Item A auto-wires Check 10 via the autonomous chain (4226ef4 + nightly scope extension from run 43). That's a guaranteed win from a 2-min change. Item B follows naturally in the next session or the one after — widget copies are currently in sync (PASS on invariants), so no active harm while we wait.

**Verdict: SURVIVES** — genuinely new recommendation (micro-scope split from A+B), strong evidence that 2-min activation energy is qualitatively different, autonomous chain fires tonight.

---

## Idea 3: AI-to-Human Handoff v1 implementation sprint (~1 day)

### Round 1 — Challenge

This exact recommendation (with os_outbound_mirror.py framing) was run 38's winner on 2026-05-28. Exactly 7 days later, zero implementation. The scope reduction from ~3 days to ~1 day didn't change behavior. What's different now?

**Defense:** The same force that blocked Item A (~25 min) for 25+ consecutive days blocks a 1-day implementation. If we can't get 25 minutes, we can't get 8 hours. The moratorium bottleneck is not information (the spec is written, the code path is clear), it's activation energy and context-switching cost. Recommending an M-effort item during the same moratorium that has blocked S-effort items is contradictory.

### Round 2 — Challenge

But the moratorium itself is proof that the review loop is broken. The system should not keep recommending S-effort items if S-effort items don't get done. Recommending something ambitious might force a different kind of engagement.

**Defense:** This contradicts evidence from runs 21-29: recommending M-effort items (AI-to-Human GH issue, moratorium sprint) during moratorium produced the same zero-implementation result. The moratorium-sprint skill was the only "ambitious" recommendation that worked, and it worked because it was delegated to autonomous nightly execution — not because the human activated it.

### Round 3 — Challenge

Customer-gaps.md rates this Critical for all 7 industries. If revenue is at stake, shouldn't that override moratorium sequencing?

**Defense:** Revenue impact of AI-to-Human Handoff is real but not urgent — no customer is churning TODAY because it's missing. Check 10 (code quality) compounds daily: every commit that violates invariants slips past the guard. The moratorium-exit path (Items A+B) is the prerequisite for any subsequent human-activated work. Fix the foundation; then tackle customer features.

**Verdict: WEAKENED** — valid Critical gap, but same-mechanism recommendation as run 38 with no new evidence. Moratorium still active. Moves to parking lot as first post-moratorium winner candidate.

---

## Idea 4: email_sequences.py god-class split via /god-class-splitter (~2h)

### Round 1 — Challenge

GH #181 billing fix is listed as a "Critical standing action: do before email_sequences split" in the run 41 note. GH #181 still open. Does this block Idea 4?

**Defense:** Re-reading the run 41 note: "Critical standing action: GH #181 billing fix (~15 min, human required) before starting split." The rationale was to avoid having a god-class split PR conflict with a billing hotfix. In practice, email_sequences.py split produces entirely different files (email_crud.py, email_enrollment.py, email_processor.py) — no overlap with billing.py. The prerequisite was risk-management advice, not a hard technical block. However, recommending a 2h task during a moratorium that can't clear 2-minute tasks is indefensible.

### Round 2 — Challenge

god-class-splitter SKILL.md exists, post-split-test-repair SKILL.md exists. Both prerequisites are met for the first time. This is the clearest the path has ever been.

**Defense:** True, but the same moratorium that blocked all S-effort items will block an M-effort item. The right sequence: clear Item A (2 min) → nightly fires Check 10 → build momentum → tackle email split in a subsequent session.

### Round 3 — Challenge

If we never recommend the email split during moratorium, it might sit forever. It's been 10+ days since run 41 (the second time it was winner). When does it become appropriate?

**Defense:** It becomes appropriate when moratorium exits (pending ≤ 2). Currently at 13. The email split would add clean code but doesn't reduce pending count — it would actually ADD an item for the split PR review. Wrong timing.

**Verdict: KILLED** — moratorium active, M-effort, wrong timing, prerequisite question unresolved, would add to pending count not reduce it.

---

## Synthesis

| Idea | Verdict | Reason |
|------|---------|--------|
| Idea 1 — atomic em-dash fix | **SURVIVES → WINNER** | 2-min, new mechanism, autonomous chain fires tonight |
| Idea 2 — Items A+B combined | WEAKENED | Run 48 repeat, superseded by Idea 1 |
| Idea 3 — AI-to-Human Handoff | WEAKENED → parking lot | M-effort, moratorium active, same as run 38 |
| Idea 4 — email_sequences split | KILLED | M-effort, moratorium active, wrong timing |
| Idea 5 — Zapier security fix | WEAKENED → parking lot | Valid, but strictly lower priority than clearing Item A first |

**Winner: Idea 1 — Fix 5 JSX em-dash lines (~2 min)**
