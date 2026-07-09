# Improvement Backlog — Run 70 (2026-06-28-pm)

Consolidated view of ideas not selected as winner this run. Ordered by priority for future runs.

---

## Active Queue (next 2-3 runs)

### 1. Fix KB Autopopulate (run 71 candidate)
- **Effort:** S-M (unknown failure mode)
- **Category:** Operational
- **Evidence:** 53 days stale. kb-autopopulate.sh broken since ~run 53.
- **Action:** `bash scripts/daily/kb-autopopulate.sh --dry-run 2>&1` → diagnose → fix
- **Why not winner:** Unknown root cause inflates effort estimate. SMS Dashboard has clear scope.

### 2. AI-to-Human Handoff v1 (run 71-72 candidate)
- **Effort:** M (1.5-2 days)
- **Category:** Customer Value — Critical
- **Evidence:** 74 days pending. All 7 industries. os_outbound_mirror.py now exists.
- **Action:** Detect trigger in widget_chat.py → write handoff_requests → SMS/email owner
- **Why not winner:** 7 prior recs without implementation. M-effort with moratorium active.
- **Unblock path:** Create GH issue with full spec as Bonus B (5 min, parallel track)

### 3. Record Audit Dashboard (run 72 candidate)
- **Effort:** S
- **Category:** Operational / Compliance
- **Evidence:** record_audit.py exists (council fix #7). No operator UI.
- **Action:** GET /api/admin/audit-log + AuditLogPage.jsx
- **Why not winner:** No urgency today. Zero delete-heavy workflows in production.

---

## Parking Lot (longer horizon)

### Email Sequences Split
- **Effort:** M
- **File:** `backend/routers/email_sequences.py` (1143L)
- **Skills ready:** god-class-splitter, post-split-test-repair
- **Sequence:** Invoke `/god-class-splitter` → 3 files (email_crud, email_enrollment, email_processor)
- **Blocker:** None (all prerequisites met). Moratorium = queue it properly.
- **When:** After moratorium clears or pending count drops.

### Plan-Name Guard Check 7
- **Effort:** S (5 min bash addition to pre-commit)
- **Status:** Was blocked until check_project_invariants.py exits 0. Now unblocked after run 70 mandate.
- **Action:** Add retired plan names (`foundation`, `operations`) to invariant check #3
- **When:** After human fixes widget drift and check exits 0.

### Pre-commit Auto-fix Flag
- **Effort:** M
- **Description:** `python3 scripts/check_project_invariants.py --fix` auto-applies safe fixes (em-dashes, widget cp)
- **When:** Post-council sprint stabilization period.

---

## Retired Topics

### Widget Drift (RETIRED — run 70 mandate)
- Retired from subconscious permanently. Human-only task.
- See `docs/reminders/widget-drift-URGENT.md` for fix command.
- If widget is updated in future: `cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js`
- Add to widget deploy checklist.
