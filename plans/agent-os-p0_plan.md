# Agent OS — P0 Foundation Build Plan

Source spec: `specs/agent-os-overhaul_spec.md` (authoritative).
Branch: `claude/agent-os-grill-resume-cHznV` (isolated long-lived; no merge to
`main` until the full OS is done).

P0 is the spine. P1–P4 (workflow agents) and the connectors depend on it, so it
ships first and alone. After P0 lands, P1–P4 + connector groups fan out in
parallel.

## P0 scope

Orchestrator routing, semantic memory, chat shell, agent-run flowchart, no-fit
backlog, usage metering. No workflow agents yet — P0 proves the orchestrator →
agent-run → deliverable → memory loop with a single stub worker.

### Confirmed decisions (2026-05-21)

1. **`os_` prefix on every new table** — `os_threads`, `os_messages`,
   `os_agent_runs`, `os_memory_entries`, `os_backlog_requests`,
   `os_tenant_usage`. Avoids collision with existing `agent_runs`-style names.
2. **Semantic memory only in P0** — the Karpathy graph layer (entity
   pages/edges) is dropped from P0. Rationale: the graph layer is the API-cost
   driver (an LLM call per memory write to update entity pages); the semantic
   layer is cheap (one embedding per write, free pgvector retrieval). The spec
   already marks graph the cut candidate (§Memory architecture, Open Questions).
   Graph layer is re-decided at end of P1.
3. **Migrations written to `migrations/` AND applied via Supabase MCP.**
4. **Async agent runs via FastAPI `BackgroundTasks`** — proves the real
   async post-back path (worker writes status/result back to `os_agent_runs` +
   `os_messages`) that P0 must de-risk. No external queue in P0.

## Build order

1. **Schema** (migrations 118+) — must land before any router.
2. **Backend** — services + routers, registered in `main.py`.
3. **Frontend** — chat shell + side-panel editor + flowchart, against the
   spec's API Surface.

Backend and frontend touch disjoint directories — built concurrently, but
frontend codes against the spec's documented API contract.

## Migrations (next free number: 118)

| File | Table |
|---|---|
| `118_os_threads.sql` | `os_threads` + `(client_id,status)` index + RLS |
| `119_os_messages.sql` | `os_messages` + `thread_id` index + RLS |
| `120_os_agent_runs.sql` | `os_agent_runs` + `(client_id,status)` index + RLS |
| `121_os_memory_entries.sql` | `os_memory_entries` + pgvector index + RLS |
| `122_os_backlog_requests.sql` | `os_backlog_requests` + `(client_id,status)` index + RLS |
| `123_os_tenant_usage.sql` | `os_tenant_usage` + `client_id` index + RLS |

Six migrations (graph-memory migration dropped per decision 2). All additive.
Schema invariants: `client_id` not `tenant_id`; no destructive changes to
existing tables. RLS = `client_id`-scoped on every table; memory edit/delete
and backlog decisions gated to owner role at the app layer (`require_role`).

## Backend files (new)

- `backend/services/orchestrator.py` — Opus orchestrator: intent classify,
  route to worker, spawn agent runs, no-fit → backlog. Reuse `llm_runtime.py`,
  `advisor_executor.py`, `managed_agents_registry.py`.
- `backend/services/os_memory.py` — semantic memory only (decision 2): Voyage
  `voyage-3-lite` 512d embeddings + pgvector top-k retrieval. Reuses
  `backend/services/embeddings.py`. Write trigger = auto + explicit "remember
  this". Owner-only edit/delete enforced in the router via `require_role`.
- `backend/services/usage_meter.py` — per-tenant API spend metering + cap
  enforcement before each agent run.
- `backend/routers/os_threads.py` — thread + message endpoints.
- `backend/routers/os_agent_runs.py` — run status, thought-process, bug report.
- `backend/routers/os_deliverables.py` — approve / reject / edit approval-gated
  drafts.
- `backend/routers/os_memory.py` — memory CRUD (write/delete owner-only) +
  `/remember`.
- `backend/routers/os_backlog.py` — backlog list + owner decision.
- `backend/routers/os_usage.py` — current-cycle usage vs cap.
- Register all routers in `main.py` (lines ~746–813 block).
- No `from __future__ import annotations` in any FastAPI file. Pydantic models
  per endpoint.

## Frontend files (new)

- `frontend/src/pages/AgentOS.jsx` — chat shell, thread list, message stream,
  async agent-result rendering.
