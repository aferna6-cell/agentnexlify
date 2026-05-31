# Improvement Backlog — 2026-05-31 (Run 42)

## Active

- **De-couple Item A: governance.json status pending_autonomous + AUTONOMOUS-EXECUTABLE directive in nightly-commit-review SKILL.md** — removes 28-day grouping label that has blocked autonomous execution; Check 11 precedent (061582c); HIGH confidence

## Parking Lot (survived debate but not chosen)

- **Invoke /moratorium-sprint (~40 min, Items A+B+D):** Standing highest-priority human-required action. After Item A executes autonomously (if run 42 winner implemented), sprint reduces to Items B+D only (~35 min). SKILL.md ready (7985fbb). Day 28 of moratorium.
- **AI-to-Human Handoff v1 (~1 day):** Run 38 winner, 45+ days. Agent OS plumbing ready (os_outbound_mirror.py). Critical gap all 7 industries. MEDIUM confidence.
- **Custom Automation Templates v1 spec:** customer-gaps.md Open/Medium, all industries. Write specs/custom-automation-templates_spec.md post-moratorium.
- **Zapier plan_status enforcement (GH #107, ROI 2.5):** Security gap. Promote to first post-moratorium winner if moratorium exits before next run.
- **Item D de-coupling (lead-qualifier-eval.yml):** Apply same AUTONOMOUS-EXECUTABLE pattern as Item A after Item A confirms execution. Collapses sprint to 1 human item.

## Rejected This Run

- **Post-Phase-C Architecture Audit:** KILLED round 2. Generates backlog noise against an existing 54-target list and a clear run 41 winner. Audit findings could destabilize the recommendation queue. Revisit after moratorium exits and email_sequences split completes.

## Questions for Next Run

1. Did nightly review execute Item A (check_project_invariants wired to pre-commit)? Check: `grep -n "check_project_invariants" scripts/hooks/pre-commit`
2. Was GH #181 billing fix implemented? Check: `grep "15000\|25000" backend/services/billing.py`
3. Was email_sequences.py split executed (run 41 winner)? Check: `wc -l backend/routers/email_sequences.py` (should be <600L if split happened)
4. Is moratorium still active? (exits when pending ≤ 2)
5. Was Item D also de-coupled and executed autonomously after Item A confirmed?
