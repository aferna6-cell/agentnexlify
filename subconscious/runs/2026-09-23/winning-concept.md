# Winning Concept — 2026-09-23 (Run 127)

**Winner:** Step 9E P0 Tier — Add 10-Day Credential Expiry Escalation
**Category:** Operational
**Carry count:** 7 (autonomous-executable since run 122)
**Status:** Recommend (task-prompt constraint: "Do NOT implement. Only recommend.")

---

## Recommendation

Add a `days_remaining <= 10` P0 escalation branch to Step 9E in `.claude/skills/nightly-commit-review/SKILL.md` that fires a dedup-guarded GH issue with `p0` + `human-action-required` labels and a structured nightly log entry.

---

## Why This, Why Now

AUTOPILOT_GH_TOKEN expires 2026-10-02 — 9 days from today. GH #893 was filed ad-hoc by yesterday's nightly, proving the need exists. The current Step 9E threshold fires at 76 days (14-day warning window) but provides no escalation as the expiry deadline approaches. Without a P0 tier, the nightly log entry stays identical whether a credential has 75 days or 1 day remaining. A human scanning the log at 9 days-to-expiry gets no stronger signal than at 75 days. Adding the P0 branch makes the urgency machine-readable and permanent — tonight's nightly would fire it for AUTOPILOT_GH_TOKEN, and every future credential will benefit automatically.

---

## Implementation Sketch

In `.claude/skills/nightly-commit-review/SKILL.md`, Step 9E block, after the existing `approaching_expiry (days_since_rotation >= 76)` branch, add:

```
4. **P0 Escalation (days_remaining <= 10):**
   - Compute days_remaining = (rotation_interval_days - days_since_rotation)
   - If days_remaining <= 10 AND days_remaining > 0:
     a. Search for existing open GH issue with title containing credential name + "expires"
     b. If NONE found: create GH issue:
        - title: "P0: {credential_name} expires in {days_remaining} days — rotate NOW"
        - labels: ["p0", "human-action-required", "ops"]
        - body: credential name, last_rotated date, expiry date, rotation steps from schedule
        - log: "Step 9E: P0 ALERT — {credential_name} expires {days_remaining} days. GH #{number} filed."
     c. If FOUND: log "Step 9E: P0 dedup skip — GH #{number} exists for {credential_name}."
   - If days_remaining <= 0:
     - log: "Step 9E: EXPIRED — {credential_name} may have expired {abs(days_remaining)} days ago. Manual rotation required."
```

Total change: ~12 lines of instruction added to existing Step 9E block. No new files, no migrations, no code changes.

---

## What This Replaces

Previous active direction: Step 9G gh→MCP fix (run 126) — IMPLEMENTED by nightly-2026-09-23. Run 127 free to pick new direction.

Step 9E P0 tier continues as the single most carried non-autonomous-implementable direction (7 carries). GH #893 is the ad-hoc analog of what this would do systematically.

---

## Confidence

**HIGH** — Evidence is direct (AUTOPILOT_GH_TOKEN at 9 days, GH #893 proves pattern), action is atomic (12-line SKILL.md edit), blast radius zero, mechanism identical to Steps 9C/9E/9F/9G/9I/9J/9K/9L (all in SKILL.md, all working). Debate verdict: SURVIVES.

---

## Escalation Status

This is the 7th carry. Autonomous-executable since run 122.

Per governance precedent (Steps 9F/9G/9I/9J/9K/9L all implemented at 3rd carry):
- Run 122 mandate authorized autonomous implementation
- Runs 122–126 task-prompt constraint "Do NOT implement" overrode escalation
- Run 127 same constraint applies
- Implementation when constraint is lifted: direct SKILL.md edit per this sketch

**AUTOPILOT_GH_TOKEN expires 2026-10-02. Human action required. See GH #893.**
