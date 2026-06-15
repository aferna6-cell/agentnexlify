# Improvement Backlog — 2026-06-15-pm

## Active
- **Update Check 11 + Wire Check 10** — Update REQUIRED_AMOUNTS in pre-commit Check 11 to {1999, 9999}
  (two-plan repricing); add Check 10 block calling check_project_invariants.py as FAIL gate.
  (run 58 winner, AUTONOMOUS-EXECUTABLE)

## Parking Lot (survived debate but not chosen)

- **JWT stale plan/role claims (M3)** — Launch audit deferred this; with pay gate live a cancelled
  user keeps paid-tier access for 24h. Approach: reduce JWT TTL from 24h → 4h (S-effort, config
  change only) rather than per-request DB read. Promote when JWT auth work is scheduled.

- **AI-to-Human Handoff v1** (run 4 / run 38 active directions, 60+ days) — os_outbound_mirror.py
  ready (PR #188). With pay gate live, churn from unhandled complex queries costs real revenue.
  Moratorium governance rule: do not re-recommend as winner until moratorium exits or explicit human
  escalation. Run 38 remains the canonical active direction.

- **Cross-tenant isolation test for os_graph_memory.py** (ROI 2.1) — 2 tests: accumulate_from_turn
  for client A, then graph_kb_entries for client B → empty. 284 mocks but no cross-tenant coverage.

- **Home.jsx god-class split (1171L)** — CLAUDE.md Rule 9 threshold exceeded. Extract HeroSection,
  FeaturesSection, PricingSection into components/home/. Promote when a landing-page sprint starts.

- **email_sequences.py split (1143L)** — 3 clean concerns (CRUD/enrollment/processor). Run 41 active
  direction. Human-required (~2h). Promote when moratorium exits.

- **Fix kb-autopopulate.sh** (broken 35+ days) — agent-browser CLI not installed. Replace with curl
  or silent skip. Knowledge base stale.

## Governance Corrections Applied This Run
- Run 55 (channels_instagram from __future__ + em-dashes): pending_autonomous → implemented (3234597)
- Run 56 (Check 13 from __future__ guard): pending_autonomous → implemented (3234597; Check 2 covers)
- Run 57 (widget sync drift): pending_autonomous → implemented (3234597)
- GH #181 related items (runs 31/32/34, pending_approval): superseded by two-plan repricing (PR #288)
- Run 51 (PR #183 merge, billing fix): superseded by two-plan repricing
- Run 22/42 (Item A de-couple/wire Check 10): subsumed by run 58 winner

## Questions for Next Run
1. Did nightly implement Check 11 update + Check 10 wire? Check: `bash scripts/hooks/pre-commit` —
   should show "Check 10: Project invariants... OK" and "Check 11: Billing constant guard... OK"
2. Is moratorium count reduced? How many items remain in pending_approval vs pending_autonomous?
3. Has AI-to-Human Handoff (run 38) been implemented? Check: widget_chat.py for handoff trigger.
4. Any new from __future__ violations in the next sprint? (Check 2 in pre-commit guards this.)
5. What's the PR velocity post-launch? More PRs = more invariant violations need catching.
