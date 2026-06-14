# Candidate Ideas — 2026-06-13

## Evidence Digest
5 PRs (#246-#254) landed in the last 3 days (~10,000+ lines). PR #254 (3f79d7f, 31 files, 3500 lines) is the largest: adds push_subscriptions, activation_nudges, admin_health, Spanish widget translation, e2e journeys, and web push — AND diverged the widget. `check_project_invariants.py` exits 1 with 3 live failures: (1) `from __future__ import annotations` in 3 router files, (2) `widget/ != landing-page-v2/widget/` — ACTIVE DRIFT confirmed, (3) 10 em-dash violations (new additions from recent PRs). Pre-commit has CHECK 2 (from __future__ for router staged files) and Check 12 — no Check 13. Run 55/56 winners both pending_autonomous, neither implemented.

---

### Idea 1: Fix widget sync drift — copy updated widget.js to landing-page-v2/widget/ (AUTONOMOUS-EXECUTABLE)
**Evidence:** `check_project_invariants.py` CONFIRMS `widget/agentnexlify-widget.js != landing-page-v2/widget/agentnexlify-widget.js`. PR #254 (3f79d7f) git stat shows `widget/agentnexlify-widget.js | 202 ++++++++-` and `frontend/public/widget/agentnexlify-widget.js | 202 ++++++++-` — both updated. landing-page-v2/widget/ NOT in the stat. CLAUDE.md Critical Invariant #4: "Widget JS byte-identical in widget/ AND frontend/public/widget/". Three-copy requirement, only 2 of 3 updated.
**Action:** `cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js` — one command, no logic changes.
**Impact:** Fixes live CLAUDE.md Critical Invariant #4. Eliminates one of 3 check_project_invariants failures. Autonomous by nightly — same class as em-dash file substitutions.
**Category:** code_health

---

### Idea 2: Add Check 13 — extend from __future__ guard to all backend Python (run 56 winner)
**Evidence:** Pre-commit CHECK 2 only covers `*routers*.py` and `*router*.py`. PR #254 added `backend/services/activation_nudges.py` (310 lines) with only a comment warning against the import — not caught by CHECK 2 if someone forgets. check_project_invariants.py confirms 3 router files still have violations. Run 56 winner (pending_autonomous) targets this exact gap.
**Action:** Insert 10-line bash block after Check 12 in `scripts/hooks/pre-commit`, scoped to `backend/**/*.py`, FAIL mode (ERRORS increment).
**Impact:** Catches `from __future__` in any backend Python file at commit time, not just router-pattern filenames. Closes gap for service files.
**Category:** code_health

---

### Idea 3: Fix 10 em-dash violations + from __future__ actual imports (run 55 expansion)
**Evidence:** check_project_invariants.py shows 10 em-dash violations: main.jsx:153, CookieConsent.jsx:5/31, MarketingUpsell.jsx:3, App.jsx:329, Sidebar.test.jsx:27/49, Sidebar.jsx:386, DemoBanner.jsx:4/7. New violations introduced by abc15c4 (DemoBanner.jsx) and 3f79d7f (Sidebar.jsx:386). Run 55 (pending_autonomous) covers channels_instagram + prior em-dashes — but target list has EXPANDED by at least 3 new violations.
**Action:** Replace 10 em-dash characters in JSX files + remove `from __future__ import annotations` from 3 router files. check_project_invariants exits 0 → Check 10 auto-wires tonight.
**Impact:** check_project_invariants exits 0 → enables Check 10 auto-wire; plus widget fix (Idea 1) needed for full PASS.
**Category:** code_health

---

### Idea 4: Fix kb-autopopulate.sh — replace agent-browser with WebFetch/curl fallback
**Evidence:** Parking lot ROI 1.8, 35+ days broken. `scripts/daily/kb-autopopulate.sh` uses agent-browser CLI (not installed). KB last populated 35+ days ago. Recent massive feature velocity (Agent OS, demo system, push notifications) has generated new patterns worth documenting. Twice-daily auto-population offline means KB compounds stale.
**Action:** In `scripts/daily/kb-autopopulate.sh`, replace `agent-browser` invocations with WebFetch/curl calls OR wrap with `command -v agent-browser || exit 0` silent skip.
**Impact:** Restores KB auto-population. New features (approve-by-text, Agent OS knowledge graph, push notifications) can be auto-documented.
**Category:** operational

---

### Idea 5: Cross-tenant isolation test for os_graph_memory.py
**Evidence:** Parking lot ROI 2.1 (added run 54). `c8a0460` shipped os_graph_memory.py (397L) with 284 mock-based tests. No test verifies that `graph_kb_entries(client_id=B)` returns empty after `accumulate_from_turn(client_id=A)`. Agent OS Phase 3 shipped 30+ agents — knowledge graph is now core to multi-tenant AI context. RLS migration 133 exists but no app-level isolation test.
**Action:** Add 2 tests to `backend/tests/test_os_graph_memory.py`: seed graph for client_id=A, query with client_id=B, assert empty result.
**Impact:** Catches any regression in cross-tenant isolation on the knowledge graph layer before it reaches production.
**Category:** code_health / security
