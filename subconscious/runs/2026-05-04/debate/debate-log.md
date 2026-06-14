# Debate Log — 2026-05-04 (Run 13)

**Top 3 by impact:** Idea 1 (JS Silent Catch Guard), Idea 2 (email N+1), Idea 3 (em-dash unblock).
**Moratorium status:** ACTIVE — 4 pending approvals; lift condition = ≤3 pending.

---

## Idea 1: JS Silent Catch Guard — Check 10 + AdminAnalyticsPage.jsx

### Challenge Round
**Is the evidence strong enough?**
AdminAnalyticsPage.jsx:117-122 confirms 6 `.catch(() => null)` on live check 2026-05-04 — yes. Pre-commit grep for Check 10 returns empty — yes. No new blockers since run 12.

**Is this the highest-leverage thing right now?**
Challenge: This has been recommended 10 times. If it hasn't been implemented after 10 runs, does that indicate friction that evidence alone can't fix? Maybe the right intervention is removing friction, not repeating the recommendation.

**What could go wrong?**
The regex for `.catch(() => null)` / `.catch(() => {})` might match comments or strings. The `grep -v "ok-silent-catch"` escape hatch handles intentional use. False positive rate is very low (pattern is syntactically specific).

**Has something similar been tried and rejected?**
No — runs 3–12 all recommended this. Never rejected. Awaiting implementation, not debate outcome.

**Too similar to current active direction?**
This IS the current active direction. Moratorium mandates it continues.

### Defense Round
- Evidence: direct file inspection confirms violations still live (2026-05-04)
- Friction: implementation sketch is copy-paste ready from run 12's winning-concept.md. S-effort. 2 files. 30-minute task.
- Moratorium protocol: governance.json moratorium_active=true explicitly mandates recommending oldest pending until implemented. This IS the oldest pending.
- New Onboarding V2 sprint started — new JSX files incoming. Guard needed before first V2 commit.
- No blockers identified in any prior run. Numbering error (Check 9 vs Check 10) was corrected in run 12.

### Verdict: **SURVIVES** — moratorium mandate + confirmed violations + zero implementation blockers + sprint timing urgency

---

## Idea 2: Fix email_sequences.py N+1 Queries (Issue #112)

### Challenge Round
**Is the evidence strong enough?**
GH #112 opened 2026-05-02 — yes. 1001 queries per 1000 enrollments is mathematically certain. But: how many tenants currently have 1000+ enrollments? Email automation shipped 2026-05-01 — essentially day 4. No production traffic data.

**Highest-leverage right now?**
Challenge: Moratorium is active (4 pending). Governance protocol says NEW recommendations are blocked when pending > 3. A new winner here would push pending to 5. The moratorium_config's purpose is preventing recommendation backlog — recommending this violates that purpose.

**What could go wrong?**
Bulk .in_() query changes the ORM interaction pattern. Supabase Python client's `.in_()` behavior differs from standard SQLAlchemy — verify that syntax matches. Behavioral change risk is low (same data, different query count) but test coverage needed.

**Similar tried and rejected?**
No — first time this pattern appeared. But moratorium blocks it regardless.

### Defense Round
- This is genuinely high-leverage. 1001 queries for 1000 enrollments is a classic production timebomb.
- Fix is well-understood (bulk .in_() is standard).
- BUT: moratorium governance explicitly blocks new recommendations until pending count drops. 

### Counter-challenge (moratorium override test)
Would this idea clear the moratorium override bar? Governance note says moratorium fires when "5 winners unimplemented; oldest 19+ days." Current state is 4 pending. Override would need to argue that N+1 is an emergency that supersedes moratorium. It is not — no production tenants with 1000+ enrollments yet. Day 4 of feature.

### Verdict: **WEAKENED** — valid diagnosis, correct fix, wrong timing. Add to parking lot. Promote to winner when moratorium lifts + email automation gains adoption.

---

## Idea 3: Scope em-dash Check to Unblock Run 8

### Challenge Round
**Is the evidence strong enough?**
9 violations confirmed by direct script run. One-line fix in check_project_invariants.py. But: this is a prerequisite for run 8, not an independent improvement. Is it atomic?

**Is this highest-leverage?**
Challenge: The em-dash fix enables run 8 (wire check_project_invariants.py). But run 8 is "pending approval" — human hasn't approved it yet. Implementing a prerequisite for an unapproved item is premature. Also: moratorium means both run 8 AND this prerequisite compete with the 4 already-pending items.

**What could go wrong?**
The em-dash check's original intent was to catch em-dashes in Python strings and docstrings. Scoping it to skip .jsx/.tsx is correct — JSX UI renders em-dash as a valid display character. Risk: someone adds a real em-dash issue in a .jsx file that the scoped check would miss. Mitigated by: em-dash violations in JSX are almost never naming violations (they're UI display chars), so the skip is semantically correct.

**Similar tried and rejected?**
No history on this specific idea. Proposed as blocking fix in runs 10-12, never debated independently.

### Defense Round
- One-line change, zero risk, makes check_project_invariants.py accurate rather than noisy.
- Even without run 8 implementation, a more accurate invariants script improves agent workflow (agents run it manually for diagnosis).
- But: recommending this as the winner feels like recommending a prerequisite over the actual goal.
- Better path: bundle this fix into the SAME implementation task as run 8. The human approving run 8 should also approve the em-dash scope fix as step 0.

### Verdict: **WEAKENED** — correct diagnosis, right fix, but better framed as prerequisite step to run 8 than as an independent winner. Flag in winning-concept.md as "implement this to unblock run 8."

---

## Ideas 4 & 5: Wire Eval Harness to CI / Extract _process_pending_sends

### Rapid Verdict
**Idea 4 (Wire eval harness):** Parking lot note explicitly says "promote when moratorium lifts." Moratorium still active. **KILLED** — not because the idea is weak (ROI 2.5 is highest in backlog), but because governance requires moratorium lift first.

**Idea 5 (Extract _process_pending_sends):** Opened 2026-05-02, moratorium active, M-effort. No urgency signal. **KILLED** — park for post-moratorium run.

---

## Debate Summary

| Idea | Verdict | Notes |
|------|---------|-------|
| JS Silent Catch Guard (Check 10 + AdminAnalyticsPage) | **SURVIVES → CHOSEN** | 10x mandate, confirmed violations, S-effort, sprint timing |
| Email N+1 (Issue #112) | **WEAKENED → Parking Lot** | Real bug, wrong timing (day 4 of feature, moratorium) |
| Em-dash scope fix (unblock run 8) | **WEAKENED → Parking Lot** | Right fix, frame as run 8 prerequisite step |
| Wire eval harness CI | **KILLED** | Moratorium gate; promote run 13 |
| Extract _process_pending_sends | **KILLED** | Moratorium + M-effort + no urgency |

**Winner: Idea 1 — JS Silent Catch Guard Check 10 + AdminAnalyticsPage.jsx fix**

Additional note: Em-dash scope fix (Idea 3) is included in the "Side Notes" section of the winning-concept — implementation should include this one-liner to unblock run 8 as a bonus action at no added risk.
