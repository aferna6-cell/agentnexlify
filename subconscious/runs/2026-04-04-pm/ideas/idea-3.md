# Idea 3: Migration Safety Net — Pre-Push Unapplied Migration Check

**Category:** reliability
**Effort:** low (0.5–1 day)
**Impact:** High — stale migrations caused 2 bugs; 11+ day old files still pending

---

## Hypothesis

A pre-push git hook (or CI check) that compares migration files on disk against `schema_migrations` in Supabase and blocks/warns when unapplied files exist will prevent the class of bugs caused by schema drift. This directly addresses the root cause of the `lead_captured` bug (migration 074) and the conversations RLS bug (migration 080) — both fixed migrations that were initially not applied.

---

## Evidence

1. `docs/daily-logs/2026-04-03.md` lines 67–73: "Apply migrations 065–070 — 11+ days old… Apply migrations 077–079 — blocks onboarding wizard KB injection" — 3 P0/P1 tasks are JUST applying migrations.
2. bug-patterns.md: Two of the last 5 bugs (conversations.lead_captured always false; conversations RLS with no policies) involved migrations (074, 080) that either weren't applied promptly or had no corresponding enforcement.
3. CLAUDE.md: "Migration SQL files do NOT auto-apply" — this is documented but relies entirely on human discipline, which has already failed multiple times.
4. `migrations/` has 064+ numbered files but some duplicate numbers (005/007) — the naming discipline is already drifting.
5. git log: `migrations/` shows up in many commits but migration apply status is never verified programmatically.

---

## Implementation Sketch (no code)

1. **Script: `scripts/check-migrations.sh`** — queries Supabase via the MCP or REST API to list applied migrations, diffs against `migrations/*.sql` file list
2. **Pre-push hook addition** — add call to the script in `.git/hooks/pre-push` (alongside existing schema consistency check)
3. **Output** — lists unapplied files; exits 1 if any exist > 24 hours old; exits 0 with a warning if < 24 hours old (grace period for in-progress work)
4. **Graceful override** — `git push --no-verify` still works, but the failure is documented in the hook output with a timestamp

---

## Success Metric

- Zero migrations pending > 24 hours at next health check
- Pre-push hook catches stale migration scenario in test run
- `docs/dev-knowledge/schema-log.md` applied_at dates match within 24h of file creation
