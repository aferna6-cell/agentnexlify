# Winning Concept — 2026-04-04

## Recommendation
Apply the 4 existing skill updates flagged by weekly discovery — most critically, add RLS policy verification to schema-guard to prevent the #1 silent failure class from recurring.

## Why This, Why Now
The MTOptions chatbot audit (commit f18faa5) revealed that 120 of 146 chat sessions were silently failing due to RLS enabled without policies. This is the most dangerous bug class in the platform — completely silent, affects all data writes. The schema-guard skill is invoked before every migration and schema change, making it the perfect place to catch this. The other 3 skill updates (feature-build migration number, debug-api orphan diagnostic, migration-workflow dupe warning) are low-risk additions that prevent known recurring issues. All 4 updates were specifically identified with evidence in the skill discovery report.

## Implementation Sketch
1. Read `docs/skill-discovery/2026-04-04.md` for the exact update text for each skill
2. Update `.claude/skills/schema-guard/SKILL.md` — add RLS policy verification step: check `pg_policies` for any table with RLS enabled
3. Update `.claude/skills/feature-build/SKILL.md` — change "next after 032" to "check migrations/ for current highest number"
4. Update `.claude/skills/debug-api/SKILL.md` — add orphaned sessions diagnostic to the troubleshooting table
5. Update `.claude/skills/migration-workflow/SKILL.md` — add duplicate number warning step
6. Commit: `fix: update 4 skills per weekly discovery — RLS check, migration numbers, orphan diagnostic, dupe warning`

## What This Replaces
No previous active direction (first run).

## Confidence
HIGH — Evidence is strong (real production bug, specific skill discovery report with exact changes), implementation is low-risk (4 line-level edits to documentation files), and the RLS check alone prevents the most critical recurring failure.
