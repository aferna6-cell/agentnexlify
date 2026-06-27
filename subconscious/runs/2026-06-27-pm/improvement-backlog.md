# Improvement Backlog — Run 70 (2026-06-27-pm)

Ordered by: urgency × impact / effort. Moratorium still active (true_pending ~6).

---

## URGENT (Human-only, run now)

### 0. Widget Byte-Sync Fix (RETIRED from subconscious — human manual action)
```bash
cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js
python3 scripts/check_project_invariants.py
git add landing-page-v2/widget/agentnexlify-widget.js
git commit -m "fix: sync widget to landing-page-v2 mirror (widget drift — run 70 mandate)"
```
**Unblocks:** all subsequent items below.

---

## APPROVED WINNER (Run 70)

### 1. AI-to-Human Handoff v1
- **Age:** 72 days (run 4, 2026-04-16)
- **Customer gap:** Critical, all 7 industries
- **Effort:** ~1 day
- **Infrastructure:** os_outbound_mirror.py (PR #188, 152 tests)
- **Files:** migrations/155, widget_chat.py, handoff_service.py (new), ConversationsPage.jsx
- **Full spec:** `subconscious/runs/2026-06-27-pm/winning-concept.md`

---

## BONUS A (AUTONOMOUS-EXECUTABLE, after widget drift fixed)

### 2. Plan-Name Invariant Guard — Add foundation + operations to Check 7
- **Effort:** XS (10 min nightly task)
- **File:** `scripts/check_project_invariants.py`
- **Trigger:** Once check exits 0 (widget drift fixed)
- **Autonomous:** YES — nightly can execute

---

## BONUS B (Human sprint, piggybacks on council SMS work)

### 3. SMS Compliance Dashboard (TCPA Visibility)
- **Effort:** S-M (3-4 hours)
- **Files:** new `SMSComplianceCard.jsx`, new `GET /api/sms/compliance-stats`
- **Context:** Council Fix #1 (9ddfd0e) wired TCPA opt-out suppression in backend — no dashboard surface yet
- **When:** Next council sprint touching SMS codebase

---

## PARKING LOT (Moratorium-blocked or tracked elsewhere)

### 4. Zapier API Key Plan Status Fix (GH #107)
- **Route:** issue-to-pr-loop (NOT subconscious winner — tracked as security bug)
- **File:** `backend/services/zapier_auth.py::_get_api_key_client`
- **Effort:** S (3-line filter + regression test)
- **Note:** parking_lot routing decision from run 16 stands. Issue-to-pr-loop owns delivery.

### 5. Email Sequences Split (run 41 direction)
- **File:** `backend/services/email_sequences.py` (1255L → 3 modules)
- **Effort:** M (2 hours, god-class-splitter SKILL.md ready)
- **When:** Post-moratorium exit. GH #112/#113 N+1 fix easier post-split.

### 6. Cross-Tenant Isolation Test for os_graph_memory
- **File:** `backend/tests/test_os_graph_memory_isolation.py` (new)
- **Effort:** XS-S
- **When:** Next Agent OS sprint

### 7. Add Tenant Scope Checklist to schema-discipline.md
- **File:** `.claude/rules/schema-discipline.md`
- **Effort:** XS
- **When:** When next Agent OS service is added

---

## MORATORIUM EXIT PATH

After run 70 widget fix (human):
1. Nightly: plan-name guard Check 7 (XS, autonomous) — true_pending unchanged but code health improves
2. Human: AI-to-Human Handoff v1 (~1 day) — true_pending drops when implemented
3. Human: email_sequences split (run 41) — true_pending drops
4. Human: cleanup sprint (runs 20/21/29/42/50) — true_pending → ≤2 → moratorium exits

Moratorium exit condition: `pending_approvals_count ≤ max_pending_approvals (2)`.
