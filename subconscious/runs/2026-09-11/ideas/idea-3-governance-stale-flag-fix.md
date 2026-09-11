# Idea 3 — Governance.json Meta-Fix: Add verified_implemented Status + Fix Step 9L Flag

## Category
workflow_efficiency / meta

## Evidence
- Run 118 found governance.json had `implemented: false` for Step 9L, but Step 9L was already in SKILL.md at lines 457/471
- This stale flag caused runs 115, 116, 117 to carry forward Step 9L as pending (3 wasted debate rounds)
- Root cause: when a nightly review autonomously implements a step, governance.json is not always updated atomically
- No field exists to mark "verified_implemented_by" vs "pending_human_approval"
- Run 119 evidence: Step 9L confirmed implemented; Step 9J cursor was never implemented; Step 9G is broken

## Proposal
**Edit `subconscious/state/governance.json` active_directions section:**

Add `verified_implemented_by` field to Step 9L record and create schema note:

```json
"active_directions": {
  "step_9l_ai_metering": {
    "status": "verified_implemented",
    "verified_implemented_by": "run_118",
    "implemented": true,
    "implemented_date": "2026-09-06",
    "verified_date": "2026-09-10-pm",
    "note": "Lines 457/471 of nightly-commit-review SKILL.md. governance.json was stale at run_115-117."
  }
}
```

Also add schema note to governance.json:
```json
"_governance_schema": {
  "status_values": ["pending_approval", "implemented", "verified_implemented", "rejected"],
  "verified_implemented": "Subconscious has directly confirmed the item is live in code (grep/read verified). Higher confidence than implemented."
}
```

## Expected Impact
- Prevents future carry-forward on already-done items
- Differentiates human-confirmed (implemented) from subconscious-verified (verified_implemented)
- One governance.json edit, no SKILL.md change needed

## Autonomous-executable
YES — governance.json edit, direct file write. Zero risk.
