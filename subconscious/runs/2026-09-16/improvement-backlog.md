# Improvement Backlog — Run 2026-09-16 (Run 121)

## Active

- **Step 9E credential expiry escalation (2nd carry-forward):** Extend Step 9E to fire at `days_remaining <= 10` (not `>= 76d`) and file/comment on GH issue. AUTOPILOT_GH_TOKEN expires 2026-10-02. Auto-implements run 122 if not approved.

## Parking Lot (survived debate but not chosen)

- **Step 9G MCP trigger fix (Idea 2):** Replace unavailable `gh CLI` with `mcp__github__actions_run_trigger` in Step 9G block to fix KB self-heal trigger. XS effort. Run 122 candidate.
- **AI metering middleware proposal (Idea 4):** File GH issue proposing `backend/middleware/ai_metering_middleware.py` to fix GH #875's 40 violations systematically. Run 122-123 candidate.
- **Step 9C 30d escalation (Idea 5):** Add second threshold at 30+ days stale for brain connector (currently 55d). Run 122-123 candidate.

## Rejected This Run

- **Idea 3 (GH #870 batch patch script):** Not debated (below top 3 by impact). Deferred to run 123+. A script that generates per-file `block_demo_role` patches would be valuable but requires more engineering than XS and Step 9E urgency is higher.

## Questions for Next Run

1. Was AUTOPILOT_GH_TOKEN rotated before expiry (2026-10-02)? If yes, Step 9E implementation becomes proof-of-concept for the next cycle.
2. Does `mcp__github__actions_run_trigger` successfully fire kb-autopopulate.yml in nightly headless sessions? (Needed to validate Step 9G MCP fix before implementing)
3. GH #875 (40 AI metering violations): is the middleware approach technically viable given the existing `llm_runtime.py` bottleneck? Or does the variety of AI call sites require per-function treatment regardless?
4. Brain connector at 55d stale: is this a token issue (SUPABASE_ACCESS_TOKEN unknown) or a scheduling issue?
