# Improvement Backlog — 2026-07-20 (Run 99)

## Active

- **Step 9F: KB Autopopulate Staleness Check** — ✅ IMPLEMENTED in SKILL.md by this run (run 99, 2026-07-20). Next: verify first nightly after implementation produces "Step 9F:" log line.

## Parking Lot (survived debate but not chosen)

- **platform_settings integer kill-switch safety** — SURVIVED. `resolve_int_setting` minimum bypass in `platform_flags.py` / `llm_runtime.py` means DB value "0" can silently kill non-boolean settings. No production rows at risk currently (all prod rows = boolean toggle=1). Revisit if numeric flag added to platform_settings table.

- **Step 9G: appointment auto-complete cron health** — WEAKENED. `auto_complete_past_appointments()` is 2 days old (PR #475, 2026-07-18). Premature monitoring — service failure would be visible in backend logs. Revisit run 100 after Step 9F confirmed working.

- **governance.json active_directions archive** — SURVIVED. 15+ active_directions entries, many stale (runs 88-92 booking/referral items superseded). Full archiving is L-effort — partially addressed via run 99 governance corrections. Revisit as dedicated cleanup task.

## Rejected This Run

- **conversation_enrichment_job.py queue investigation** — KILLED. Mandate condition "after GH #399 resolved" not met. GH #399 OPEN Day 17+. Filing ai-ready GH issue now adds to the 30+ blocked queue without clearing anything. Deferred until GH #399 resolved.

## Questions for Next Run (Run 100)

1. Did nightly-2026-07-21 execute Step 9F and produce "Step 9F:" log line? If not, why?
2. Is KB still within 7-day threshold? (Risk: as of 2026-07-20, it's exactly at the boundary — if GH Actions kb-autopopulate.yml didn't run today, KB is stale by 2026-07-21.)
3. GH #399 still open Day 18+? After 17 days, is there a secondary remediation path (new PAT, different secret name, manual loop restart)?
4. appointment_completion.py: any auto-complete events visible in nightly or backend logs? How many historical appointments were completed in the first cycle?
5. platform_settings: any non-boolean rows added since migration 175? If so, flag immediately.
