# Ideas — Run 2026-06-06-pm (Run 52)

## Evidence Digest

Nightly 2026-06-05 (8db33df) applied run 49 winner (5 JSX em-dash fixes). `check_project_invariants.py` exits 0 confirmed live (all 6 checks PASS). BUT Check 10 (wire `check_project_invariants` into pre-commit, Item A, `pending_autonomous` since run 22) is NOT in pre-commit. Root cause confirmed: nightly scanned `pending_autonomous` items BEFORE applying fixes, found Item A blocked, applied the em-dash fix, verified exit 0 — but did NOT re-scan pending_autonomous items afterward. Pre-condition for Item A met at end of cycle, no action taken.

Other state: `check-widget-sync.sh` MISSING (43+ days). `billing.py` missing 15000/25000 (GH #181, run 51 winner merge PR #183 pending human). `email_sequences.py` 1255L. Moratorium day 37. 15 pending items. No production feature commits 5+ days.

---

### Idea 1: Add post-fix re-scan to nightly — apply pending_autonomous items unblocked mid-cycle
**Evidence:** Nightly 2026-06-05 log explicitly confirms `check_project_invariants.py` exits 0 AFTER applying em-dash fix, then reports standing items including Check 10 — never executes it. Item A is `pending_autonomous + autonomous_executable: true`. Scope for pre-commit bash additions is live (run 43, 4226ef4). The single gap: nightly's pending_autonomous scan runs once (before fixes) and doesn't loop. At least 1 confirmed occurrence. Same-class SKILL.md edit as runs 40/43 — both implemented autonomously within 1 cycle.
**Action:** Append a "Post-Fix Re-scan" section to `nightly-commit-review SKILL.md`: after applying any LOW-risk fix, re-run `check_project_invariants.py`, then re-check `governance.json` `pending_autonomous` items for newly-unblocked pre-conditions and execute any that are now unblocked (same scope rules apply).
**Impact:** Item A (Check 10) wires in tonight's cycle or next. Generalizes: any fix that unblocks an autonomous item now triggers that item in the same cycle. Eliminates multi-cycle autonomous delays.
**Category:** workflow

---

### Idea 2: Merge PR #183 — billing fix (run 51 winner, still pending 24h)
**Evidence:** billing.py grep confirms 0 matches for 15000/25000. PR #183 is 13+ days old. GH #181 open. Check 11 WARNING fires on every commit. email_sequences.py split (run 41) prerequisites unmet. Run 51 recommended this as human-required ~10 min action. No new framing since run 51.
**Action:** Human reviews PR #183 diff (Step 1 from run 51 winning-concept.md), verifies CI, merges. ~10 min.
**Impact:** Closes GH #181, silences Check 11, unblocks email_sequences split.
**Category:** code_health
**Note:** This is run 51's winner — no new evidence since yesterday PM. Repeating as a winner without new forcing function weakens the recommendation. Bonus action only.

---

### Idea 3: Tag GH #107 (Zapier plan_status security) as ai-ready for issue-to-pr-loop
**Evidence:** GH #107 opened 2026-04-30 (37 days). `backend/services/zapier_auth.py::_get_api_key_client` resolves API keys without `plan_status` check. Cancelled tenants with un-revoked keys bypass tier gate. Parking lot since run 16, ROI 2.5. Never been a subconscious winner. No new exploitation evidence. Parking lot note explicitly says "route via issue-to-pr-loop, NOT subconscious winner queue."
**Action:** Add `ai-ready` label to GH #107. Add implementation hint in comment: "add `plan_status IN ('active','trialing')` filter in `_get_api_key_client` + regression test."
**Impact:** Issue enters issue-to-pr-loop for autonomous fix. Security gap closed. ~2 min.
**Category:** code_health / security

---

### Idea 4: Invoke /god-class-splitter on email_sequences.py (run 41 active_direction)
**Evidence:** `email_sequences.py` confirmed 1255L with 3 clean concerns (CRUD/enrollment/processor). god-class-splitter SKILL.md ready (e848b87). post-split-test-repair SKILL.md ready (d481799). GH #181 soft prerequisite (Check 11 warning noise). No new evidence since run 41.
**Action:** Invoke `/god-class-splitter email_sequences.py` — split into email_crud.py + email_enrollment.py + email_processor.py. ~2h human.
**Impact:** Resolves 1255L god-class. Fixes N+1 queries (GH #112/#113) becomes easier. Reduces blast radius.
**Category:** code_health
**Note:** GH #181 is still open (prerequisite). Moratorium active. Same as runs 35/41 active_direction. No new evidence.

---

### Idea 5: Fix nightly-commit-review SKILL.md — ensure run 50 AUTONOMOUS-EXECUTABLE scope extension executes
**Evidence:** Run 50 winner ("extend nightly scope + mark Item B AUTONOMOUS-EXECUTABLE") was committed 2026-06-05. Nightly 2026-06-05 applied run 49 (em-dash fix) but NOT run 50. `check-widget-sync.sh` MISSING confirms Item B did not execute. Run 50 added new scope to SKILL.md for Item B — but that SKILL.md edit itself may not have been applied.
**Action:** Verify whether nightly-commit-review SKILL.md was updated per run 50. If not, add Item B scope block explicitly (same mechanism as runs 40/43 — additive SKILL.md edit, autonomous scope).
**Category:** workflow
**Note:** Partially overlaps Idea 1. Both address nightly SKILL.md scope gaps. Idea 1 is more generalizable. If Idea 1 wins, run 50 scope extension should be included in the same SKILL.md edit.
