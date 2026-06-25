# Improvement Backlog — Run 67 (2026-06-25-pm)

## ACTIVE (pending_approval, moratorium blocks new additions)

### [RUN 65] Fix Widget Drift + Em-Dash Violations
- Status: pending_approval (AUTONOMOUS-EXECUTABLE label)
- Effort: S
- Blocked by: nightly scope mismatch → NOW ESCALATED to human interactive execution
- See: subconscious/runs/2026-06-23/winning-concept.md

### [RUN 66] Add Step 9B to nightly-commit-review SKILL.md
- Status: pending_approval (AUTONOMOUS-EXECUTABLE label)
- Effort: S
- Blocked by: editing existing SKILL.md not in nightly scope → NOW ESCALATED with run 65
- See: subconscious/runs/2026-06-25/winning-concept.md

---

## RUN 68 CANDIDATE (after Check 13 exits 0)

### Plan-Name Invariant Guard (Check 7 in check_project_invariants.py)
- Confidence: HIGH
- Autonomous-executable: YES
- Prevents GH #292/#293-class bugs at next repricing event
- Pattern: scan gate dicts for retired plan names (foundation, operations)
- Effort: S (~20 lines)
- Blocked until: check_project_invariants.py exits 0

---

## PARKING LOT

### KB Autopopulate Fix
- Replace agent-browser CLI calls with curl/WebFetch in scripts/daily/kb-autopopulate.sh
- KB stale 50+ days
- Parking lot ROI: 1.8
- Not urgent — no invariant failure, no commit block
- Target: run 68 or 69 after moratorium exits

### AI-to-Human Handoff v1 (Run 4)
- Day 70 without implementation
- M-effort, requires human UX design decisions
- Moratorium-blocked until cleanup sprint runs
- Target: post-moratorium, multi-session human-guided

### email_sequences.py split (~1143L god class)
- Rule 9 violation: >600 lines, needs factoring
- M-effort, human required (blast radius unknown without gitnexus)
- Parking lot until AI-to-Human Handoff delivered (sequencing dependency)

---

## CLEANUP SPRINT (unblocks moratorium exit)

Runs 20, 21, 29, 42, 50 — marked implemented but governance not updated.
~1h of audit + status flips.
When done: true_pending drops from ~6 to ~1, moratorium exits.

---

## FROZEN (do not revisit)
- Zapier integration pattern (frozen indefinitely)
- White-label subdomain routing (frozen pending enterprise customer)
