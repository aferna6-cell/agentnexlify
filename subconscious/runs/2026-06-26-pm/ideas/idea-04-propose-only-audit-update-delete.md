# Idea 04 — Extend Propose-Only Pattern to UPDATE/DELETE Paths

**Category:** code_health  
**Confidence:** MEDIUM  
**Autonomous:** false — REQUIRES HUMAN  
**Effort:** S-M (~1.5h backend + tests)

## Summary
Council sprint Fix #7 landed `propose-only-records.md` rule + `record_audit.py` (72L) + `backend/routers/leads.py` changes + 83 tests. The current implementation covers the **CREATE path**: new records (leads, appointments) are flagged if created without the propose-only flow. But UPDATE/DELETE paths (changing lead status, archiving conversations, deleting appointments) carry equal or greater risk — a wrong status change or accidental delete is harder to reverse than a duplicate create. Extending `record_audit.py` to cover these paths closes the remaining gap.

## Evidence
- `backend/services/record_audit.py` exists and has proven test harness (83 tests passing)
- `propose-only-records.md` rule in `.claude/rules/` — currently scoped to record creation
- Highest-risk real scenario: tenant accidentally marks 50 leads as "closed-lost" via bulk action — no audit trail, no confirmation
- Adjacent pattern: `record_audit.py::audit_create()` already exists; `audit_update()` + `audit_delete()` would be symmetric additions

## Proposed Action
Add to `record_audit.py`:
- `audit_update(record_type, record_id, old_values, new_values, client_id)` — logs delta, flags if status changes are bulk/unusual
- `audit_delete(record_type, record_id, client_id)` — soft-delete log + confirmation flag for >= 5 records
Extend `leads.py` PATCH endpoint and any bulk-update paths to call `audit_update`.
Add 30+ tests to `tests/test_record_audit.py` covering update/delete scenarios.

## Why Competing
- Natural extension of fresh pattern — less "new work" and more "complete the pattern"
- Low blast radius: additive to existing audit service, no schema change
- But: moratorium active, propose-only just landed (3 days ago, should stabilize before extension)

## Sequencing
Strong run 69/70 candidate. Pair with council sprint retrospective to validate propose-only behavior in production first.
