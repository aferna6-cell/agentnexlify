# Agent OS — What To Do Next

Source spec: `specs/agent-os-overhaul_spec.md`.
Branch: `claude/agent-os-grill-resume-cHznV` (isolated long-lived; no merge to
`main` until full OS done). PR #177 stays a draft.

## State now (2026-05-22)

Shipped on branch:

- **P0 foundation** — orchestrator routing (`answer`/`delegate`/`backlog`),
  semantic memory, chat shell, agent-run flowchart, no-fit backlog, usage
  metering. Migrations 118-123 (`os_*` tables).
- **P1-P4 workers** — `backend/services/os_workers/` registry package, 5
  workers auto-discovered: `customer_question`, `booking`, `lead_nurture`,
  `campaign`, `generalist`.
- **MVP demo + regression test** — `tests/test_os_mvp_e2e.py` (commit
  `b08c7a1`). Drives full loop: orchestrate -> delegate -> run_worker ->
  deliverable -> reply. 115 OS tests pass.

MVP is working end-to-end with at least one agent (`customer_question`) ready.

## Next steps — ranked

### 1. Connector groups A / B / C (parallel)

Each connector group is its own spec + plan + build agent. Fan out only after
deciding group boundaries. Per P0 plan, connectors depend on the spine and run
in parallel post-P0.

- **Group A — inbound channels** — widget chat, email, SMS feed into
  `os_threads`. Spec: `specs/agent-os-connectors-inbound_spec.md`.
- **Group B — action connectors** — booking calendar, CRM lead write,
  campaign send. The workers currently produce deliverables; connectors turn
  approved deliverables into real-world effects. Spec:
  `specs/agent-os-connectors-actions_spec.md`.
- **Group C — data sync** — pull tenant data (leads, appointments, KB) into
  `os_memory_entries`. Spec: `specs/agent-os-connectors-sync_spec.md`.

Each: run `grill-me` -> `write-prd` -> `prd-to-plan` -> build. Do NOT start a
connector group without its spec.

### 2. Graph-memory re-decision (deferred from P0)

P0 dropped the Karpathy graph layer (entity pages/edges) — semantic memory
only. P0 plan decision #2: "Graph layer is re-decided at end of P1." P1 is now
done. Decision input needed:

- Cost: graph layer = one LLM call per memory write (entity-page update).
- Benefit: cross-thread entity recall vs flat semantic retrieval.
- Action: measure semantic-only recall quality against real tenant threads
  first. If recall is adequate, keep graph cut. If not, scope graph as P5.

This is a decision, not a build task — produce
`planning/decisions/2026-MM-DD-agent-os-graph-memory.md`.

### 3. Phase C — pre-merge cleanup (SEPARATE SESSION)

Per P0 plan: Phase C runs LAST as a separate audit-only session. Do not audit
and fix in the same session (half-finished-refactor risk). Phase C gates the
`main` merge. Cleanup scope is whatever the audit produces.

### 4. Pre-existing CI rot — NOT part of the rehaul

PR Validation on #177 fails on 21 pre-existing test failures inherited from
`origin/main`, not branch regressions. Proof: main worktree = 21 failed / 524
passed; branch = 21 failed / 647 passed (same 21, +123 passing, zero new
failures). The branch also fixes a broken test collection on main
(`test_local_seo_parsers.py` imports `_strip_json_fences`, missing from main's
`local_seo.py`; branch adds it).

Root cause of the 21: `call_claude_messages` patch-target mismatches in
`tests/test_local_seo.py`, `tests/test_retry_policy.py`,
`tests/test_onboarding_ai_paths.py`, `tests/test_auth_endpoints.py`. Routers
were refactored to delegate AI calls to handler services; tests still patch the
old router-level symbol.

Action: file a separate GitHub issue for the 21 failures. Out of scope for the
Agent OS rehaul — fixing them here would mix unrelated concerns into the merge.

## Sequencing

```
NOW: MVP working, P0-P4 on branch
  |
  +-- Connector groups A/B/C  (parallel, each own spec + agent)
  +-- Graph-memory decision   (end of P1 -> now; decision doc)
  |
  v
Phase C cleanup  (separate audit-only session)
  |
  v
Merge branch -> main  (PR #177 leaves draft)

Out of band: GH issue for 21 pre-existing CI failures (NOT in rehaul)
```

## Cross-refs

- `specs/agent-os-overhaul_spec.md` — authoritative spec
- `plans/agent-os-p0_plan.md` — P0 build plan + Phase C definition
- `tests/test_os_mvp_e2e.py` — MVP demo + regression test
