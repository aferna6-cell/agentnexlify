# Debate Log — Run 13 (2026-05-02)

**Top 3 by impact + urgency:** Idea 1 (JS Silent Catch), Idea 2 (N+1 query fix), Idea 3 (em-dash scope + invariants wiring).

Moratorium filter applied before debate: Idea 4 (golden eval harness) and Idea 5 (reasoning-trace scanner) set aside — moratorium forbids adding new items while pending ≥ 4.

---

## Idea 1: JS Silent Catch Check 10 + AdminAnalyticsPage Fix

### Challenge
- This has been recommended 10 times. If the human hasn't implemented it in 21 days, what does run 13 change?
- AdminAnalyticsPage violations are in Issue #109 — the nightly review system has already flagged them. Is this subconscious territory or is it duplication?
- The `console.warn` fix is trivial (copy-paste from established pattern). Is there actually any blocker stopping the human from doing this today?
- Is recommending the oldest winner again just noise at this point?

### Defend
- Moratorium protocol exists precisely for this: the system must signal that the backlog is too deep, repeatedly, until something gets implemented. Stopping recommendations doesn't help — it removes pressure.
- AdminAnalyticsPage is in Issue #109 but the PRE-COMMIT GUARD (Check 10) has no open GH issue. The guard is what the subconscious owns — the individual fix is secondary evidence that the guard is needed.
- There are zero blockers: em-dash blocker is on run 8 (separate item), not run 3. The Check 10 slot is confirmed open. The implementation sketch was written in run 12 with correct check numbering.
- Onboarding V2 sprint (21 issues, starting now) makes timing perfect: the guard needs to exist before the first JSX commit from this sprint, or new violations will land.
- Moratorium lifts if this is implemented: 4 pending → 3 pending. That unlocks golden eval harness (ROI 2.5), which is the highest-value item in the parking lot.

### Verdict: **SURVIVES — CHOSEN**

---

## Idea 2: email_sequences N+1 Query Fix (Issue #112)

### Challenge
- Issue #112 is already in GH, opened by the nightly review system. Subconscious redundancy: recommending something already formally tracked adds no value.
- The N+1 is in a brand-new router (shipped yesterday). It hasn't caused a support ticket yet. Is it urgent enough to override moratorium priority?
- The moratorium rule is clear: no new items in active_directions until pending ≤ 3. email_sequences N+1 is a new item — proposing it violates the moratorium.
- The fix scope (bulk queries, aggregation) is M-effort and involves a non-trivial DB query pattern. Adding to backlog while 4 items sit unimplemented makes the pile worse.

### Defend
- The N+1 is HIGH severity. 1001 queries for 1000 enrollments will hit Supabase's per-request limits at non-trivial tenant scale. This is the kind of issue that becomes a production incident 30 days from now.
- Nightly review tracks it but doesn't have the governance weight that subconscious active_directions provides. Promoting it signals urgency beyond "nice to fix."

### Counter
- The moratorium governance explicitly prohibits this. `max_pending_approvals: 3` and current count is 4. Adding a 5th item would be a governance violation. The nightly review system + GH issue #112 is the correct handling — subconscious doesn't need to duplicate it.
- Urgency argument doesn't override the moratorium. The moratorium was triggered specifically because urgency arguments kept adding items to the pile without clearing the old ones.

### Verdict: **KILLED — moratorium violation; already tracked in GH #112**

---

## Idea 3: Scope em-dash Check + Wire check_project_invariants.py

### Challenge
- This is a two-step operation (prerequisite + wiring), making it M-effort when this project targets S-effort wins in moratorium mode.
- The em-dash fix was flagged in runs 10, 11, 12 as a "prerequisite for run 8." It still hasn't been done. Same implementation-lag pattern as JS silent catch. Adding it to the pile makes the pile deeper.
- Run 8 winner (Wire invariants.py) is already in active_directions as pending. This idea is the prerequisite to that — recommending the prerequisite while the primary is unimplemented just reorders the same stuck work.
- Moratorium: adding this to active_directions would be 5 pending, not reduction to 3.

### Defend
- The em-dash scope fix is literally one line of Python. Calling it M-effort is generous. The wiring step is also small. Combined, this is closer to S-effort for a motivated developer.
- Fixing this unblocks run 8, which then brings the queue from 4 → 3 → moratorium lifts. Strategic unblock, not just another item.

### Counter
- Even if the em-dash fix is one line, the combination "em-dash fix + wire script + verify" is three distinct actions. That's not atomic.
- More importantly: run 8 is already in active_directions. The prerequisite to an existing item isn't a new subconscious recommendation — it's a blocker note on the existing item. Adding it as a separate recommendation violates the "atomic, one clear action" principle.
- The moratorium protocol already covers this: it says to repeat the oldest pending winner. The oldest is JS Silent Catch (run 3). Run 8 (Wire invariants.py) is newer. Even within moratorium mode, priority order is clear: run 3 before run 7 before run 8.

### Verdict: **WEAKENED — moratorium override; prerequisite belongs in run 8 item notes, not a standalone recommendation**

---

## Synthesis

| Idea | Verdict | Notes |
|------|---------|-------|
| JS Silent Catch Check 10 | SURVIVES → **CHOSEN** | Moratorium mandate, zero blockers, Onboarding V2 timing |
| email_sequences N+1 fix | KILLED | Moratorium violation; already in GH #112 |
| em-dash scope + wire invariants | WEAKENED | Moratorium override; belongs as blocker note on run 8 item |
| Golden eval harness CI | Filtered pre-debate | Moratorium violation; promote to run 14 winner |
| Reasoning-trace scanner | Filtered pre-debate | Moratorium violation; promote to run 15 candidate |

**Winner: Idea 1 — JS Silent Catch Check 10 + AdminAnalyticsPage.jsx fix.**

Same winner as run 12. Moratorium continues to signal: implement before expanding.
