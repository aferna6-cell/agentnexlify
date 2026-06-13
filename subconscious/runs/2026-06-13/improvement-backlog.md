# Improvement Backlog — 2026-06-13

## Active
- **Fix widget sync drift** — cp widget/agentnexlify-widget.js to landing-page-v2/widget/ (run 57 winner, AUTONOMOUS-EXECUTABLE, fixes live Critical Invariant #4 violation from PR #254)

## Parking Lot (survived debate but not chosen)

- **Add Check 13 to pre-commit** (run 56 winner, still pending_autonomous) — extend `from __future__ import annotations` guard from router-only (CHECK 2) to all `backend/**/*.py`. 10-line bash insertion after Check 12. AUTONOMOUS-EXECUTABLE. Weakened this run: CHECK 2 provides partial coverage; widget drift was more urgent new finding. Still valid for a future nightly run.

- **Fix em-dash violations + from __future__ actual imports** (run 55 winner, still pending_autonomous) — 10 JSX em-dash substitutions + remove from __future__ from 3 router files. PR #254 added 3 new violations (DemoBanner.jsx:4/7, Sidebar.jsx:386) expanding the target list. Killed as run 57 winner (run 55 already queued); remains autonomous-executable.

- **Fix kb-autopopulate.sh** (parking lot ROI 1.8, 35+ days broken) — agent-browser CLI not installed, twice-daily KB population offline. Replace with WebFetch/curl fallback or silent skip. Promote when a sprint explicitly targets knowledge-base quality.

- **Cross-tenant isolation test for os_graph_memory.py** (parking lot ROI 2.1) — 2 tests confirming client_id=A data not visible to client_id=B queries. os_graph_memory.py (397L) has 284 mocks but no cross-tenant isolation test. Killed this run for insufficient new urgency signal.

## Rejected This Run
- **Idea 3 as winner (em-dash + from __future__)** — KILLED. Run 55 already covers this; would create duplicate pending items for same fix class without adding new value.
- **Idea 5 as winner (os_graph_memory cross-tenant test)** — KILLED. No new evidence since run 54 parking lot addition. Widget drift is higher priority.

## Questions for Next Run
1. Did nightly implement widget sync fix (cp command)? Check: `diff widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js`
2. Did nightly implement run 55 fix (em-dash + from __future__)? Check: `python3 scripts/check_project_invariants.py` — should exit 0 if widget + em-dash + future all fixed
3. Did nightly implement Check 13 (run 56)? Check: `grep "Check 13" scripts/hooks/pre-commit`
4. What new code shipped in the next 3-day window? Any new from __future__ violations, widget changes, or em-dashes?
5. Status of PRs #183 (billing), #209 (security), #200 (autonomous chain) — still unmerged?
