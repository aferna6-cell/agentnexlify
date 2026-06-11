# Debate Log — 2026-06-11-pm

Top 3 ideas ranked by impact. Each challenged then defended.

---

## Idea 1: Fix check_project_invariants.py false positive + em-dash AUTONOMOUS batch

### Challenge
**Is the evidence strong enough?**
The false positive is real — `check_project_invariants.py:209` does `if "from __future__ import annotations" in text:` (full-file text search), and `channels_instagram.py:19` contains the warning text in a docstring. Confirmed by direct grep. Strong evidence.

**Is this the highest-leverage thing?**
Item A (Check 10) has been pending since run 22 (50+ days). Every attempt has been blocked by a different sub-issue: em-dash violations (runs 44-54), Python script not in autonomous scope (runs 44-45), false positive (today). This is the LAST known barrier. Once this is fixed AND nightly processes em-dashes, the self-healing loop activates: violations blocked at commit time going forward.

**What could go wrong?**
- Python script edits require human — nightly autonomous scope cannot modify `.py` scripts (confirmed run 44). Human must do this.
- Nightly handles the 10 JSX em-dashes (proven pattern: run 49 did 5 violations). But nightly ran the run 50/54 em-dash fix for only some files — the 10 new violations from PRs #228/232 are fresh. Same mechanism should work.
- If nightly fails the JSX batch, Check 10 is still blocked by em-dash failures. But the false positive fix is still a net improvement (eliminates a new class of blocker).

**Has something similar been tried?**
Run 44 attempted to scope `check_project_invariants.py` em-dash check to skip .jsx/.tsx (different fix). That was superseded when nightly confirmed Python edits outside scope. Today's fix is different: it targets the `__future__` check (not the em-dash check), AND the em-dash violations are handled by autonomous JSX substitution (not Python script editing).

**Too similar to active direction?**
Run 54 winner was "Fix 3 JSX em-dash violations (MemoryPanel.jsx:180, AgentOS.jsx:197/224)." Those 3 violations from run 54 are now resolved (c8a0460 pre-dates run 54 recommendation? — actually c8a0460 INTRODUCED them, and run 54 recommended fixing them as AUTONOMOUS-EXECUTABLE). New violations from PR #228/232 are a different batch. The false positive is genuinely new.

### Defend
The check_project_invariants.py bug is a NEW class of blocker not present in any prior run. The em-dash violations grew from 3 (run 54) to 10 — same mechanism, bigger batch, proven nightly pattern handles it. The 1-line Python fix is S-effort (2 min, no testing needed — the fix is trivially correct: `startswith` instead of `in text`). The compound effect: false positive fixed → em-dash violations fixed by nightly → Check 10 wires automatically → future violations caught before commit. 50-day blockage ends.

### Verdict: **SURVIVES → WINNER**

---

## Idea 2: Widget sync guard — acknowledge autonomous failure + human-execute

### Challenge
**Is the evidence strong enough?**
Run 50 claimed AUTONOMOUS-EXECUTABLE for check-widget-sync.sh + pre-push wire. Six days later: script still MISSING. Nightly failed to create it. Evidence of autonomous channel failure is strong.

**Highest-leverage thing?**
Widget copies are currently in sync ("PASS widget assets are byte-identical"). No active harm from missing script. Creating the script now is preventive, not reactive. The widget sync guard was the run 7 winner (43 days ago) — it's stale but low urgency.

**What could go wrong?**
Human executes the script creation, but widget copies are already in sync, so the script passes trivially on first run. Future drift prevention is the value. But this is a 10-minute action with no urgent evidence it's needed today.

**Has this been recommended before?**
Runs 7, 15, 16, 17, 18 (switched), 50 — yes, many times. Each time autonomous channel was supposed to handle it and failed.

**Too similar to active direction?**
Run 50 already covers this (pending_autonomous). Recommending it again without new urgency would be a 7th consecutive recommendation on the same item.

### Defend
The autonomous channel failure is new evidence that this item needs human execution. Widget sync is currently fine (PASS), but the pattern of "autonomous says it'll do it, it doesn't" has repeated. Recommending human-execute over autonomous is a mechanism change.

### Verdict: **WEAKENED → Parking Lot / Bonus Action**
Low urgency (widget PASS). Include as Bonus Action B. Reserve winner slot for higher-leverage item.

---

## Idea 3: Fix GH #181 AMOUNT_TO_PLAN — condition (b) evaluation

### Challenge
**Is the evidence strong enough?**
GH #181 is in `rejected_paths` after 5-consecutive-run threshold. Condition (b) for re-proposal: "new evidence about why it keeps being skipped." PR #228 confirmed billing.py path (already known since run 47). The major refactor touched billing.py heavily — but the bug persists through it, which actually suggests the fix is deliberately being deferred, not accidentally missed. 56 days open.

**Is this highest-leverage?**
Yes — billing constants are load-bearing for revenue attribution. Every Stripe webhook that matches a 15000 or 25000 charge falls back to "no plan found."

**What could go wrong?**
`rejected_paths` governance rule exists precisely because 5 consecutive recommendations didn't result in action. The mechanism is broken: human simply hasn't found 15 minutes for this. Recommending it a 6th time as winner violates governance.

**Has something similar been tried?**
Yes — runs 31, 32, 34 (mandate), 35 (governance pivot), 51 (PR #183 framing). 5 primary winner recommendations + 2 more as critical_standing_action. The PR #183 mechanism (review existing draft PR instead of writing new code) was run 51's innovation — PR #183 has been draft for 18+ days now.

**New evidence?**
PR #228 did a major billing.py refactor. But it didn't fix the bug. Run #226 "2nd billing bug fix" — unclear what was fixed. These are weak signals, not the "new evidence about why it keeps being skipped" that condition (b) requires. Condition (b) means: evidence about the MECHANISM of avoidance (why human keeps skipping), not just new context around the issue.

### Defend
PR #228 cleaned billing.py significantly. If the test backwards assertions were also fixed in PR #226, the fix now requires only adding 2 lines to billing.py — trivially simple. But verifying this requires reading the test file, which adds steps to the recommendation.

### Verdict: **KILLED — rejected_paths rule holds**
No new mechanism evidence. Condition (b) not met. Remains critical_standing_action. Do not propose as winner until human implements or explicitly provides rejection reason.

---

## Summary

| Idea | Verdict | Disposition |
|------|---------|-------------|
| 1. Fix check_project_invariants.py false positive + em-dash batch | SURVIVES | **WINNER** |
| 2. Widget sync guard autonomous failure → human execute | WEAKENED | Bonus Action B |
| 3. Fix GH #181 AMOUNT_TO_PLAN | KILLED | rejected_paths holds |
| 4. Cross-tenant isolation test (not debated) | — | Parking lot |
| 5. Fix kb-autopopulate.sh (not debated) | — | Parking lot |
