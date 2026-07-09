# Improvement Backlog — Run 73 (2026-06-30)

## Parking lot (deferred, not rejected)

### Plan-Name Guard Check 7
- Origin: Run 67 proposal; unblocked 2026-06-23 (GH #292/#293)
- Why deferred: human session needed (Python script edit outside nightly scope); lower customer value than SMS Dashboard
- Re-evaluate: run 74 IF SMS Dashboard shipped by then
- Effort: S | Risk: LOW | NOT autonomous

### AI-to-Human Handoff v1 (scoped via os_outbound_mirror.py)
- Origin: Run 4 (2026-04-16) — 75+ days
- Why deferred: 7 failed recs, no new readiness signal, M-effort + migration
- Re-evaluate: run 75 with explicit owner commitment signal OR when pending queue < 2
- Effort: M | Risk: MEDIUM | NOT autonomous
- Competitive: GoHighLevel "AI Employee" — critical gap remains

### email_sequences.py Split
- Origin: Run 41 pending_approval
- Why deferred: moratorium (true_pending 4+), M-effort, HIGH blast radius, no urgency signal
- Re-evaluate: when moratorium lifts (pending queue < 2)
- Effort: M | Risk: HIGH (call-site migration) | NOT autonomous

## Operational notes

### KB cron verification
- Script fix: DONE (65284cc, 2026-06-30)
- `knowledge-base/log.md`: still at 2026-05-05 — cron not yet fired post-fix
- Human action: `tail -3 knowledge-base/log.md` post-cron to confirm; manual trigger if cron not wired
- Not blocking

### Moratorium status (post-corrections)
- true_pending after run 71+72 correction: ~4
  - Run 70: SMS Compliance Dashboard (pending_approval → being recommended NOW as run 73 winner)
  - Run 41: email_sequences.py split (pending_approval)
  - Run 38: AI-to-Human Handoff (pending_approval)
  - Run 4: AI-to-Human Handoff original (pending_approval)
- Moratorium lifts when true_pending < 2
- SMS Dashboard (run 73 winner) closes run 70 pending → true_pending drops to ~3 after human executes

## Recently closed
- Runs 71+72: kb-autopopulate fix → IMPLEMENTED by nightly 65284cc (2026-06-30)
- Runs 65-70: widget drift topic → RETIRED (6 consecutive delivery failures; landing-page-v2 is confirmed legacy)

## Next recommended run (74) focus areas
If SMS Dashboard shipped by run 74:
1. Plan-Name Guard Check 7 (first in parking lot queue, S-effort)
2. AI-to-Human Handoff v1 — reconsider only with readiness signal
3. Architecture health check (IMPROVE-ARCHITECTURE cadence: overdue)

If SMS Dashboard NOT shipped by run 74:
1. Re-escalate SMS Dashboard with specific blocker diagnosis
2. Do NOT add new recommendations while 4+ items are pending
