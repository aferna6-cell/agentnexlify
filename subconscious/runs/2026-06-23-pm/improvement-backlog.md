# Run 65 Improvement Backlog — 2026-06-23-pm

## Winner (this run)
- **Check 7 plan-name guard in check_project_invariants.py** — AUTONOMOUS-EXECUTABLE, pending_autonomous

## Active pipeline (pending_autonomous — nightly can implement)
- **Check 7** (this run winner) — highest priority
- **check-widget-sync.sh** (run 7/50 active_direction) — widget 3-copy guard, still pending_autonomous

## Active pipeline (pending_approval — human required)
Note: these have been accumulating. True pending estimate ~7 post-correction.
Key human-required items (by priority):
1. **email_sequences.py god-class split** (run 41, 1143L) — /god-class-splitter, M-effort ~2h
2. **AI-to-Human Handoff v1** (run 38, run 4) — Critical gap all industries, ~1.5 days
3. **Governance cleanup** — mark runs 20/21/28/29/30/31/36 as superseded/absorbed (reduces true pending count, exits moratorium)

## Parking lot (future run candidates)
- **Fix kb-autopopulate.sh** (run 63/53) — ROI 1.8, rewrite to use WebFetch instead of agent-browser CLI. Valid S-M effort. Run 66 candidate.
- **Migration object-existence audit script** (from GH #263 triage) — ROI 2.0, deterministic Supabase object check vs naive number-diff. Run 66 candidate.
- **Home.jsx god-class split** (1006L) — human-required, M-effort. Post-email_sequences.
- **Cross-tenant isolation tests for os_graph_memory** — ROI 2.1, parking lot since run 54.
- **Schema-discipline New-Table Checklist** — ROI 1.9, parking lot since run 61.

## Killed this run
- **CAN-SPAM physical address** — operator task (Instantly.ai campaign config), not a code artifact. Flagged as operator checklist item. Not a subconscious winner candidate.

## Operator checklist (not code — human action required)
- Add physical mailing address to Instantly.ai cold-outreach campaign body (CAN-SPAM compliance, required before July 10 launch)

## Governance state after run 65
- `total_runs`: 65
- `moratorium_active`: true (true_pending ~7, still > max_pending_approvals=2)
- `moratorium_override` items: BOTH CLEARED (GH #292/#293 + GH #308 implemented 2026-06-23)
- New winner: AUTONOMOUS-EXECUTABLE → pending_autonomous, does not worsen moratorium
- Moratorium exit path: implement ~5 of the pending_approval items (or apply governance corrections that mark stale ones superseded)
