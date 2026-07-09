# Idea 05: Diagnose Railway /healthz Handler Hang

**Category:** code_health  
**Effort:** S (grep + read backend, document root cause)  
**Moratorium impact:** NONE if AUTONOMOUS-EXECUTABLE read-only pass  
**Autonomous:** YES (read-only code investigation)

## Evidence

- GH #388: `/healthz` timed out at 10:27 UTC, `/version` returned 200
- Pattern: `/version` is a one-liner (returns app version). `/healthz` does more (likely DB ping, dependency checks)
- Partial failure = `/healthz` handler blocks on something that `/version` doesn't touch
- Likely culprits: DB connection pool exhaustion, slow Supabase health ping, synchronous I/O in async path

## Recommendation

Autonomous read-only investigation:
1. `grep -n "healthz\|health" backend/main.py backend/routers/*.py` — find handler
2. Read handler body — identify any blocking calls
3. Check: is DB ping behind `/healthz`? Is it async? Is there a timeout set on the DB call?
4. Document root cause in `docs/dev-knowledge/bug-patterns.md` under "Railway healthz timeout"
5. Recommend fix (probably: add `asyncio.wait_for(db_check(), timeout=5.0)` guard)

## Relationship to Idea 1

Idea 1 (alert monitoring) and Idea 5 (root cause) are complementary, not competing:
- Idea 1: notify when /healthz fails → DETECT failures
- Idea 5: fix /healthz handler → PREVENT failures

Idea 5 has higher long-term value but:
- Requires reading + analyzing code (longer)
- Fix needs implementation (adds to backlog if non-trivial)
- Idea 1 is immediately deployable and addresses the alert gap today

## Score

| Dimension | Rating |
|-----------|--------|
| Evidence quality | HIGH — GH #388, /version 200 vs /healthz timeout |
| Impact | HIGH (fix > detect) but blocked on diagnosis first |
| Effort | S investigation + unknown fix effort |
| Novelty | HIGH — never debated |
| Moratorium | NONE if read-only |

**Total: STRONG secondary — loses to Idea 1 on activation energy but worth bonus action**
