# Idea 3: Add brain/INGESTION-LOG.md to Subconscious Phase 2 Evidence Sources

**Category:** Workflow Efficiency (self-improvement)  
**Effort:** XS (3–5 lines in `.claude/skills/subconscious/SKILL.md`)  
**Autonomous:** YES — SKILL.md edit, same class as Step 9B/9C additions  
**Source:** Parking lot P-BRAIN-EVIDENCE (from run 80 debate-log Idea 3)  

---

## Evidence

- Runs 77 and 78 ideated without knowing the brain had been failing for 4+ days  
- Run 79 detected brain failure INCIDENTALLY (read a brain-refresh bot commit by chance)  
- Detection lag: 4+ days between first failure (Jul 1) and first detection (Jul 5)  
- Step 9C now handles escalation detection in nightly-commit-review  
- But the SUBCONSCIOUS Phase 2 evidence gathering STILL does not read `brain/INGESTION-LOG.md`  
- Runs 77, 78, 80 all proposed improvements without knowing agent context was stale  

## What This Adds

In Phase 2 (Evidence Gathering), after existing commands, add:

```bash
tail -10 brain/INGESTION-LOG.md
```

And instruct the subconscious: if last entry shows consecutive failures, note in evidence digest: "Brain data stale since [date] — ideation may miss recent developments."

## Impact

- Future runs know upfront whether brain is fresh or stale  
- Avoids recommending "check the brain logs" as a discovery when it should be baseline  
- Closes the gap that cost 4 detection days in the Jul 1–5 incident  
- XS cost: 3 lines + 1 instruction sentence  

## Why Not Winner This Run

Brain connectors currently failing (Day 7). INGESTION-LOG.md would show "error" on every read until GH #394 is resolved. The improvement's benefit is best realized once the brain is healthy. SMS Dashboard label fix (Idea 1) has higher immediate impact.

## Deferred to

Parking lot carry-forward. Implement in run 82 or after GH #394 is resolved.

## Implementation

In `.claude/skills/subconscious/SKILL.md` Phase 2 evidence block, after existing `tail -20 ops/routines/logs/...` line:

```
- Run: tail -10 brain/INGESTION-LOG.md
  Purpose: Detect brain connector failures before ideation. If last 3 entries show errors → note "brain stale since [date]" in evidence digest.
```
