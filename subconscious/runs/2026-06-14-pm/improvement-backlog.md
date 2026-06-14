# Improvement Backlog — 2026-06-14-pm

## Active
- Wire `check_project_invariants.py` as Check 10 in pre-commit (AUTONOMOUS-EXECUTABLE, 55-day gap, now unblocked — run 8 winner finally clear)

## Parking Lot (survived debate, not chosen)

- **Integration encryption backfill verification** — `backfill_integration_encryption.py` exists (9f9203d) but manual execution required for existing tenant OAuth tokens. Add documentation to `schema-log.md` migration 148 entry that backfill must run before sunset migration; optionally add preflight.py warning if encryption env not set. Ops-docs level fix, not winner-class improvement.
- **AI-to-Human Handoff v1** — 58-day gap, Critical cross-industry, scope reduced to ~1 day via `os_outbound_mirror.send_sms()` (PR #188). Trigger detection in `widget_chat.py` + lead status update. POST-MORATORIUM first priority. Do not re-recommend as winner until moratorium exits (governance corrections this run may push true pending ≤ 2).
- **check-widget-sync.sh + pre-push wire** — Prevents widget drift recurrence (run 7, 55+ days). Partially superseded by Check 10 (which catches widget sync at pre-commit). Pre-push gate still adds value for large widget PRs touching multiple copies. LOW effort, S-class.
- **E2E journey demo seed fixture** — 13 tests in `e2e/journeys/` "run red until demo seed created" per `cfdd6e3`. Verify `e2e.yml` handles missing fixtures gracefully OR ensure demo seed is created in CI setup step. Protects launch demo funnel signal.
- **email_sequences.py true god-class split** — Still 1143L (reduced from 1255L by cfdd6e3 perf refactor, not a split). 3 clean concerns (CRUD/enrollment/processor). `/god-class-splitter` SKILL.md ready. Pre-requisite: GH #181 now FIXED (billing.py confirmed correct). No remaining blockers.

## Rejected This Run
- **Check 13 (from __future__ guard as standalone new check)** — SUPERSEDED. Check 2 in pre-commit already guards `from __future__ import annotations` in backend router files. Check 10 provides broader coverage project-wide. Run 56 winner governance status updated to `superseded`.
- **Integration encryption backfill as winner** — WEAKENED to parking lot. Ops-docs level, not systemic. Adding live DB data validation to CI has security/complexity issues. Documentation addition is the right fix.

## Governance Corrections Applied This Run
- Run 57 (widget sync drift): `pending_autonomous` → `implemented` (by `3234597` + `landing-page-v2/widget/` updated)
- Run 55 (from __future__ + em-dash): `pending_autonomous` → `implemented` (by `3234597`)
- Run 56 (Check 13): `pending_autonomous` → `superseded` (Check 2 already guards this)
- Run 51 (billing PR #183): `pending_approval` → `implemented` (billing.py confirmed: 15000→autopilot, 25000→professional at lines 266-267)
- Run 34 (GH #181 critical_standing_action): → `implemented`
- Run 32 (GH #181): `pending_approval` → `implemented`
- Run 31 (GH #181): `pending_approval` → `implemented`
- True pending count after corrections: ~4 items (Check 10 wire, check-widget-sync.sh, email_sequences split, AI-to-Human Handoff)

## Questions for Next Run
- Was Check 10 wired? (`grep "CHECK 10" scripts/hooks/pre-commit` → should match)
- Did moratorium exit? (True pending_approval items ≤ 2 after corrections = moratorium exits)
- Was integration encryption backfill run on production? (check schema-log.md migration 148 notes)
- Are E2E journey tests now green in CI? (check `e2e.yml` workflow run status)
