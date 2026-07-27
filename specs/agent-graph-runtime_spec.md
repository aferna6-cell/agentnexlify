# Agent Graph Runtime — Spec

Status: draft · Owner: platform · Created 2026-07-27

## Problem

AgentNexLiFy runs a growing amount of multi-step AI work — lead qualification,
photo quoting, review responses, document drafting, the nightly loops — and
every one of them is hand-rolled. Each service re-implements the same four
things badly:

1. **Sequencing** — "call the model, then check the answer, then maybe call it
   again" is written as nested `if`/`await` in a service function.
2. **Retry + failure policy** — some call sites pass `max_retries`, some wrap in
   `try/except`, some fail open silently.
3. **Durability** — if the process dies mid-way, the work is lost. There is no
   record of *which step* was reached.
4. **Budget** — `.claude/rules/task-budgets.md` says every long agentic loop must
   be budgeted. Today nothing enforces that; budgets are per-API-call at best.

The one piece of existing machinery, `backend/services/automation/`, is a
**linear** step sequencer: `automation_executions` carries a step index and a
`next_run_at`. It cannot branch, cannot loop, cannot fan out, and its steps are
email/SMS sends — not agent turns.

## Goal

A small, dependency-free runtime for expressing agent work as a **directed graph
with cycles**, executed as durable supersteps with enforced budgets.

Concretely: a developer writes ~20 lines to declare a graph, and gets
branching, bounded loops, parallel fan-out with deterministic merges, retries,
checkpointing, resume, human-in-the-loop pauses, and per-run token accounting
for free.

## Non-goals

- **Not a LangGraph dependency.** We adopt the ideas (superstep execution,
  channel reducers) and implement ~800 lines ourselves. Adding a heavyweight
  orchestration dependency to a FastAPI service we deploy on Railway is not
  worth it, and `.claude/skills/agent-filter/` exists precisely to say no here.
- **Not a replacement for `automation/`.** The drip sequencer works and has
  live tenant data. The graph runtime is for *agent* work. Migrating drips onto
  it is a later, separate decision.
- **Not a UI.** No visual graph builder in v1. Graphs are Python.
- **Not distributed.** One run executes inside one process. Durability lets a
  different process *resume* a run, but a single superstep is not split across
  machines.

## Concepts

### State and channels

State is a flat `dict[str, Any]`. Each key is a **channel** with a declared
**reducer** that says how concurrent writes combine:

| Reducer | Behavior | Use for |
|---|---|---|
| `last` | last write wins (default) | scalars, current status |
| `append` | list concatenation | message history, findings |
| `merge` | dict update | accumulating structured facts |
| `add` | numeric sum | counters, scores |
| `once` | write-once; second write raises | run inputs, immutable IDs |

Reducers are the whole reason parallel branches are safe. Without them, two
nodes writing the same key in the same superstep is a race whose winner depends
on `asyncio` scheduling. With them, the merge is deterministic and declared.

### Nodes

A node is a name plus an async callable `(NodeContext) -> NodeResult`.

`NodeResult` carries:
- `updates: dict` — the state delta this node produced (applied via reducers)
- `goto: str | list[str] | None` — dynamic routing that overrides static edges
- `meta: dict` — observability payload recorded on the step row

`kind` is metadata for observability and gating (`task`, `agent`, `router`,
`human`, `terminal`) — it does not change execution.

### Edges

`Edge(source, target, condition=None)`. `condition` is a predicate over state.
`START` and `END` are sentinel node names. A node with multiple outgoing
conditional edges takes **every** edge whose condition is true — that is the
fan-out primitive. Cycles are legal and expected; that is the "loop" in
loop/graph engineering.

### The loop (superstep execution)

Pregel/BSP-style, because it makes parallel merges and checkpointing trivial:

```
frontier ← successors(START)
while frontier and budget allows:
    results ← await gather(run(n) for n in frontier)   # concurrent
    state   ← reduce(state, all updates)               # deterministic merge
    record checkpoint(superstep, state)                # durable
    frontier ← successors(frontier, evaluated against new state)
```

Every node in a superstep sees the *same* input state. Writes land at the
superstep boundary. No node observes a half-applied sibling.

### Budgets

`RunBudget` caps `supersteps`, `node_runs`, `node_visits` (per node),
`tokens`, and `seconds`. Exhaustion is a first-class terminal status
(`budget_exhausted`), not an exception — the run's partial state is preserved
and inspectable. The per-node `node_visits` cap is what makes an infinite
self-loop fail with "node `reflect` exceeded 12 visits" instead of hanging.

This is the enforcement point `.claude/rules/task-budgets.md` asks for: token
usage from `ClaudeCallResult` is charged to the run budget by the agent-node
adapter.

### Interrupts (human-in-the-loop)

A node raises `Interrupt(reason, payload)`. The run checkpoints with status
`awaiting_input` and returns. `resume(run_id, value)` reloads the checkpoint,
injects `value`, and re-runs that node. This is how "owner approves the drafted
reply before it sends" is expressed without a bespoke pending-approval table.

### Durability

`Checkpointer` protocol with two implementations:
- `InMemoryCheckpointer` — tests and single-shot runs
- `SupabaseCheckpointer` — `graph_runs` (one row per run) and `graph_run_steps`
  (one row per node execution)

Both tables are `tenant_id`-scoped, RLS-enabled, service-role policy — matching
the convention from migrations 173/186/187. (`client_id` is the leads and
conversations convention only; service tables use `tenant_id`.)

## Failure policy

Per node: `retries` with exponential backoff, then `on_error`:
- `raise` (default) — run fails, status `failed`, error recorded
- `continue` — node contributes no updates, graph advances
- `goto:<node>` — jump to a recovery node

## What ships in v1

- `backend/graph/` package: state, nodes, graph + validation, runtime, budget,
  checkpointing, registry, errors
- Agent-node adapter over `backend/services/llm_runtime.call_claude_messages`
  with automatic token charging
- Tool-node adapter with a name→callable registry
- `migrations/189_graph_runs.sql`
- Tests covering validation, branching, cycles, budget exhaustion, parallel
  merge semantics, retries, interrupt/resume, and checkpoint round-trip
- A worked example graph (bounded lead-qualification loop) that exercises
  branch + cycle + budget together

## Open questions (deferred, not blocking v1)

- Should tenant-authored graphs be storable as JSON in the DB? The node
  registry makes this possible; the security review of running tenant-authored
  control flow does not belong in v1.
- Does the drip sequencer eventually migrate onto this? Only worth doing if a
  drip needs branching.
- Streaming intermediate node output to the dashboard — needs an events table
  or a channel; out of scope until there is a UI consuming it.
