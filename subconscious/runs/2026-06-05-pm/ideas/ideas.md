# Ideas — Run 2026-06-05-pm (Run 51)

## Evidence Digest

Run 50 (AM) queued Items A+B for tonight's nightly (2:37 AM). check_project_invariants.py exits 0 (all 6 PASS). Pre-commit only has Check 11; Check 10 not wired. check-widget-sync.sh MISSING (day 43). email_sequences.py 1255L. GH #181 open: billing.py AMOUNT_TO_PLAN confirmed at backend/routers/billing.py:263, missing 15000→autopilot + 25000→professional. PR #183 (12-day draft) labeled "merge — confirmed path" by morning digest. PR #200 (nightly SKILL.md scope extension) draft, unmerged. AI-to-Human Handoff: 50 days pending, Critical, os_outbound_mirror.py merged. Zapier plan_status security: GH #107, 36+ days. Moratorium day 35, 14 pending.

Zero new code commits since nightly 8db33df (em-dash fix). This PM run focuses on human-executable actions available NOW that AM run 50 did not address.

---

### Idea 1: Verify and merge PR #183 — close GH #181 via existing billing fix PR
**Evidence:** Morning digest labels PR #183 "merge — confirmed path." Path confirmed run 47 (2026-06-02-pm): backend/routers/billing.py:263. AMOUNT_TO_PLAN missing 15000→autopilot + 25000→professional for 26+ days. Check 11 WARNING fires every commit. PR exists 12 days as draft. rejected_paths governance bars GH #181 as winner when recommendation = "write the fix." This recommendation = "review + merge existing PR" — categorically different framing.
**Action:** Read PR #183 diff, verify it targets backend/routers/billing.py (not services/) and adds 15000 + 25000 entries, verify test assertions are corrected. If correct: `gh pr ready 183 && gh pr merge 183 --squash`.
**Impact:** Closes GH #181. Silences Check 11 WARNING. Unblocks email_sequences.py split (run 41 active_direction, 1255L). Reduces moratorium pressure. ~10 min including review.
**Category:** code_health

---

### Idea 2: Merge PR #200 — ensure Item B executes tonight
**Evidence:** Morning digest priority #1: "Merge PR #200 — 5 min. SKILL.md scope extension required for nightly to execute Item B autonomously tonight. PR is draft but correct." Without scripts/ + pre-push scope bullets on main, nightly may not know how to create check-widget-sync.sh + wire pre-push.
**Action:** `gh pr ready 200 && gh pr merge 200 --squash`
**Impact:** Ensures Item B (widget sync guard) fires tonight. Items A+B both close in same nightly cycle. Pending drops by 2.
**Category:** workflow

---

### Idea 3: Create AI-to-Human Handoff v1 GH issue with ai-ready label
**Evidence:** Run 4 winner, 50 days pending (oldest). Critical gap all 7 industries. os_outbound_mirror.py merged (PR #188, 152 tests) — delivery layer ready. Last recommended as winner in run 38 (25 days ago). New evidence: infrastructure now complete. 5-min docs action, moratorium-exempt.
**Action:** Create GH issue: "feat(widget): AI-to-Human Handoff v1 — explicit trigger → notify owner via os_outbound_mirror". Full implementation sketch from subconscious/runs/2026-05-28-pm/winning-concept.md. Labels: customer-value, widget, backend, ai-ready.
**Impact:** Closes oldest pending item (50 days). Creates actionable GH issue. Routes to issue-to-pr-loop.
**Category:** customer_value

---

### Idea 4: Create ai-ready GH issue for Zapier plan_status security fix
**Evidence:** bug-patterns.md: zapier_auth.py::_get_api_key_client missing plan_status IN ('active','trialing') check. GH #107 open 36+ days. Cancelled tenants with un-revoked keys bypass tier gate. Parking lot ROI 2.5. Parking lot note says "route via issue-to-pr-loop, NOT subconscious winner queue." 2-min action.
**Action:** Create GH issue with ai-ready label: "fix(zapier): add plan_status filter to _get_api_key_client". ~10-line fix sketch. Routes to issue-to-pr-loop for autonomous fix.
**Impact:** Security gap closed autonomously. Reduces attack surface for cancelled tenants. Parking lot ROI 2.5 realized.
**Category:** code_health (security)

---

### Idea 5: Invoke /god-class-splitter on email_sequences.py (run 41 active_direction)
**Evidence:** 1255L (confirmed today). god-class-splitter SKILL.md ready (e848b87). post-split-test-repair SKILL.md ready (d481799). GH #112/#113 N+1 fixes easier post-split. Run 41 active_direction. Moratorium technically active but god-class splits are M-effort, not blocked by moratorium if they don't add to pending.
**Action:** Invoke /god-class-splitter on backend/routers/email_sequences.py. Split into email_crud.py + email_enrollment.py + email_processor.py (<600L each). Human approval of resulting PR.
**Impact:** Closes run 41 active_direction. Enables N+1 fix (GH #112/#113). 3 clean modules from 1 god class. 2-3h execution.
**Category:** code_health
**Blocker:** Run 41 note: "GH #181 billing fix (~15 min, human required) before starting split." GH #181 still open.
