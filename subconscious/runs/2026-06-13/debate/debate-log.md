# Debate Log — 2026-06-13

Top 3 ideas ranked by impact: Idea 1 (widget drift), Idea 2 (Check 13), Idea 3 (em-dash/future fix).

---

## Idea 1: Fix widget sync drift (AUTONOMOUS-EXECUTABLE)

### Round 1: Challenge
**Is the evidence strong enough?**
check_project_invariants.py output is unambiguous: `drift: widget/agentnexlify-widget.js != landing-page-v2/widget/agentnexlify-widget.js`. PR #254 git stat confirms both widget/ and frontend/public/widget/ received 202 lines of changes — landing-page-v2/widget/ has zero lines in the stat. The drift is confirmed, current, and from a same-day commit. Evidence is strong.

### Round 1: Defend
Evidence is concrete and independently verified by two sources (git stat + invariant script). This is not a risk — it is a confirmed live state.

### Round 2: Challenge
**Is this the highest-leverage thing right now?**
landing-page-v2 domains (agentnexlify.com + www) are currently attached to the stale `agentnexlify-site` Vercel project, not `agentnexlify` (per CLAUDE.md 2026-06-12 warning). Widget drift in landing-page-v2 may not be serving actual users today. Is fixing an invariant violation in a non-served copy the highest priority?

### Round 2: Defend
The CLAUDE.md warning says domain routing is wrong — that's a REASON to fix the routing, not a reason to let the widget drift persist. When the domains are corrected, the landing-page-v2 instantly starts serving users. A stale widget in a not-yet-live-but-imminently-live path is HIGH risk. Also: check_project_invariants.py exits 1, which blocks Check 10 wiring. Fixing widget drift directly reduces the failure count from 3 to 2 (and when combined with em-dash fix, achieves exits 0 → Check 10 auto-wires). The leverage is real.

### Round 3: Challenge
**Previous runs (7, 15, 50) all had widget-related recommendations that went unimplemented. What makes this different?**
Run 7 (April 24) proposed creating check-widget-sync.sh. Run 15 re-escalated. Run 50 (June 5) proposed extending nightly scope. None fully executed. History suggests widget work is low-implementation-probability.

### Round 3: Defend
Critical distinction: prior recommendations were about creating a GUARD (check-widget-sync.sh) — a new script, SKILL.md changes, pre-push hook wiring. This recommendation is a single FILE COPY — one `cp` command, ~50 tokens of bash. The implementation complexity is 10-20x lower than prior widget recommendations. The nightly review executes file copies autonomously (precedent: 8db33df fixed 5 JSX em-dash replacements via nightly). This is the same class of action.

**Verdict: SURVIVES → WINNER**

---

## Idea 2: Add Check 13 to pre-commit (run 56 winner)

### Round 1: Challenge
**Is Check 13 redundant with pre-commit CHECK 2?**
Pre-commit already has CHECK 2 (lines 49-65) that scans staged files matching `*routers*.py || *router*.py` for `from __future__ import annotations`. CHECK 2 would catch any STAGED router file with this import. Check 13's proposed scope is `backend/**/*.py` (broader, catches services). But are there known service violations? Grep of activation_nudges.py only shows a COMMENT warning against the import, not an actual import.

### Round 1: Defend
CHECK 2 has a path matching flaw: `*routers*.py` would catch `backend/routers/foo.py` but what about files like `backend/services/my_router_helper.py`? Conversely it could produce false positives on test files that happen to contain "router" in the name. More importantly: CHECK 2 is scoped to `*router*` naming convention, which is a convention not a contract. Check 13 scopes to `backend/**/*.py` which is structurally sound. The coverage gap is real for service files.

### Round 2: Challenge
**Run 56 was specifically marked AUTONOMOUS-EXECUTABLE and pending_autonomous. Why hasn't nightly implemented it in 1+ days?**
Nightly d12bd21 (2026-06-12) ran and produced only a log commit with no code changes. The mechanism appears unreliable for pre-commit bash insertions (though runs 37/52 both succeeded for similar tasks).

### Round 2: Defend
d12bd21 ran after run 56 was committed. The timing is uncertain. Run 57 could re-confirm the autonomous path with updated language or a stronger inline patch in governance.json.

### Round 3: Challenge  
**Is this the best use of the winner slot given widget drift is more urgent?**
Widget drift is a CONFIRMED live bug. Check 13 is a PREVENTIVE guard for a class of bugs that pre-commit CHECK 2 already partially covers. Widget drift is higher urgency than a partially-redundant guard.

**Verdict: WEAKENED → Parking Lot (run 56 already active_direction pending_autonomous; not needed as winner)**

---

## Idea 3: Fix em-dash + from __future__ actual imports (run 55 expansion)

### Round 1: Challenge
**Run 55 is already pending_autonomous. Recommending it again as run 57 winner just duplicates the pending queue.**
Run 55 covers channels_instagram.py from __future__ + em-dash violations. That item exists in governance.json as pending_autonomous. Recommending the same action creates TWO pending items for the same fix class.

### Round 1: Defend
Run 55 targeted a specific set of em-dash locations. PR #254 added 3+ new violations (DemoBanner.jsx:4/7, Sidebar.jsx:386) that were not in run 55's implementation sketch. Run 57 could frame as an EXPANDED run 55 with an updated target list.

### Round 2: Challenge
**Even with the expanded list, this doesn't fix widget drift. check_project_invariants.py still exits 1 after em-dash fix unless widget is also fixed. What's the unlock?**
check_project_invariants has 3 failures. Em-dash fix addresses 1 of 3. Widget fix addresses 1 of 3. from __future__ fix addresses 1 of 3. No single action gets to exits 0 — it requires combination. Check 10 cannot auto-wire until ALL 3 are fixed. Recommending only 1/3 of the fix is less effective than recommending the most atomic piece.

### Round 2: Defend
Widget fix (Idea 1) + em-dash fix (run 55) together would clear 2/3 failures. With from __future__ fix they clear 3/3. The correct sequencing is: (1) widget fix tonight, (2) em-dash + future fix in same or next nightly = exits 0.

### Round 3: Challenge
**If widget fix is the winner and run 55 stays pending_autonomous, isn't this already the plan?**
Yes. Winner = widget fix. Run 55 = em-dash+future (already in autonomous queue). Together they clear check_project_invariants. Running Idea 3 as winner adds no incremental value beyond what's already queued.

**Verdict: KILLED as winner (run 55 already covers; widget fix is the right new recommendation)**
