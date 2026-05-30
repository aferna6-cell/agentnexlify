# Improvement Backlog — 2026-05-30-pm (Run 42)

## Active

- **GH #181 → /god-class-splitter on email_sequences.py** — GH #181 billing fix first (~15 min), then split (~2h). All prerequisites met. Run 35+41 active_direction. Human present in session. Implementation sketch in winning-concept.md.

## Parking Lot (survived debate or not chosen)

- **AUTONOMOUS Item A — check_project_invariants pre-commit (Check 12)** — 9-line bash addition to scripts/hooks/pre-commit. Spec written in winning-concept.md §Parking Lot. Pending: nightly-commit-review SKILL.md must extend scope to pre-commit additions before nightly can execute. Precedent: 061582c added Check 11 autonomously (22 lines). Revisit run 43 with explicit scope extension.

- **AUTONOMOUS Item D — lead-qualifier-eval.yml** — Spec written in winning-concept.md §Parking Lot. Pending: nightly scope extension to .github/workflows/ creation. Alternatively: execute manually as part of moratorium sprint (~20 min). Closes GH #110.

- **/moratorium-sprint (standing action)** — Items A/B/D, ~40 min, exits moratorium. Tool ready (7985fbb). 13+ consecutive recommendations without invocation. Execute in same session as email_sequences split if possible.

- **auth.py god-class split** — 1591L, LARGEST router file, bigger than email_sequences. Security-critical (JWT, sessions, OAuth). Next god-class target AFTER email_sequences validates the process. Use /god-class-splitter when email_sequences is complete.

- **GH #112/#113 N+1 fixes** — After email_sequences split scopes these to email_processor.py.

- **AI-to-Human Handoff v1** — Run 38 winner, 44+ days. Agent OS outbound ready (os_outbound_mirror.py). ~1 day. No new evidence since run 38.

## Rejected This Run

- **Idea 3 (auth.py split planning as winner)** — KILLED: wrong timing. Split must be validated on email_sequences first. Security-critical code needs security-reviewer pass. Not atomic enough as a planning-only recommendation.

- **Idea 4 (AUTONOMOUS Item D) as winner** — WEAKENED to parking lot: 2-step prerequisite chain (nightly scope extension required before workflow creation). Same blocking pattern as post-split-test-repair delay.

## Questions for Next Run

1. Was GH #181 billing fix implemented? (`grep "15000.*autopilot" backend/routers/billing.py`)
2. Was email_sequences.py split executed? (`ls backend/routers/email_crud.py`, `wc -l backend/routers/email_enrollment.py`)
3. Were moratorium Items A/B/D executed? (check_project_invariants in pre-commit, check-widget-sync.sh, lead-qualifier-eval.yml)
4. Is the moratorium now lifted? (pending_approvals ≤ 2)
5. Was nightly-commit-review SKILL.md extended to cover pre-commit additions and .github/workflows/ YAML creation?
