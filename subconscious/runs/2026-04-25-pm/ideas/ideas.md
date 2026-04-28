# Subconscious Run 8 — Candidate Ideas
**Date:** 2026-04-25-pm  
**Evidence window:** 2026-04-22 → 2026-04-25

---

## Evidence Digest

**20 commits in 3 days.** Activity split: content/copy (em-dash ban, pricing cleanup), skills/rules (karpathy verbatim quotes, memory-tiered-retrieval rule), documentation (workspace agent blueprints, repo evaluations). No major backend features.

**Key signals:**
1. `037865f` added `scripts/check_project_invariants.py` — stdlib-only invariant checker, zero external deps. Not wired into any hook or CI. CLAUDE.md Critical Invariants describe 3+ production bugs from the exact naming violations this script catches.
2. **JS Silent Catch Guard (run 3) still unimplemented at day 14+.** Run 7 mandated "escalate directly if not by run 8." Violations confirmed: `AuthContext.jsx:89 .catch(() => {})`, `MarketingDashboardPage.jsx:96 .catch(() => null)`.
3. **Widget sync script (run 7 winner) NOT created.** `scripts/check-widget-sync.sh` does not exist despite 3+ days since recommendation. All 3 widget copies were touched in `037865f` (em-dash copy change) — likely in sync NOW, but gap has no automated guard.
4. **QA backlog: 25+ carried items** in current-tasks.md. widget_helpers split (run 5 winner, "implemented_unverified") still unverified — 1,673-LOC split of revenue paths untested.
5. **bug-patterns.md at 2,204 lines** (unchanged from run 7). Auto-logger writes daily.
6. **API key P0: day 22+ of exposure.** Still live in Railway.

---

## Idea 1: Wire check_project_invariants.py into Pre-commit Hook

**Evidence:** `037865f` (2026-04-25) added `scripts/check_project_invariants.py` — a stdlib-only script that walks the codebase checking for product-specific invariants (naming violations, etc.). The script header explicitly says it is "safe for CI and for agents." It is currently sitting unwired in scripts/. CLAUDE.md Critical Invariants section documents 3+ production bugs from naming violations (`tenant_id` vs `client_id`, `lead_stage` vs `status`). Pre-commit hook at `scripts/hooks/pre-commit` already runs Python checks (bare-except scan, `__future__` annotation scan). Adding one call to `check_project_invariants.py` costs zero new dependencies and ~2s of commit time.

**Action:** Add this block to `scripts/hooks/pre-commit` after existing Python checks:
```bash
# Invariant check — naming violations (client_id, status, areas_of_interest)
if ! python3 scripts/check_project_invariants.py 2>&1; then
  echo "BLOCKED: project invariant violation detected. Fix before committing."
  exit 1
fi
```

**Impact:** Catches naming-invariant violations at commit time. Directly prevents a documented recurring bug class (3+ production incidents). S-effort, zero deps, immediate guard.

**Category:** code_health

---

## Idea 2: JS Silent Catch Guard — Run 8 Escalation with Moratorium Flag

**Evidence:** Run 3 winner (2026-04-11), now 14 days unimplemented. Run 7 governance explicitly mandated: "If not by run 8, escalate directly." Violations confirmed still present: `AuthContext.jsx:89 .catch(() => {})` (auth-path silent failure, high risk), `MarketingDashboardPage.jsx:96 .catch(() => null)`, `LocalSEOPage.jsx:262`. The pre-commit hook has no JavaScript equivalent of the Python `bare-except` guard. Silent catch in auth context means authentication failures can be swallowed silently, appearing as logged-out state without any error trace.

**Action:** Add Check 9 to `scripts/hooks/pre-commit`:
```bash
# Check 9: JS silent catch guard
SILENT_CATCHES=$(grep -rn "\.catch\s*(\(\)\s*=>\s*{\s*}\|() => null\|() => {}" \
  frontend/src/ 2>/dev/null | grep -v "\.test\.\|node_modules" | wc -l)
if [ "$SILENT_CATCHES" -gt 0 ]; then
  echo "WARNING: $SILENT_CATCHES silent .catch() patterns found in frontend/src/"
  grep -rn "\.catch\s*(\(\)\s*=>\s*{\s*}\|() => null\|() => {}" frontend/src/ | grep -v "\.test\."
fi
```
AND set `moratorium_triggered: true` in governance.json — no new subconscious recommendations until this is implemented.

**Impact:** Prevents silent frontend error swallowing. Auth-context violation is highest risk. Moratorium flag forces implementation before backlog grows further.

**Category:** code_health / workflow

---

## Idea 3: Smoke-test widget_helpers Split Modules

**Evidence:** Run 5 winner (`6cf4646`, 2026-04-18) split 1,673-LOC `widget_helpers.py` into `widget_chat_helpers.py`, `widget_lead_helpers.py`, `widget_booking_helpers.py`. Governance status: `implemented_unverified`. current-tasks.md lists: "QA widget_helpers god-class split (6cf4646) — Cross-origin embed + booking + lead capture need prod smoke." These are revenue paths. The split has been unverified for 7 days.

**Action:** Create `backend/tests/test_widget_helpers_smoke.py` with three tests: `test_chat_helpers_imports_cleanly()`, `test_lead_helpers_imports_cleanly()`, `test_booking_helpers_imports_cleanly()`. Each imports the module and calls one exported function with a minimal fixture. Run in CI.

**Impact:** Closes the only `implemented_unverified` subconscious winner. Revenue-path modules verified at import + API level. S-effort, no Playwright needed.

**Category:** code_health

---

## Idea 4: Bug-patterns.md Monthly Split

**Evidence:** bug-patterns.md at 2,204 lines (unchanged since run 7). Auto-logger (`scripts/daily/nightly-commit-review.sh`) appends new entries daily. current-tasks.md shows 24 unenriched skeleton entries (runs from 2026-03-24 and 2026-04-07). The file is unscannable at 2,204 lines. The nightly auto-logger always appends to the same file; as bugs accumulate the file grows unboundedly. Parking lot ROI 1.8 since run 7.

**Action:** Split `docs/dev-knowledge/bug-patterns.md` into `bug-patterns-2026-03.md`, `bug-patterns-2026-04.md` (etc.) + `bug-patterns-INDEX.md` with a header table of contents. Update the auto-logger to write to `bug-patterns-YYYY-MM.md` for the current month. Update all references in scripts and CLAUDE.md.

**Impact:** File stays scannable month by month. Auto-logger remains functional. Enrichment of unenriched entries becomes tractable. M-effort (multi-file update).

**Category:** operational

---

## Idea 5: Implementation-Lag Moratorium Governance — Self-Enforcing Threshold

**Evidence:** 5 subconscious winners are unimplemented (runs 2, 3, 4, 7 + widget sync script). governance.json already has `implementation_lag_warning.escalate: true` from run 7. The warning exists but has no teeth — no threshold that triggers automatic change to recommendations. The subconscious keeps recommending new improvements while old ones sit unimplemented. At run 8, the moratorium criteria is met: 3+ consecutive runs with the oldest pending winner >14 days old.

**Action:** Add `moratorium_config` to governance.json: `{ "max_pending_approvals": 3, "max_pending_age_days": 14, "moratorium_active": true }`. When `moratorium_active` is true, next run's synthesis phase recommends IMPLEMENTING the oldest pending winner rather than generating new ideas.

**Impact:** Self-governing improvement system. Forces clearance of backlog before new recommendations compound. Converts passive `escalate: true` flag into an active constraint.

**Category:** workflow
