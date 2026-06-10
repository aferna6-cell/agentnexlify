# Winning Concept — 2026-06-10

## Recommendation

Fix 3 JSX em-dash violations introduced by c8a0460 in MemoryPanel.jsx:180 + AgentOS.jsx:197/224 — restoring check_project_invariants exit 0 and unblocking autonomous Item A (Check 10 pre-commit wire) tonight.

## Why This, Why Now

`c8a0460` (Agent OS knowledge graph, landed 2026-06-10) re-introduced 3 em-dash violations in new UI copy. `check_project_invariants.py` now exits 1 — the exact blocker that stalled Item A (check_project_invariants Check 10 wire) for 28+ days before run 49 cleared it. The nightly autonomous channel for em-dash fixes is confirmed (8db33df fixed 5 violations on 2026-06-05; same mechanism). Once exit 0 is restored, Item A has no remaining blockers: `governance.json` marks it `pending_autonomous`, `autonomous_executable: true`, and the nightly SKILL.md already covers pre-commit bash additions (4226ef4). This is the last manual step before Check 10 enters the pipeline as a permanent guard — after which future em-dash violations are caught at commit time and never recur.

## Implementation Sketch

1. **File:** `frontend/src/components/os/MemoryPanel.jsx` — find line 180, replace em dash (—) with hyphen (-) in the UI string
2. **File:** `frontend/src/pages/AgentOS.jsx` — find line 197, replace em dash with hyphen
3. **File:** `frontend/src/pages/AgentOS.jsx` — find line 224, replace em dash with hyphen
4. **Verify:** `python3 scripts/check_project_invariants.py` — must exit 0, `1 invariant(s) failed` should be gone
5. **Commit** with message: `fix: replace em dashes with hyphens in Agent OS UI copy (personality.md rule)`
6. **Tonight nightly** (2:37 AM) auto-executes Item A: adds `check_project_invariants.py` call as Check 10 to `scripts/hooks/pre-commit`

## What This Replaces

Previous active direction was run 53 winner (os_action_dispatch tests) — now IMPLEMENTED by c6805a5. This run advances the moratorium exit sequence by clearing the check_project_invariants pre-condition again.

## Confidence

HIGH — same mechanism as run 49 winner (8db33df, 5 violations fixed autonomously). Bounded scope (3 specific lines, confirmed by direct script run). Autonomous channel active (Check 12 added by nightly same channel same night). Item A governance label already set to `pending_autonomous / autonomous_executable: true`.

## Governance Notes

- Run 53 status: `pending_autonomous → implemented` (c6805a5, nightly 2026-06-10)
- `runs_implemented`: 15 → 16
- New em-dash violations introduced by c8a0460 in Agent OS UI — same pattern as pre-run-49 violations; fix is the same class

## Standing Actions (not this run's winner, but still critical)

- **Merge PR #183** (~10 min): billing.py still missing 15000→autopilot + 25000→professional (17d draft PR). Condition (b) met per run 51 framing: path confirmed (backend/routers/billing.py:263), PR exists.
- **Item B (check-widget-sync.sh)**: still MISSING after 46 days. pending_autonomous but never executed by nightly. Consider explicit inline implementation in next interactive session.
- **email_sequences.py split** (1255L): unblocked once GH #181 resolved.
