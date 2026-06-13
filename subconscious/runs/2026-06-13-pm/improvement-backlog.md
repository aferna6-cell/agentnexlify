# Improvement Backlog — 2026-06-13-pm

## Active
- **Wire check_project_invariants.py to pre-commit as Check 10** (run 8 winner, 50 days, AUTONOMOUS-EXECUTABLE)
  — blocked condition cleared by PR #257; nightly executes tonight

## Parking Lot (survived debate, not chosen)

- **Create check-widget-sync.sh + wire to pre-push** (run 7, pending_autonomous) — valid,
  deferred. check_project_invariants.py already monitors widget byte-identity; pre-push
  enforcement adds another layer. Propose run 59 if Check 10 wires successfully tonight.

- **AI-to-Human Handoff v1** (run 4, 60+ days, Critical customer gap) — WEAKENED this run due
  to launch-sprint stabilization context. Becomes #1 post-sprint priority. Infrastructure
  exists: os_outbound_mirror.py (152 tests), Agent OS fully merged, conversation_notify.py
  shipped. Scope ~1 day.

- **email_sequences.py /god-class-splitter** (run 41, 14+ days) — WEAKENED this run due to
  sprint timing. GH #181 prerequisite CLEARED. Tooling ready (god-class-splitter +
  post-split-test-repair SKILL.md). First post-sprint candidate after AI-to-Human Handoff.
  GH #112/#113 N+1 issues addressed by split.

- **Fix kb-autopopulate.sh fallback** (runs 52/53/54) — KB automation broken 35+ days.
  Add `which agent-browser || use WebFetch MCP` fallback. Propose when operational run is
  appropriate.

## Rejected This Run

- **AI-to-Human Handoff as run 58 winner** — WEAKENED to parking lot (not killed). Wrong
  sprint timing (launch-readiness stabilization + adjacent PRs #255/#256 still settling).
  Not added to rejected_paths — valid item, preserve for post-sprint.

- **email_sequences.py split as run 58 winner** — WEAKENED to parking lot (not killed).
  High-velocity sprint = wrong window for M-effort refactor.

## Governance Corrections Applied This Run
1. Run 57 (widget sync): pending_autonomous → **implemented** (PR #257)
2. Run 55 (from __future__ + em-dashes): pending_autonomous → **implemented** (PR #257)
3. Run 56 (Check 13): pending_autonomous → **partially_implemented** (CHECK 2 tightened in PR #257)
4. Run 51 (billing PR #183): pending_approval → **implemented** (PR #255 ca718ab)

## Questions for Next Run
1. Did Check 10 wire successfully tonight (grep scripts/hooks/pre-commit for check_project_invariants)?
2. Has any new invariant violation appeared post-PR #257 (check_project_invariants.py exits 0)?
3. Is the launch-readiness sprint winding down — can AI-to-Human Handoff begin?
4. Was email_sequences.py split attempted post-sprint?
5. Did check-widget-sync.sh get created as autonomous bonus?