- `frontend/src/components/os/DeliverablePanel.jsx` — side-panel doc editor
  for approval-gated drafts (approve / edit / reject).
- `frontend/src/components/os/AgentRunFlowchart.jsx` — agent-run flowchart with
  thought process + "report bug" action.
- `frontend/src/utils/api/os.js` — API client for `/api/v1/os/*`.
- Sidebar entry + `App.jsx` route. Dark theme, live API, empty states.
- No `localStorage` in any component.

## P0 done criteria

- All 6 migrations apply cleanly via Supabase MCP.
- `/api/v1/os/threads` round-trip: send prompt → orchestrator responds →
  `os_agent_runs` row created → stub worker posts deliverable back →
  approval gate works.
- Memory write (auto + explicit) + semantic retrieval verified.
- No-fit request → `os_backlog_requests` row + owner email path.
- Usage meter blocks a run when the cap is hit.
- `npm run build` clean.

## After P0

Fan out in parallel: P1 (customer-question agent), P2 (booking), P3
(lead-nurture), P4 (marketing campaign); connector groups A/B/C. Each becomes
its own plan + build agent.

---

# Phase C — Pre-Merge Cleanup & Refactoring

Runs **last**, after P1–P4 + connectors land and **before** the branch merges
to `main`. The rehaul replaces old surfaces; this phase removes what the
replacement makes obsolete so `main` does not inherit two generations of code.

## Operating rules for this phase

- **Audit produces a report; deletion is a separate step.** No file is removed
  until its candidate row is confirmed. Honors `no-assumptions.md` — never guess
  which files to delete.
- **One PR per category** (skills / docs / plans / dead code). No mixed
  deletion commits. Honors `user-rules.md` Rule 8 (no half migrations).
- **Separate session from the build.** Per `improve-architecture.md`: do not
  audit and fix in the same session.
- **Reversible by design.** Everything removed is recoverable from git history;
  prefer `git rm` over archive-move unless a file is referenced by an external
  consumer.
- Each category below: (1) run the audit, (2) produce a candidate table with a
  keep/remove/uncertain verdict + rationale, (3) get explicit confirmation on
  the `uncertain` rows, (4) delete in one commit, (5) grep for dangling
  references, (6) run `check:quick` + build.

## C1 — Skills audit (`.claude/skills/`, 83 skills)

Goal: remove skills that do not relate to the Claude-driven workflow or are
superseded.

Audit steps:
1. List every skill, classify by relation to the current Claude Code workflow.
2. Flag non-Claude-tool skills, duplicates of a rule file, and skills no
   command/hook/agent references.
3. `grep -rl "<skill-name>" .claude/commands .claude/hooks .claude/agents
   CLAUDE.md` for each — zero hits = orphan candidate.

Initial candidate set (verdict pending confirmation):
- `kevin-mode` — joke persona skill; not workflow.
- `go`, `nodejs-backend-patterns`, `nodejs-best-practices` — off-stack
  (backend is FastAPI/Python, not Node/Go).
- `obsidian-sync` — Obsidian note sync; not Claude workflow.
- `autopilot-loop` — CLAUDE.md states `issue-to-pr-loop` replaced it
  ("kept for reference"); confirm whether reference copy is still wanted.
- `buddy`, `kairos`, `subconscious`, `last30days` — purpose unclear; classify
  during audit, do not pre-judge.

Deliverable: candidate table; confirmed removals deleted in one commit;
update CLAUDE.md skill count + any skill index.

## C2 — Stale `.md` files

Goal: remove dead docs — non-Claude AI configs, one-time audit reports,
superseded guides.

Root `.md` candidates (verdict pending confirmation):
- `GEMINI.md` — Gemini AI tool config; does not relate to Claude. Remove.
- One-time/dated reports: `AUDIT_RESULTS.md`, `CLEANUP_REPORT.md`,
  `CODEBASE-AUDIT-2026-03-25.md`, `DEBUGGING_SESSION_REPORT.md`,
  `FULL_AUDIT.md`, `PRE_LAUNCH_AUDIT.md` — confirm each is fully actioned,
  then remove (git history retains them).
- Keep: `CLAUDE.md`, `AGENTS.md`, `README.md`, `STRUCTURE.md`, `CHANGELOG.md`,
  `PROMPTLIBRARY.md`, `KARPATHY.md`, `design.md`.

