# Debate Log — Run 2026-06-11-pm (Run 56)

Top 3 ideas ranked by impact: Idea 1 (em-dash fix), Idea 2 (os_graph isolation tests), Idea 4 (AI-to-Human Handoff).

---

## Idea 1: Fix 10 em-dash violations (AUTONOMOUS-EXECUTABLE)

### Round 1
**Challenge:** Run 55 recommended the exact same fix this morning. Two subconscious runs in one day generating identical recommendations adds no compounding intelligence. If the fix is 10 one-char substitutions, why hasn't it been done?
**Defend:** New evidence since run 55: Sidebar.jsx:386 is a NEW violation not in run 55's list — introduced by one of the 4 PRs that landed after the morning run. This is a third category of evidence (first: static violations, second: from __future__ fixed, third: violations accumulating in real-time during the sprint). The fix being "easy" doesn't mean it's been done — the AUTONOMOUS-EXECUTABLE path is the mechanism that will do it, and the path is confirmed active. The human is present; the recommendation is the approval gate.

### Round 2
**Challenge:** This is the 3rd consecutive em-dash recommendation (runs 49/55/56). At what point does the moratorium escalation protocol fire on an idea that keeps not getting implemented?
**Defend:** Runs 49 and 55 are NOT the same mechanism as run 56. Run 49 (8db33df) was IMPLEMENTED autonomously by the nightly — it fixed 5 violations successfully. Run 55 fixed the `from __future__` issue. Run 56 addresses the residual 10 violations. The trajectory is convergent: each run reduced the problem class. This is the final step.

### Round 3
**Challenge:** The Sidebar.jsx:386 violation came from fc662b4 ("Hide platform-admin pages from tenant sidebar") — a 4-line cosmetic fix. That's not a high-velocity risk; it's noise. The core violations (main.jsx, CookieConsent, ReferralCard) have been there since run 55. Is the "high-velocity sprint is introducing violations" framing accurate?
**Defend:** The framing is correct because Check 10 is designed PRECISELY to prevent this. fc662b4 introduced a violation as a side effect of a 17-line diff. Without Check 10 in the pre-commit hook, every developer commit — trivial or complex — can introduce violations undetected. The accumulation pattern over 55 days IS the high-velocity risk. Fixing the 10 violations NOW triggers Check 10 tonight, and Check 10 PREVENTS future accumulation.

**Verdict: SURVIVES → WINNER** — highest leverage (unblocks 55-day systemic gate, closes accumulation loop), S-effort, AUTONOMOUS-EXECUTABLE, no moratorium conflict.

---

## Idea 2: Add tenant isolation tests for os_graph_memory.py (AUTONOMOUS-EXECUTABLE)

### Round 1
**Challenge:** There is no confirmed cross-tenant leak today. The 3rd _TENANT_COLUMN_OVERRIDES miss was caught and fixed by c6805a5 before shipping. Why write tests for a hypothetical failure when real failures exist?
**Defend:** The 3rd occurrence of _TENANT_COLUMN_OVERRIDES miss is the evidence. It has happened 3 times — the pattern is reliable. The fact that it was caught each time is a tribute to the code reviewer, not to systematic testing. os_graph_memory.py at 397L with complex graph operations is the hardest surface to manually review for cross-tenant isolation. A test makes the correctness automatic.

### Round 2
**Challenge:** The nightly's AUTONOMOUS-EXECUTABLE scope covers existing patterns (test files for existing services). os_graph_memory.py is a new service with novel architecture — the nightly may write tests that test implementation details, not isolation semantics.
**Defend:** test_os_action_dispatch.py (run 53, c6805a5) is the precedent: 5 mock-based tests for a new Agent OS service, created autonomously by the nightly. The isolation test pattern (client_id=A → no results with client_id=B) is straightforward enough for nightly execution. The implementation sketch is specific: 2 tests, bounded scope.

### Round 3
**Challenge:** The em-dash fix (Idea 1) is lower-effort AND higher-leverage (unblocks 55-day pending item). Idea 2 adds to the implementation queue without clearing any existing blocker. In moratorium mode, adding pending items makes the moratorium harder to exit.
**Defend:** Idea 2 is AUTONOMOUS-EXECUTABLE — it would add to pending_autonomous, not pending_approval. The moratorium threshold counts human-required items. AUTONOMOUS-EXECUTABLE items don't worsen the human-required queue.

**Verdict: SURVIVES WEAKENED → Parking Lot** — valid and AUTONOMOUS-EXECUTABLE, but lower leverage than Idea 1. Defer to next run. ROI: 2.1.

---

## Idea 4: AI-to-Human Handoff v1 implementation

### Round 1
**Challenge:** Moratorium is active. This is M-effort (~1 day). Moratorium protocol requires clearing pending items first. Idea 1 is S-effort and directly clears a pending blocker. Idea 4 adds a new high-complexity item.
**Defend:** bc8d0da (voice recovery, shipped today) establishes the exact dispatch pattern needed for handoff: detect condition → Agent OS action → os_outbound_mirror delivery. The infrastructure difference since run 38 (most recent recommendation) is now production-proven, not theoretical. The scope is bounded.

### Round 2
**Challenge:** Run 38 was MEDIUM confidence because "7 prior mentions without implementation; genuine scope reduction via Agent OS is new evidence." That was 14 days ago. The scope reduction has now been further validated by bc8d0da. But the fundamental bottleneck — M-effort during moratorium — is unchanged.
**Defend:** Correct, the moratorium constraint is the binding one. The improved infrastructure is relevant evidence for post-moratorium prioritization.

### Round 3
**Challenge:** The moratorium's max_pending_approvals is set to 2. Adding an M-effort human-required item increases pressure on the human to implement MORE items before moratorium exits, not fewer. This is anti-moratorium.
**Defend:** No strong defense. The moratorium constraint is correct and binding.

**Verdict: WEAKENED → Parking Lot** — highest customer value, right post-moratorium priority, but moratorium protocol prevents M-effort winner. Promote immediately after Check 10 is wired and moratorium exits.

---

## Not Debated

**Idea 3 (Home.jsx god-class split):** Valid, M-effort, wrong timing. email_sequences.py (run 41, 1255L) has moratorium seniority. Home.jsx goes to parking lot with note: invoke /god-class-splitter AFTER email_sequences.py split.

**Idea 5 (kb-autopopulate.sh):** Operational, low-urgency, parking lot.
