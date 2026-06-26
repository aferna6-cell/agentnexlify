# Improvement Backlog — Run 68 (2026-06-26-pm)

## Active (pending implementation)

### P0 — Unblock Pre-Commit (MANDATE, run 65/68)
**Status:** pending_approval (REQUIRES HUMAN — 30-second terminal block above)  
**Winner since:** run 65 (2026-06-24)  
**Blocked:** 4 consecutive runs, pre-commit Check 13 FAIL+BLOCK since 2026-06-23  
**Action:** Paste terminal block from run 68 winning-concept.md

### P1 — AI-to-Human Handoff v1 (run 4, day 71)
**Status:** pending_approval (REQUIRES HUMAN)  
**Winner since:** run 4 (2026-04-16)  
**Blocked:** moratorium (true_pending ~6 >> max 2), no new forcing function  
**Action:** After moratorium exits — widget "Transfer to Human" button + tenant notification

### P1 — email_sequences.py god-class split (run 41)
**Status:** pending_approval (REQUIRES HUMAN)  
**Effort:** M (~2h, 1143L → 3 modules)  
**Action:** After moratorium exits

### P2 — Cleanup Sprint: runs 20/21/29/42/50 (various)
**Status:** pending_approval (REQUIRES HUMAN batch)  
**Effort:** ~1h total  
**Action:** After moratorium exits — drops true_pending ≤2 → moratorium exits

---

## Sequenced / Parking Lot

### Plan-Name Guard Check 7 (AUTONOMOUS-EXECUTABLE)
**Run:** 65 parking lot → run 69 active candidate  
**Sequencing:** After run 65 fix (check exits 0)  
**Effort:** XS (~20 lines Python)  
**Action:** Add `check_plan_names()` to `check_project_invariants.py` as Check 7

### SMS Compliance Dashboard Section
**Run:** 68 debate Bonus B → run 69 candidate  
**Sequencing:** After moratorium path clears  
**Effort:** S (~1h — endpoint + Settings page section)

### Propose-Only Audit Extension (UPDATE/DELETE)
**Run:** 68 debate Bonus C → run 69/70 candidate  
**Sequencing:** After propose-only stabilizes in production (3+ weeks)  
**Effort:** S-M (~1.5h — `audit_update()` + `audit_delete()` + 30 tests)

### Cross-Tenant Isolation Test (os_graph_memory)
**Run:** 54 parking lot  
**Effort:** XS (~10 lines, 2 tests)

### Fix kb-autopopulate.sh (agent-browser not installed)
**Run:** 54 parking lot  
**Effort:** S (replace agent-browser with curl/WebFetch)

### Tenant Scope Registration Checklist (schema-discipline.md)
**Run:** 54 parking lot  
**Effort:** XS (5-question checklist appended to rule file)

### California AI Companion Disclosure Audit
**Run:** 13 parking lot  
**Effort:** S (compliance review, possible widget disclosure banner)

### Zapier API key plan_status enforcement
**Run:** 16 parking lot  
**Effort:** S (1-line filter in `zapier_auth.py`)

---

## Rejected / Frozen Paths

- GH #181 fix (5-run mechanism exhausted, see governance.json rejected_paths)
- Full AI-to-Human Handoff implementation (moratorium-blocked, escalated via run 21)
- Duplicate SKILL.md recommendation (rejected run 67)
- Items A+B concurrent nightly execution (governance conflict — parallel autonomous deployment risk)
- Another meta-fix layer for nightly delivery gap (run 67 mandate: "no more meta-fix layers")
