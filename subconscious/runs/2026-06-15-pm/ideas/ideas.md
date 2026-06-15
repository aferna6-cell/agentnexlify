# Ideas — 2026-06-15-pm

## Evidence Digest

PR #257 (3234597, 2026-06-13) cleared ALL check_project_invariants failures in a single batch:
widget sync (cp to landing-page-v2/widget/), em-dashes (12+ JSX files), and `from __future__`
(3 router files). `check_project_invariants.py` now exits 0 — runs 55, 56, 57 all implemented.

PR #288 (9bed342) repriced to two-plan model: AMOUNT_TO_PLAN now {1999:chatbot, 9999:agent_os}.
**Check 11 now fires false WARNING on every commit**, scanning for amounts {9900,15000,25000,89900}
that no longer exist. GH #181 and all related billing-fix pending items are superseded.

PR #291 (ff2ca28) gated signup behind payment: real paying customers now active. Launch-readiness
audit (2026-06-15) reports 862 tests passing, security PASS, JWT stale claims (M3) deferred.

---

### Idea 1: Update Check 11 + Wire Check 10 (combined pre-commit cleanup)
**Evidence:** PR #288 repriced AMOUNT_TO_PLAN to {1999:chatbot, 9999:agent_os}; Check 11 false-WARNs
on every commit (REQUIRED_AMOUNTS=(9900 15000 25000 89900) — none exist in repriced billing.py).
check_project_invariants.py exits 0 (PR #257 cleared all blockers). Check 10 pending 60+ days with
no remaining blocker.
**Action:** (a) Update Check 11 REQUIRED_AMOUNTS to (1999 9999); (b) Add Check 10 block (3-line
python3 scripts/check_project_invariants.py call, FAIL on non-zero exit) before Check 11.
**Impact:** Eliminates false WARNING on every commit; 60+ day pending item wired; invariant gate
catches future em-dash / from __future__ / widget drift at commit time.
**Category:** code_health

### Idea 2: Fix Check 11 false positive only (narrow variant of Idea 1)
**Evidence:** PR #288 made Check 11 permanently fire WARNING about old billing amounts that no longer
exist. Every developer sees "AMOUNT_TO_PLAN missing entries: 9900 15000 25000 89900" on every commit.
Warning fatigue = real warnings get ignored.
**Action:** Update REQUIRED_AMOUNTS in Check 11 to `(1999 9999)` and correct plan names in the error
message from "9900 (growth), 15000 (autopilot), ..." to "1999 (chatbot), 9999 (agent_os)".
**Impact:** Stops false-positive billing warnings immediately.
**Category:** code_health

### Idea 3: Wire Check 10 (check_project_invariants) to pre-commit as Check 10 (narrow variant)
**Evidence:** check_project_invariants.py exits 0 — first unblocked state since run 44 (~45 days).
60+ days pending. Pre-commit currently has no Check 10. All blockers cleared by 3234597.
**Action:** Add 3-line bash block before Check 11: call python3 scripts/check_project_invariants.py,
FAIL on non-zero exit. AUTONOMOUS-EXECUTABLE (same class as Check 11 added by nightly 061582c).
**Impact:** Future em-dash, from __future__, widget drift, retired-column violations caught at commit
time — self-healing invariant loop.
**Category:** code_health

### Idea 4: Address JWT stale plan/role claims (M3 from launch audit)
**Evidence:** audits/audit-launch-readiness-2026-06-15.md defers M3: "JWT 24h stale plan/role claims
— token-version check needs per-request DB read." PR #291 (pay gate) now means plan downgrades/
cancellations leave paying users with paid-tier access for up to 24h.
**Action:** Add token_version to tenants table; JWT includes version; auth dependency validates version
against DB on each request; bump version on plan change.
**Impact:** Instant plan changes; closes MEDIUM security gap from launch audit.
**Category:** code_health / security

### Idea 5: AI-to-Human Handoff v1 (customer_value, run 4, 60+ days)
**Evidence:** customer-gaps.md: Critical across all 7 industries. os_outbound_mirror.py (PR #188,
152 tests) handles SMS/email delivery. PR #291 (pay gate): real paying customers now active —
churn from unhandled complex queries directly costs revenue. Run 4 = 60 days pending.
**Action:** Add trigger detection in widget_chat.py; write to handoff_requests table; call
os_outbound_mirror.send_sms() to notify business owner.
**Impact:** Reduces churn from complex AI queries; protects paying customer revenue.
**Category:** customer_value
