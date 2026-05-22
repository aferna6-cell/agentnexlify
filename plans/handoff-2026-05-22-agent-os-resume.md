# Handoff — Agent OS rehaul resume (2026-05-22)

Session hit ~86% of 1M context budget. Forced handoff per
`.claude/rules/one-task-one-chat.md` — quality degrades past ~40% context.
Start a fresh session and read this file first.

## 1. What we're working on

Agent OS rehaul of AgentNexLiFy — chat-first orchestrator + worker agents.
Branch `claude/agent-os-grill-resume-cHznV`, PR #177 (draft, stays draft).

Active goal (set via `/goal`): "complete the rest of the plan, then perform a
significant refactoring removing all dead code, specs and plans before merging
to main." This is multi-session work — do not attempt in one chat.

## 2. Decisions made

- P0 foundation + P1-P4 workers built, committed, pushed.
- MVP works end-to-end; `customer_question` agent ready.
- CI failure on PR #177 (PR Validation) = pre-existing rot on `origin/main`,
  NOT a branch regression. 21 inherited failures (`call_claude_messages`
  patch-target mismatches in `test_local_seo.py`, `test_retry_policy.py`,
  `test_onboarding_ai_paths.py`, `test_auth_endpoints.py`). Out of rehaul
  scope — file a separate GH issue. Branch is a net CI improvement
  (main 21F/524P; branch 21F/647P) and fixes a broken main test collection.
- Graph-memory layer was cut from P0; re-decision now due (end of P1).

## 3. Files / key paths

- `specs/agent-os-overhaul_spec.md` — authoritative spec
- `plans/agent-os-p0_plan.md` — P0 build plan + Phase C definition
- `plans/agent-os-next-steps_plan.md` — the remaining roadmap (READ THIS)
- `backend/services/os_workers/` — worker registry (5 workers auto-discovered)
- `backend/services/orchestrator.py`, `os_memory.py`, `usage_meter.py`
- `tests/test_os_mvp_e2e.py` — MVP demo + regression test
- Migrations 118-123 — `os_*` tables
- Last commits: `ab00b91` (next-steps plan), `b08c7a1` (MVP test),
  `d5e5c7a` (P1-P4 workers)

## 4. Open questions / blockers

- Connector group A/B/C boundaries not yet specced — each needs its own
  spec before any build.
- Graph-memory: measure semantic-only recall on real tenant threads before
  deciding whether to build the graph layer as P5.
- Phase C cleanup + the requested dead-code refactor must run as a SEPARATE
  audit-only session (do not audit and fix in the same session).

## 5. Concrete next step

In a fresh session: read `plans/agent-os-next-steps_plan.md`, then start with
connector group A — run `grill-me`, then `write-prd` to produce
`specs/agent-os-connectors-inbound_spec.md`. One connector group per session.
The dead-code refactor and merge come last, each in its own session.