`docs/` candidates: dated/one-time reports (`ai-auto-improve-report.md`,
`IMPLEMENTATION_SUMMARY_2026-04-05.md`, `env-vars-2026-04-26.md`,
`claude-code-audit.md`, `CODEBURN.md`, etc.) — audit each, confirm before
removal. Keep `dev-knowledge/` (bug-patterns, schema-log, architecture-
decisions) and live runbooks.

`audits/` candidates: 20+ dated audit files — superseded by later audits.
Confirm which the latest audit obsoletes, remove the rest.

Audit step for every removal: `grep -rl "<filename>" .` — fix or accept each
inbound reference before deleting.

## C3 — Stale plans (`plans/`)

Goal: remove plan files for work that has shipped or been abandoned.

Candidates (verify completion against the codebase before removing):
- `lead-parser-replacement_plan.md`, `marketing-addon-activation_plan.md`,
  `onboarding-v2_plan.md`, `onboarding-v2_issues.md`,
  `ops-automation-surfacing_plan.md`, `post-audit-remediation_plan.md`,
  `handoff-2026-04-16-post-analytics-split.md`.
- Keep: `agent-os-p0_plan.md` (this file), `plans/README.md`.

For each: confirm the feature shipped (grep the codebase for the implemented
surface) or was explicitly dropped. Shipped/dropped → remove. Still-open →
keep. Run `scripts/check_plan_drift.py` after to confirm no dangling refs.

## C4 — Dead code from the rehaul

Goal: remove code the Agent OS replaces. P0–P4 were additive; the dead code is
whatever the OS surfaces supersede (old dashboard pages, routers, services no
longer reachable once the chat-first OS is the entry point).

This step is **scoped only after P1–P4 land** — the dead set depends on which
old surfaces the workflow agents replace. Do not pre-list here.

Audit steps:
1. `dead-code-sweep` skill + `knip` / `ts-prune` / `depcheck` (frontend),
   `vulture` or grep-based reachability (backend).
2. `gitnexus_impact` on each candidate symbol — confirm zero live callers.
3. Cross-check against the spec: a surface the spec marks "replaced by Agent
   OS" is a removal candidate; a surface still referenced is not.
4. Removal PR: delete file + its tests + its router registration in `main.py`
   + its route in `App.jsx`/`Sidebar.jsx` together (no half-removal).
5. Verify: backend imports resolve, `npm run build` clean, full test suite
   green (minus the 21 pre-existing `main` failures already de-scoped).

## Phase C done criteria

- C1–C4 candidate tables produced and confirmed.
- Four removal commits (one per category), each with a passing
  `check:quick` + build.
- No dangling references (`grep` + `check_plan_drift.py` clean).
- CLAUDE.md updated: skill count, any removed-file references.
- Branch ready to merge to `main` with no obsolete code carried over.

### Status — 2026-05-25 (DONE)

- C1–C4 candidate tables: PRODUCED (`audits/audit-phase-c-2026-05-25.md`).
- Re-audit + per-ref triage completed (audit addendum "RE-AUDIT FINDINGS").
  Initial "0 refs" methodology too narrow — found 10 BLOCKED rows with
  active refs in registry files, CI workflows, migration comments,
  sibling specs, state dirs, toggle docs.
- Final outcome: **18 files removed across 4 commits**, **10 BLOCKED rows
  kept** (documented in audit addendum).
- Removal commits on this branch:
  - `80dc695d` C2 root .md (7 files + 4 ref patches: `.ai/manifest.json`,
    `.ai/README.md`, `.github/workflows/agent-config-security.yml`,
    `docs/AGENT_SYSTEM_PLAN.md`)
  - `b5fc7135` C2 stale doc + 7 superseded audits (8 files)
  - `5e27a13a` C3 shipped/dropped plan files (4 files)
  - `f519a5fd` C1 buddy skill (1 file)
- BLOCKED rows kept (do not re-attempt deletion in future sessions):
  - C1 skills with active refs: `kevin-mode`, `nodejs-*` mirrors,
    `obsidian-sync`, `kairos`, `subconscious`, `last30days`
  - Plans referenced by sibling specs: `lead-parser-replacement_plan`,
    `onboarding-v2_plan`, `onboarding-v2_issues`
- Verify: `npm run check:quick` ran; em-dash failures pre-existing in
  unrelated files (`os-inbound.js`, `SettingsInboundChannels.jsx`) — not
  introduced by Phase C deletions.
- The rest of the plan (P0–P4 workers, Group A inbound, tests, e2e loop)
  shipped earlier on this branch and PR.
