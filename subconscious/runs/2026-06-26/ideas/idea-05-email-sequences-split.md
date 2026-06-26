# Idea 5: Split email_sequences.py God Class (Rule 9 — 1143 lines)

**Category:** code_health
**Impact:** MEDIUM (removes god-class blast radius for future email feature work)
**Effort:** M (~2 hours, multi-file refactor)
**Autonomous-executable:** NO (sequencing-blocked: check must exit 0 first; Rule 9 requires plan approval)

## Evidence
- `backend/routers/email_sequences.py`: 1143 lines — triggers Rule 9 (>600 lines → split before adding)
- `frontend/src/pages/Home.jsx`: 1006 lines — same trigger
- `docs/dev-knowledge/council-fixes-register.md`: email_sequences noted as parking lot from council audit
- bug-patterns.md: god classes are where bugs compound; every additional concern increases blast radius
- TCPA compliance landed (migration 160 + sms_compliance.py) — similar compliance concern may hit email next; adding to 1143-line file is risky

## Action
1. Run `/improve-architecture` audit specifically on `backend/routers/email_sequences.py`
2. Factor into 3 modules:
   - `email_sequences_crud.py` — CRUD routes (list/get/create/update/delete)
   - `email_sequences_triggers.py` — trigger logic and scheduling
   - `email_sequences_analytics.py` — stats/reporting endpoints
3. Keep `email_sequences.py` as thin router that imports from the 3 modules

## Expected Impact
- Each module <400 lines, reviewable, independently testable
- Future compliance (CAN-SPAM, GDPR unsubscribe) lands in `email_sequences_triggers.py` not a 1200-line monolith
- Mirrors TCPA pattern: compliance logic isolated in dedicated service

## Status
**PARKING LOT** — sequencing-blocked on check exits 0 (Idea 1) + requires human plan approval per Rule 9. Run 70+ candidate.
