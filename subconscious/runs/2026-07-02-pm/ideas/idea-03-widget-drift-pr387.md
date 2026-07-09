# Idea 03: Recommend Merging PR #387 (Widget Drift Fix)

**Category:** code_health  
**Effort:** XS (PR review + merge, 5 min human)  
**Moratorium impact:** HUMAN-REQUIRED — counts toward human queue  
**Autonomous:** NO — PR merge requires human

## Evidence

- `check_project_invariants.py` exits 1: widget/agentnexlify-widget.js != landing-page-v2/widget/agentnexlify-widget.js
- PR #387 "brain: sync Maps to 2026-07-01 reality + fix landing-page-v2 widget drift" — open 1 day
- Morning digest: "MERGE #387 — fixes Check 13 widget drift FAIL"
- Title "fix landing-page-v2 widget drift" — directly addresses Check 13 FAIL

## Why KILLED in debate

**Governance constraint:** Widget drift topic RETIRED from subconscious (governance.json `widget_drift_topic_retired: true`). Reason: 6-run delivery failure chain (runs 65-70). Subconscious is forbidden from debating widget drift fixes — this is human-only territory.

Even framed as "recommend merging a PR that happens to fix widget drift", this violates the retirement constraint. The subconscious should not spend a winning recommendation slot on a topic it has been explicitly barred from.

**Morning digest already covers this**: the human-facing report already flagged PR #387 for merge. Subconscious adding a recommendation on top is redundant.

## Score

| Dimension | Rating |
|-----------|--------|
| Evidence quality | HIGH — PR open, check confirmed fail |
| Impact | MEDIUM — restores Check 13 to PASS |
| Effort | XS |
| Novelty | ZERO — morning digest already flagged |
| Governance | KILLED — widget_drift_topic_retired constraint |

**Total: KILLED — governance retirement constraint + zero novelty**
