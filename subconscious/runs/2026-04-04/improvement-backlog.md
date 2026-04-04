# Improvement Backlog — 2026-04-04

## Active
- Update 4 stale skills per weekly discovery (schema-guard RLS check, feature-build migration number, debug-api orphan diagnostic, migration-workflow dupe warning)

## Parking Lot (survived debate but not chosen)
- Fix failing test `test_resend_webhook_route_is_registered` — one-off but foundational for CI trust

## Rejected This Run
- Build AI-to-human handoff feature — too large for atomic recommendation; belongs in `/new-feature` pipeline

## Not Debated (lower impact)
- Populate 4 empty KB categories via /kb-discover — valuable but not urgent
- Consolidate duplicated test fixtures into conftest.py — good housekeeping, low urgency

## Questions for Next Run
- Did the skill updates get applied? Check if the 4 files were modified since this run.
- Is the failing test still red? If so, escalate priority.
- Are any new tenants onboarding? Check for chatbot audit needs.
