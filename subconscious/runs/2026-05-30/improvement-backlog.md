# Improvement Backlog — 2026-05-30 (Run 41)

## Active

- **Invoke /god-class-splitter on email_sequences.py** — split 1255L into email_crud + email_enrollment + email_processor. All prerequisites met (god-class-splitter SKILL.md + post-split-test-repair SKILL.md both exist). Run 35 active_direction. ~2h effort.

## Parking Lot (survived debate or not chosen)

- **AUTONOMOUS-EXECUTABLE labels for moratorium Items A + D** — add labels to `subconscious/runs/2026-05-21/winning-concept.md`. Items A (3-line pre-commit addition, same class as 061582c Check 11) and D (new YAML, same class as SKILL.md additions). WEAKENED: governance grey area between "labeling scope" and "authorizing bypass." Revisit if /moratorium-sprint remains uninvoked through run 42.

- **/moratorium-sprint (standing action)** — Items A/B/D, ~40 min, exits moratorium. Tool ready (7985fbb). 13+ consecutive recommendations without invocation. Highest-priority action before or alongside email_sequences split. Invoke in same session as split if possible.

- **AI-to-Human Handoff v1** — Run 38 winner, 44+ days oldest pending. Agent OS outbound ready (os_outbound_mirror.py). ~1 day. WEAKENED: no new evidence since run 38. Next recommendation after email_sequences split.

- **GH #112/#113 N+1 fixes** — After email_sequences split scopes these to single modules.

## Rejected This Run

- **Idea 4 (GH #181 via AUTONOMOUS-EXECUTABLE)** — In rejected_paths. Check 11 daily warning adds partial new evidence, but the fix requires MEDIUM-risk test modification. Human required. Not re-opened as winner.

- **Idea 5 (AI-to-Human Handoff as winner)** — WEAKENED (not killed). Valid idea, no new evidence since run 38. 9th recommendation without implementation without new evidence wastes winner slot.

## Questions for Next Run

1. Was email_sequences.py split executed? (`wc -l backend/routers/email_crud.py backend/routers/email_enrollment.py backend/routers/email_processor.py`)
2. Was GH #181 billing fix implemented? (Check 11 WARNING should stop firing after fix)
3. Were moratorium Items A/B/D executed? (`grep check_project_invariants scripts/hooks/pre-commit`, `ls scripts/check-widget-sync.sh`, `ls .github/workflows/lead-qualifier-eval.yml`)
4. Did GH #112/#113 get updated with new module scope? (post-split)
5. Is the moratorium now lifted? (pending_approvals <= 2)
