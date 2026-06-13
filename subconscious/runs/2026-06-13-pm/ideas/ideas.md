# Ideas — Run 2026-06-13-pm

## Evidence Digest

**50 commits in 7 days** — launch-readiness sprint (PRs #249-#257). PR #257 (3234597) is the key event:
it cleared all three check_project_invariants.py failures (widget sync, em-dashes, from __future__) as part
of a P0 sweep. `check_project_invariants.py` exits 0 for the first time in 50+ days. GH #181 billing fix
confirmed (AMOUNT_TO_PLAN has 15000→autopilot + 25000→professional since PR #255). email_sequences.py
remains 1255L (run 41 winner, 14+ days). check-widget-sync.sh MISSING 50+ days. AI-to-Human Handoff
(run 4) still Critical gap, 60+ days. Pre-commit has Checks 1-9 only — no Check 10.

---

### Idea 1: Wire check_project_invariants.py into pre-commit as Check 10 (AUTONOMOUS-EXECUTABLE)
**Evidence:** check_project_invariants.py exits 0 for first time in 50+ days — the only blocking condition
is now cleared (PR #257 fixed widget sync, em-dashes, and from __future__). Pre-commit has Checks 1-9,
no Check 10 (confirmed grep). Run 8 winner (2026-04-25), 50-day pending item. Nightly SKILL.md extended
(4226ef4) to cover pre-commit bash additions. Check 11 (billing guard) wired autonomously by 061582c —
same class. Check 12 (timing-safe guard) wired autonomously by ca3ce68 — same class.
**Action:** Add 3-line bash block to scripts/hooks/pre-commit as Check 10: call
`python3 scripts/check_project_invariants.py` in FAIL mode, exit 1 on violations.
**Impact:** Future invariant violations (widget drift, em-dash regression, from __future__ regression,
retired field usage) blocked at commit. Closes 50-day pending item. Activates the quality gate
check_project_invariants.py was built for.
**Category:** code_health

---

### Idea 2: Create scripts/check-widget-sync.sh + wire to pre-push hook (AUTONOMOUS-EXECUTABLE)
**Evidence:** MISSING 50+ days (runs 7/15/50). PR #257 manually fixed widget drift but created no
automated guard. Widget JS has changed 3+ times in 7 days (PR #254 +202 lines, PR #257 backfill).
Velocity will continue. check_project_invariants.py checks widget byte-identity but only runs manually.
check-widget-sync.sh provides pre-push enforcement. Run 7 pending_autonomous.
**Action:** Create scripts/check-widget-sync.sh (diff widget/ vs frontend/public/widget/ vs
landing-page-v2/widget/, FAIL on diverge). Wire to scripts/hooks/pre-push.
**Impact:** Widget drift blocked at push, not discovered post-deploy. Complementary to Check 10
(pre-commit monitors; pre-push enforces before push).
**Category:** code_health

---

### Idea 3: Invoke /god-class-splitter on email_sequences.py (HUMAN-REQUIRED)
**Evidence:** email_sequences.py confirmed 1255L, run 41 winner, 14+ days unimplemented. GH #181
prerequisite CLEARED (billing.py has 15000+25000 since PR #255). god-class-splitter SKILL.md exists
(e848b87). post-split-test-repair SKILL.md exists (d481799). GH #112/#113 (N+1 queries) open.
**Action:** Run /god-class-splitter — split into email_crud.py + email_enrollment.py + email_processor.py.
3 independent concerns, no circular deps.
**Impact:** Reduces god class, enables GH #112/#113 N+1 fixes, improves testability, closes run 41.
**Category:** code_health

---

### Idea 4: Implement AI-to-Human Handoff v1 via Agent OS infrastructure (HUMAN-REQUIRED, M-effort)
**Evidence:** 60+ days pending (run 4), Critical customer gap all 7 industries per customer-gaps.md.
os_outbound_mirror.py (PR #188, 152 tests) handles SMS/email delivery. Agent OS fully merged.
conversation_notify.py shipped (PR #255). Scope is ~1 day (trigger detection + handoff_requests
table write + os_outbound_mirror.send_sms() call).
**Action:** Add explicit trigger detection in widget_chat.py → write handoff_requests table → call
os_outbound_mirror.send_sms() to owner phone number.
**Impact:** Closes #1 customer gap (Critical, all 7 industries). Demo-critical for launch sprint.
**Category:** customer_value

---

### Idea 5: Fix kb-autopopulate.sh broken fallback (AUTONOMOUS-EXECUTABLE)
**Evidence:** kb-autopopulate.sh broken 35+ days (noted runs 52/53/54). Cause: agent-browser CLI
not installed in remote env. KB 34+ days stale in run 53. CLAUDE.md: "twice daily 6 AM + 6 PM via
scripts/daily/kb-autopopulate.sh". Competitor research, customer gap discovery both depend on KB.
**Action:** Modify scripts/daily/kb-autopopulate.sh to fallback to WebFetch/WebSearch MCP tools
when agent-browser CLI absent (`which agent-browser` check).
**Impact:** KB stays current twice daily. Competitive intelligence live. Customer gap discovery
accurate. Fixes dormant automation.
**Category:** operational
