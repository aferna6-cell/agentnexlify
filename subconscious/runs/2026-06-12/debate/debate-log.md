# Debate Log — Run 56 (2026-06-12)

Top 3 by impact: Idea 1 (Check 13 guard), Idea 2 (fix 4 files + em-dashes), Idea 3 (cross-tenant isolation tests).

---

## Idea 1: Add pre-commit Check 13 — `from __future__ import annotations` guard

### Round 1 Challenge
Is the evidence strong enough to justify a systemic check vs. a one-time fix? The `from __future__` violations in auth_password_reset.py, auth_billing.py, auth_google.py — are these actually causing 422 errors, or is the risk theoretical?

### Round 1 Defense
Not theoretical. CLAUDE.md Critical Invariant #5: "No `from __future__ import annotations` in FastAPI files — PEP 563 deferred annotations make Pydantic resolve bodies as strings → every request 422s." The auth split introduced 3 new router files that serve real endpoints (password reset, billing webhooks, Google OAuth). All requests to those endpoints are currently producing 422s if any Pydantic model is used in the request body. channels_instagram.py was identified in run 55 as causing Instagram endpoint 422s. Same class, 3 more files. Evidence: direct invariants check output shows all 4 files.

### Round 2 Challenge
Is a pre-commit guard the highest-leverage action vs. just fixing the current violations? Run 55 winner targets the same problem and is already pending_autonomous. Why add a guard before fixing what's broken?

### Round 2 Defense
Sequence matters: Fix without guard → next split re-introduces violation (PR #238 is proof: PR #235 + #237 created god-class splits, PR #238 auth.py split immediately introduced 3 more violations in the same deploy cycle). Guard without fix → violations persist but no new ones are added. Guard + fix → self-healing. The guard is the systemic lever; fixing current violations is the immediate lever. Both are needed, but the guard prevents the class from recurring infinitely. 

The god-class-splitter has 14+ targets remaining (god-class-refactor_plan.md). Every split WILL produce new router files. Without Check 13, each split risks introducing `from __future__`. With Check 13, the commit is blocked at source.

### Round 3 Challenge
Will nightly actually implement this? The autonomous channel broke in runs 36-38 (SKILL.md didn't execute). Run 55 winner (pending_autonomous) was not implemented by d12bd21 tonight despite the AUTONOMOUS-EXECUTABLE label. What makes Check 13 different?

### Round 3 Defense
Check 11 (billing-constant-guard bash, 22 lines, autonomous-implemented by nightly 061582c) and Check 12 (timing-safe guard bash, 20 lines, autonomous-implemented by nightly ca3ce68) are the exact precedents. Both are bash additions to scripts/hooks/pre-commit. Check 13 is the same class. The nightly failure for run 55 is likely because removing `from __future__` from Python files is a code edit — nightly may not cover Python source edits in its autonomous scope. A bash addition to pre-commit is unambiguously in autonomous scope. Check 13 has higher autonomous delivery confidence than run 55's Python edit target.

**VERDICT: SURVIVES → WINNER**

---

## Idea 2: Fix `from __future__` in all 4 files + 10 em-dashes (extends run 55)

### Round 1 Challenge
Run 55 made this same recommendation (channels_instagram.py + 10 em-dashes). Nightly did not execute it (d12bd21 = log-only commit). What new mechanism makes this work in run 56?

### Round 1 Defense
Run 56 expands the target: 4 files (not 1) increases severity and makes the fix more urgent. The 3 new files (auth_password_reset.py, auth_billing.py, auth_google.py) serve production auth traffic. The urgency is higher. However, the MECHANISM hasn't changed — it's still pending_autonomous for nightly to execute Python source file edits.

### Round 2 Challenge
If nightly didn't execute the simpler version (1 file + em-dashes), there's no evidence it will execute the expanded version (4 files + em-dashes). The nightly channel's Python source edit capability is unproven. Recommending this as the winner repeats a failed mechanism.

### Round 2 Defense
Conceded. This is a real weakness. The nightly successfully edits .md files (SKILL.md, CLAUDE.md), bash files (pre-commit), and JSX strings (em-dash fix 8db33df). Python source file removal is less certain. Run 55 chose this as winner confidently but the nightly didn't execute.

### Round 3 Challenge  
Is this idea dominated by Idea 1 (Check 13)? If Check 13 is implemented, it catches all future violations. Idea 2 fixes current violations. Idea 2 should be a bonus action after Idea 1, not a standalone winner.

**VERDICT: WEAKENED → Parking Lot / Bonus action after Check 13 is implemented**

---

## Idea 3: Cross-tenant isolation tests for os_graph_memory.py

### Round 1 Challenge
Is this the highest-leverage action right now? The moratorium is active with from __future__ violations causing active 422 errors. Security test for graph isolation is speculative — no confirmed cross-tenant breach, no customer report.

### Round 1 Defense
The isolation gap is real and proactive. os_graph_memory.py stores per-tenant knowledge graph nodes/edges. The graph memory is surfaced to Agent OS agents which interact with real customers. A cross-tenant read would expose business knowledge between tenants. The pattern from runs 53-54: _TENANT_COLUMN_OVERRIDES miss hit 3 times in rapid succession before being caught. Prevention is cheaper than post-breach remediation.

### Round 2 Challenge
Even if valid, it loses to Idea 1 on all criteria: (a) lower urgency (no active bug vs. 422 errors), (b) similar autonomous delivery confidence, (c) smaller blast radius (1 service vs. all router splits forever). Why choose Idea 3 over Idea 1?

### Round 2 Defense
No compelling counter. Idea 3 is valid but loses head-to-head with Idea 1.

**VERDICT: WEAKENED → Parking Lot (ROI 2.1 stands)**

---

## Synthesis

- Idea 1 (Check 13: from __future__ guard): SURVIVES → **WINNER**
- Idea 2 (Fix 4 files + em-dashes): WEAKENED → Parking Lot (bonus action, run 55 remains pending_autonomous)  
- Idea 3 (Cross-tenant isolation): WEAKENED → Parking Lot
- Idea 4 (kb-autopopulate fallback): Not debated → Parking Lot ROI 1.8
- Idea 5 (Home.jsx split): Not debated → Parking Lot, HUMAN-REQUIRED
