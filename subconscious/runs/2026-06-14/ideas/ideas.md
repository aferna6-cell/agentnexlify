# Improvement Ideas — 2026-06-14 (Run 58)

## Evidence Digest

50 commits in 3 days. Two landmark events:
1. **check_project_invariants.py exits 0 for the first time** — 3234597 cleared all invariant
   violations: from __future__ (3 router files fixed), widget drift (landing-page-v2 cp'd),
   em-dash violations (11 JSX files patched). check_project_invariants.py passes all 6 checks.
2. **GH #181 FIXED** — billing.py now contains {9900, 15000, 25000, 89900}. Runs 55/57 and
   the billing fix (runs 30-34/51) are all effectively IMPLEMENTED — governance stale.

New surface: 651c6fe dropped WordPress plugin (wordpress-plugin/agentnexlify/agentnexlify.php,
325L PHP), IntegrationHealthDashboard.jsx (633L — crossed 600L god-class threshold on first
ship), qualification_rubrics.py (new service), widget_health.py (349L new service).

email_sequences.py: still 1255L. AI-to-Human Handoff: still unimplemented (run 4, 59 days).
Pre-commit: has Check 9 + 11 + 12 but NOT Check 10 (invariant gate) or Check 13 (from
__future__ bash guard). check-widget-sync.sh: still missing.

---

### Idea 1: Wire check_project_invariants.py into pre-commit as Check 10
**Evidence:** check_project_invariants.py exits 0 for the first time (verified live this run,
2026-06-14). Pre-commit has checks 1-9, 11, 12 — but not Check 10 (the invariant gate).
Run 22 (pending_autonomous, 51 days stale) and run 42 (de-coupled Item A) both target this.
3234597 cleared all violations — the gate can now be wired without false positives.
**Action:** Add ~5-line bash block to `scripts/hooks/pre-commit` (after Check 12) calling
`python3 scripts/check_project_invariants.py`. FAIL on nonzero exit. AUTONOMOUS-EXECUTABLE
via nightly (same class as Check 11 + 12 bash additions). Bonus: add Check 13 (from __future__
bash guard, 10 lines) in the same commit — run 56 pending_autonomous target.
**Impact:** Permanent enforcement of all 6 invariants at commit time. Prevents any new PR from
reintroducing from __future__, em-dashes, widget drift, or schema naming violations. Makes the
50-commit invariant sweep self-sustaining.
**Category:** code_health

---

### Idea 2: Wire Check 13 (from __future__ bash pre-commit guard, standalone)
**Evidence:** from __future__ import annotations has 3 infection events in 11 days (100%
recurrence rate on router splits). check_project_invariants.py has AST-level Python check
(line 49) but no bash-level pre-commit gate. Run 56 winner (pending_autonomous). Pre-commit
has Check 12 as last entry.
**Action:** Add 10-line bash block to `scripts/hooks/pre-commit` as Check 13: `grep -rn
"from __future__ import annotations" backend/routers/ backend/main.py --include="*.py"`.
FAIL mode (not WARNING). AUTONOMOUS-EXECUTABLE.
**Impact:** Belt-and-suspenders for CLAUDE.md Critical Invariant #5 (production 422 error
class). Dual layer: Python invariant script + bash gate at commit time.
**Category:** code_health

---

### Idea 3: Governance mega-correction + moratorium state audit
**Evidence:** 3234597 implemented runs 55 (em-dash + from __future__ fix), 57 (widget drift),
and the GH #181 fix covers runs 30/31/32/34/51 targets. governance.json still shows
`runs_pending_approval: 17` and `runs_implemented: 16`. True pending count is inflated.
Check_project_invariants.py ALL PASS means runs 55/57 are done.
**Action:** Apply governance corrections: runs 55, 57 → implemented (3234597). Run 51 →
implemented (billing.py now has 15000/25000). Increment runs_implemented 16→19. Re-count
true pending_approval. Determine if moratorium lift condition (pending ≤ 2) is met.
**Impact:** Accurate governance state. May reveal moratorium can be lifted, unblocking
email_sequences split (run 41) and AI-to-Human Handoff (run 4) as next winners.
**Category:** workflow

---

### Idea 4: Invoke /god-class-splitter on email_sequences.py (1255L)
**Evidence:** email_sequences.py confirmed 1255L (57 days stale, runs 35+41 winners never
implemented). GH #181 FIXED (prerequisite met). god-class-splitter SKILL.md ready (e848b87).
post-split-test-repair SKILL.md ready (d481799). 3 clean concerns: CRUD / enrollment /
processor. N+1 issues tracked (GH #112/#113).
**Action:** Invoke /god-class-splitter on email_sequences.py → split into
email_crud.py + email_enrollment.py + email_processor.py. Human-required (~2h).
**Impact:** Resolves oldest standing god-class. Enables targeted N+1 fix. Reduces blast
radius on 1255L file. Clears HUMAN-REQUIRED debt before next email automation sprint.
**Category:** code_health

---

### Idea 5: Add WordPress plugin smoke tests
**Evidence:** 651c6fe shipped wordpress-plugin/agentnexlify/agentnexlify.php (325L PHP) with
zero test coverage. New codebase territory — PHP, embedded JS, AJAX callbacks. Plugin
registers widget embed, handles form submissions, configures API key. No test infrastructure
in wordpress-plugin/ directory.
**Action:** Create `wordpress-plugin/tests/` with basic PHP unit tests (PHPUnit) for the
5 core plugin functions: widget_embed_shortcode, handle_ajax, api_key_settings, enqueue_scripts,
register_plugin. Add to CI.
**Impact:** Prevents WordPress plugin regressions at the moment it's most fragile (day 1).
Establishes PHP test pattern for future plugin features.
**Category:** code_health
