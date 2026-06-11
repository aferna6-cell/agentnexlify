# Candidate Ideas — 2026-06-11-pm

## Evidence Base

**27 commits in 3 days.** Active sprint: PRs #228–232. Key changes:
- PR #232: Instagram connector + Agent OS uploads/image-gen (21 files, 2228 insertions)
- PR #231: Security — HTML escaping in approval notification emails
- PR #229: Hotfix — vite config breaking prod build (orphaned `@xyflow/react` manualChunks)
- PR #228: Retire marketing add-on, schema-drift guard, major billing.py refactor

**check_project_invariants.py exits 1 with 2 failures:**
1. FAIL: `channels_instagram.py` flagged for `from __future__ import annotations` — FALSE POSITIVE. Script uses full-file text search (`"from __future__ import annotations" in text` at line 209), catching the warning comment at `channels_instagram.py:19` (`  - No from __future__ import annotations in FastAPI router files`). Not an actual import.
2. FAIL: 10 em-dash violations in 7 files introduced by PRs #228/232 (CookieConsent.jsx, MarketingUpsell.jsx, App.jsx, Sidebar.test.jsx, ReferralCard.jsx, ComposerAttachments.jsx, main.jsx).

**Item A (Check 10) still NOT wired** to pre-commit (grep confirms). Both failures must clear for Item A to auto-wire via nightly SKILL.md directive.

**Widget sync guard: PASSING** ("PASS widget assets are byte-identical across mirrors"). But `check-widget-sync.sh` script still MISSING — run 50 AUTONOMOUS-EXECUTABLE directive appears to have not fired.

**GH #181** (AMOUNT_TO_PLAN missing 15000→autopilot + 25000→professional): Still open. billing.py lines 259-274 confirmed still missing both entries after PR #228 major refactor.

---

### Idea 1: Fix check_project_invariants.py false positive (1-line anchor fix)
**Evidence:** Script line 209 `if "from __future__ import annotations" in text:` searches full file text, catching warning comments. `channels_instagram.py:19` has the prohibition as a docstring reminder. False positive confirmed by direct grep.
**Action:** Change line 209 to per-line check: `if any(line.strip().startswith("from __future__ import annotations") for line in text.splitlines())`. This fixes the false positive without changing actual import detection. Human execution ~2 min. Also mark 10 JSX em-dash violations AUTONOMOUS-EXECUTABLE for nightly tonight.
**Impact:** Once both checks pass, Item A (Check 10 wire) auto-fires via existing SKILL.md directive. Self-healing loop activated: future `__future__` violations blocked at commit. Em-dash violations blocked at commit. 50+ day blockage resolved.
**Category:** code_health

---

### Idea 2: Recognize widget sync guard as autonomy failure + recommend script creation via human session
**Evidence:** Run 50 marked Item B (check-widget-sync.sh) as AUTONOMOUS-EXECUTABLE (2026-06-05). Six days later: script still MISSING. Nightly hasn't created it. Widget copies ARE in sync ("PASS"), so no active harm. But the run 50 autonomous channel claim was wrong.
**Action:** Update governance to acknowledge autonomous channel failed for Item B. Recommend human-execute `check-widget-sync.sh` creation + pre-push wire (~10 min) in this interactive session.
**Impact:** Closes run 7/15/50 pending item (43+ days). Reduces true pending count by 1. Prevents future drift (widget is currently sync'd but unguarded).
**Category:** code_health / workflow

---

### Idea 3: Fix GH #181 AMOUNT_TO_PLAN — condition (b) new evidence evaluation
**Evidence:** billing.py at lines 259-274 still missing `15000: "autopilot"` and `25000: "professional"`. PR #228 performed major billing.py refactor (175→ reduced lines). Run #226 included "2nd billing bug fix" — unclear if test_billing_amount_to_plan.py backwards assertions (lines 38-44) were also fixed. If CI barrier cleared, this is 5 min not 15 min.
**Action:** Check if test_billing_amount_to_plan.py backwards assertions still exist. If cleared: add 2 lines to billing.py AMOUNT_TO_PLAN, done. If not cleared: remains 15 min.
**Impact:** Closes GH #181 (56-day open), unblocks email_sequences.py god-class split (stated prerequisite), reduces billing constant gap.
**Category:** code_health
**Governance note:** In rejected_paths with condition (b) — "new evidence about why it keeps being skipped." PR #228 confirmed path (known run 47) but doesn't change mechanism.

---

### Idea 4: Cross-tenant isolation test for os_graph_memory (AUTONOMOUS-EXECUTABLE)
**Evidence:** c8a0460 shipped os_graph_memory.py (397L) with 284 mock-based tests. Migration 133 has clean RLS. But NO test verifies client_id=A queries cannot return nodes from client_id=B. Parking lot ROI 2.1 (run 54).
**Action:** Create backend/tests/test_os_graph_isolation.py — 2 tests: (1) accumulate_from_turn(client_id=A) then graph_kb_entries(client_id=B) → empty; (2) accumulate_from_turn(client_id=B) then graph_kb_entries(client_id=A) → empty. AUTONOMOUS-EXECUTABLE: same class as run 53 winner (test_os_action_dispatch.py, nightly c6805a5).
**Impact:** Prevents silent cross-tenant data leakage in Agent OS knowledge graph. 2 tests, ~20 lines. Does not worsen moratorium (pending_autonomous, not pending_approval).
**Category:** code_health / security

---

### Idea 5: Fix kb-autopopulate.sh (35+ days broken — agent-browser CLI not installed)
**Evidence:** Parking lot ROI 1.8 (run 54). `scripts/daily/kb-autopopulate.sh` uses agent-browser CLI not installed in this environment. KB 35+ days stale. Run 54 added to parking lot.
**Action:** Replace `agent-browser` invocations in kb-autopopulate.sh with `curl` / Python `requests` calls. Or skip silently when unavailable with WebFetch fallback. AUTONOMOUS-EXECUTABLE: pure script change, LOW-risk, no schema changes.
**Impact:** Restores twice-daily KB auto-population (6 AM + 6 PM). Knowledge compounds again.
**Category:** operational
