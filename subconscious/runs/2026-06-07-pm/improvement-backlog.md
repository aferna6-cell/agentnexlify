# Improvement Backlog — 2026-06-07-pm (Run 52)

## Active

- Fix `crypto.timingSafeEqual` in `agent-service/src/auth.ts` — close GH #206 timing side-channel in Agent OS v2 auth gate (run 52 winner)

## Parking Lot (survived debate but not chosen)

- **Merge PR #183** (GH #181 billing fix) — AMOUNT_TO_PLAN missing 15000+25000, PR exists 14 days. Bonus Action A in winning concept. Next human session after auth.ts fix.
- **Write integration tests for Agent OS v2 routing pipeline** — `os_orchestrate.py` → `agent_os_bridge.py` → agent-service chain, no cross-layer tests. M-effort. Widget hijack (2287f6b) shows regression risk. Promote run 54.
- **Create GH issue: apply migration 131 to production Supabase** — os_routing_decision + os_model_call_log tables. Time-sensitive. Bonus Action B in winning concept.
- **Fix autonomous channel structural issue** — SKILL.md trigger reads "most recent winning-concept.md contains AUTONOMOUS-EXECUTABLE" — breaks when non-AUTONOMOUS winning concept is chosen. Structural fix: change trigger to read governance.json entries directly. Deferred to run 54 if Check 10 still not wired.

## Rejected This Run

- **Idea 2 (merge PR #183 as primary winner)** — WEAKENED. Repetition cycle broken (run 51 same recommendation, unimplemented). Demoted to Bonus Action. Mechanism is broken, not information.
- **Idea 3 (restore autonomous channel as primary winner)** — WEAKENED. Valid mechanism but best deployed as embedded directive in winning concept, not primary recommendation.

## Questions for Next Run

1. Was GH #206 fixed in `agent-service/src/auth.ts` (`crypto.timingSafeEqual` in place)?
2. Did nightly 2026-06-08 wire Check 10 (`check_project_invariants.py` in pre-commit)?
3. Was PR #183 merged (GH #181 closed)?
4. Was migration 131 applied to production Supabase?
