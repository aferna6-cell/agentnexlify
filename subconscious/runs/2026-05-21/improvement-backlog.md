# Improvement Backlog — 2026-05-21 (Run 28)

## Active

- **Invoke /moratorium-sprint (3 items A+B+D)** — one command, ~40 min, exits moratorium. Phase 6 governance audit this run clears count to 4; sprint brings to 2 = exit.

## Parking Lot (survived debate but not chosen)

- **AI-to-Human Handoff v1** — first post-moratorium winner. Critical gap all 7 industries, 35 days pending. M-effort (~1.5-2 days). Authorization unclear during moratorium; promote after sprint PR merges. Sketches in subconscious/runs/2026-05-17/winning-concept.md.
- **Zapier plan_status security enforcement (GH #107)** — cancelled tenants bypass tier gate. S-effort, 30 min. Can be done independent of moratorium. ROI 2.5. Route via issue-to-pr-loop.
- **Sprint sentinel UserPromptSubmit hook** — auto-prepend moratorium note at session start when sprint items pending. Promote to run 29 if sprint still not invoked.
- **pre-commit-guard-add skill** — parking lot from run 26. Promotes after moratorium exits.

## Rejected This Run

- None formally killed — Idea 4 (Zapier) and Idea 5 (sentinel hook) not debated (out of top 3); both valid parking lot items.
- AI-to-Human Handoff: WEAKENED (not killed) — authorization ambiguous mid-moratorium. Post-moratorium priority maintained.

## Questions for Next Run

1. Was /moratorium-sprint invoked? If yes: what's the real pending count after PR merge? If no: what's the blocker (time, knowledge, willingness)?
2. Is the governance audit (pending 12→4) visible in governance.json after this run's Phase 6? Does the new count match the exit map?
3. Post-moratorium: should AI-to-Human Handoff be scoped into the issue-to-pr-loop immediately, or does it need a /grill-me + /write-prd pass first?
4. Are safe dep PRs #102/#103/#164/#171 still open? If so, they're a 5-minute win at any time.
