# Idea 2 — Add brain/INGESTION-LOG.md to Phase 2 Evidence Sources

**Category:** workflow
**Effort:** XS (one-line SKILL.md addition)
**Confidence:** HIGH

## What
Add `brain/INGESTION-LOG.md` to the "Also read:" block in the Phase 2 (Gather Evidence) section of `.claude/skills/subconscious/SKILL.md`. This gives every future subconscious run a direct signal on brain connector health before ideation.

## Evidence
- Run 82 parking lot item 1: "Add brain/INGESTION-LOG.md to Phase 2 evidence in SKILL.md. One-line addition. Deferred per mandate: after GH #394 resolved."
- Brain connector failure (GH #394) went undetected 4 days before run 79 caught it (run 79 evidence).
- Commit `a0874c4` (2026-07-08) shows successful brain refresh — brain connectors may be partially recovering.
- Step 9C added to nightly SKILL.md (run 80 winner) now monitors connectors nightly. Subconscious still lacks this signal in Phase 2.
- INGESTION-LOG.md now exists at `brain/INGESTION-LOG.md` (confirmed: a0874c4 wrote +4 lines today).
- Run 82 mandated this for run 83 if GH #394 resolved. Evidence of recovery (a0874c4) partially satisfies.

## Dependency Check
Run 82 parking lot note said "deferred: after GH #394 resolved." GH #394 not formally resolved (run 79 still pending_human). However:
- a0874c4 shows successful refresh today (brain/ updated)
- INGESTION-LOG.md exists and has current data
- Adding the "Also read:" line is safe even if connectors are intermittent — Phase 2 reads the log as-is (partial data beats no data)

Dependency is satisfied enough to proceed.

## Impact
- Every future subconscious run (84+) will read brain freshness signal in Phase 2
- Connector failures surface before ideation, not via parking lot
- Zero risk: additive SKILL.md edit, no code change

## Autonomous-Executable?
YES — additive SKILL.md edit, LOW-risk, same class as runs 40/43 autonomous SKILL.md changes that nightly review successfully implemented.

## Implementation Sketch
In `.claude/skills/subconscious/SKILL.md`, Phase 2 "Also read:" block, add one line:
```
- brain/INGESTION-LOG.md (last 10 lines — connector health signal)
```
