# Agent Graph Runtime — developer guide

Package: `backend/graph/` · Spec: `specs/agent-graph-runtime_spec.md`

A small runtime for expressing agent work as a **directed graph with cycles**,
executed as durable supersteps with enforced budgets.

## When to use it

Use a graph when the work has any of: a branch, a loop, a fan-out, a step that
should retry independently, a pause for human approval, or a spend ceiling.

Do **not** use it for a single model call — `call_claude_messages` directly is
the right answer there, and wrapping one call in a graph buys nothing.

It does not replace `backend/services/automation/`. That is a linear drip
sequencer with live tenant data and it works. This is for agent work.

## The 60-second version

```python
from backend.graph import END, Graph, run

graph = Graph("triage")
graph.declare("findings", reducer="append", default=[])

async def classify(ctx):
    return {"score": score_lead(ctx.get("lead"))}

async def escalate(ctx):
    return {"findings": "escalated to owner"}

graph.add_node("classify", classify)
graph.add_node("escalate", escalate)
graph.set_entry("classify")
graph.add_branch("classify", {"escalate": lambda s: s["score"] > 0.8}, default=END)
graph.add_edge("escalate", END)

result = await run(graph, {"lead": lead}, tenant_id=tenant_id)
result.status   # "completed" | "failed" | "awaiting_input" | "budget_exhausted"
result.state    # final state dict
```

## State is channels, not a bag

Every state key is a **channel** with a reducer that says how concurrent writes
combine. This is not ceremony — it is the reason two parallel branches writing
the same key is safe rather than a race whose winner depends on `asyncio`
scheduling.

| Reducer | Combines by | Use for |
|---|---|---|
| `last` (default) | last write wins | scalars, current status |
| `append` | list concatenation | message history, findings |
| `merge` | `dict.update` | accumulating structured facts |
| `add` | numeric sum | counters, scores |
| `once` | write-once; second write raises | run inputs, immutable IDs |

```python
graph.declare("messages", reducer="append", default=[])
graph.declare("cost", reducer="add", default=0)
graph.declare("lead_id", reducer="once")
```

Writes are folded in **node-name order** at the superstep boundary, so a run's
result never depends on which node happened to finish first.

Set `StateSchema(strict=True)` to make writing an undeclared channel an error.
Worth it once a graph is in production — it catches `summry` vs `summary`
instead of silently accumulating dead state.

## Nodes

A node is an async callable taking a `NodeContext` and returning a dict,
a `NodeResult`, or `None`.

```python
async def draft(ctx):
    ctx.state          # state at the START of this superstep — same for every
                       # node in it, so you never see a half-applied sibling
    ctx.get("lead")    # shorthand for ctx.state.get
    ctx.run_id
    ctx.superstep
    ctx.tenant_id
    ctx.resume_value   # value passed to resume(), when this node interrupted
    return {"draft": text}
```

Declarative policy per node — no boilerplate in the body:

```python
graph.add_node(
    "call_crm", fn,
    kind="agent",              # task | agent | router | human | terminal
    retries=2,                 # attempts AFTER the first, so up to 3 calls
    retry_backoff_seconds=0.5, # doubles each attempt
    timeout_seconds=20,
    on_error="raise",          # or "continue", or "goto:<node>"
)
```

`kind` is observability metadata only. It is what lets the step ledger tell
"this step called a model" from "this step read the database" without
inspecting the callable.

## Edges, branches, and the else rule

```python
graph.add_edge("a", "b")                                  # unconditional
graph.add_edge("a", "c", condition=lambda s: s["hot"])    # guarded
graph.add_branch("a", {"c": is_hot, "d": is_cold}, default="e")
```

**Every** matching non-default edge is taken — that is the fan-out primitive.
A `default` edge is an *else*: it fires only when nothing else matched. Getting
this wrong is the obvious trap (an unconditional fallback firing *alongside* a
matching branch, quietly running both targets), which is why `default` is a
distinct kind of edge rather than just an unguarded one.

`START` and `END` are sentinels. Reaching `END` ends that branch; the run
finishes when no branch is left.

A node can also route dynamically, overriding its static edges:

```python
return NodeResult(updates={...}, goto=["fetch_a", "fetch_b"])
```

`goto=[]` ends the branch.

## Loops

Cycles are the point. Bound them with a condition **and** rely on the budget as
the backstop:

```python
graph.add_branch("critique", {"draft": needs_revision}, default="approve")
```

`RunBudget.max_node_visits` (default 25) catches a loop whose condition never
flips, and fails with the offending node named — not a hang, not a wall-clock
timeout you have to diagnose.

## Budgets

```python
from backend.graph import RunBudget

budget = RunBudget(
    max_supersteps=40,
    max_node_visits=8,
    max_tokens=120_000,
    max_seconds=180,
)
result = await run(graph, inputs, budget=budget)
result.budget  # {"supersteps": .., "node_runs": .., "tokens": .., "visits": {..}}
```

Exhaustion is a **status**, not an exception — `budget_exhausted` with the
partial state intact and inspectable.

This is the loop-level enforcement point `.claude/rules/task-budgets.md` asks
for. Anthropic's `task_budget` is per-call and advisory; it cannot see that a
graph has looped forty times. This can. Agent nodes report token usage and the
runtime charges it to the run budget.

Budget counters survive `resume()`, so a run cannot earn a fresh allowance by
being resumed repeatedly.

## Human-in-the-loop

```python
from backend.graph import Interrupt, resume

async def approve(ctx):
    if ctx.resume_value is None:
        raise Interrupt("owner approval required", payload={"draft": ctx.get("draft")})
    return {"approved": ctx.resume_value["approved"]}
```

The run checkpoints as `awaiting_input` and returns. Later:

```python
result = await resume(graph, run_id, {"approved": True}, checkpointer=checkpointer)
```

**Only the node that paused re-runs.** Siblings that completed in the same
superstep had their results banked in the checkpoint, so a human pause never
causes a duplicate side effect. That is the one guarantee worth remembering
here; without it every graph with an approval gate would need idempotent nodes.

## Durability

```python
from backend.graph import SupabaseCheckpointer

result = await run(graph, inputs, checkpointer=SupabaseCheckpointer(), tenant_id=tid)
```

- `graph_runs` — one row per run, updated at each superstep boundary
- `graph_run_steps` — one row per node execution: attempts, duration, tokens, error

Migration `189_graph_runs.sql`. Both tables are `tenant_id`-scoped with RLS and
a service-role policy. (Note the split convention in this repo: `automation_*`
and this family use `tenant_id`; the `os_*` family uses `client_id`; `leads`
and `conversations` use `client_id`.)

Checkpoint **writes** are best-effort — a failed write logs and the run
continues, because losing durability is better than killing live work.
Checkpoint **reads** raise, because resuming from a checkpoint you could not
read is not safe.

Default when you pass nothing is `InMemoryCheckpointer`. Use `NullCheckpointer`
to discard.

## Agent nodes

```python
from backend.graph.adapters.llm import agent_node

graph.add_node(
    "qualify",
    agent_node(
        operation="graph.qualify.score",
        model="claude-haiku-4-5-20251001",
        prompt=lambda s: f"Score this lead: {s['lead']}",
        output_key="qualification",
        response_schema=QUALIFY_SCHEMA,   # implies parse_json
        max_tokens=512,
    ),
    kind="agent",
    retries=1,
)
```

`prompt` and `system` accept a callable over state — that is how state reaches
the model. Use `messages=lambda s: s["history"]` for multi-turn.

An agent node is **one model turn**. `llm_runtime` has no `tools` parameter and
keeps no inner agentic loop, and that is deliberate here: a tool-using agent is
expressed as nodes and edges instead of an opaque loop inside one call. The
graph then gets what an inner loop cannot give — a per-step audit trail, a
resume point between turns, and a budget that can see how many turns actually
happened.

Malformed JSON raises rather than falling back, so the node's `retries` and
`on_error` policy decide what happens. Silent fallbacks are how bad model
output reaches production.

## Tool nodes

```python
from backend.graph.adapters.tools import tool, tool_node

@tool("crm.update_stage")
async def update_stage(*, lead_id: str, stage: str) -> dict:
    ...

graph.add_node(
    "advance",
    tool_node("crm.update_stage",
              args=lambda s: {"lead_id": s["lead_id"], "stage": "qualified"}),
)
```

Tools are resolved by name at call time, so a graph can be defined before the
module registering its tools is imported — and so a graph stays serializable.

## Registry

```python
from backend.graph import register

@register("qualify_lead", version="2")
def build() -> Graph:
    ...

graph = registry.get("qualify_lead")        # highest version
graph = registry.get("qualify_lead", "1")   # pinned
```

Self-registration, same shape as `backend/services/os_actions`. It is what
keeps this from becoming another hand-maintained list like the ~35
`_safe_run(...)` calls in `backend/main.py`.

## Validation

`graph.validate()` runs automatically before the first node executes and
rejects: dangling edges, no entry point, unreachable `END`, unreachable nodes,
a node with no outgoing edge, a node with only conditional edges and no else,
an `on_error="goto:"` target that does not exist, edges out of `END` or into
`START`.

Catching these at build time is the difference between a clear error and a run
that burns budget going nowhere.

`graph.to_mermaid()` renders a flowchart for docs and PR descriptions.

## Worked example

`backend/graph/examples/qualify_lead.py` — qualify, draft, self-critique in a
bounded loop, pause for owner approval, send. Exercises cycles, conditional
branching, a human gate, and token budgeting together.

## Gotchas

- A node body must not mutate `ctx.state` — return updates instead. The state
  it is handed is shared across the superstep.
- **Supersteps are all-or-nothing.** If any node in a superstep fails the run,
  its siblings' writes are discarded along with it — the checkpoint holds the
  state from the last clean boundary. That keeps resume points consistent, but
  it means a side effect a sibling already performed is not reflected in state.
  Give side-effecting nodes `on_error="continue"` or their own superstep when
  that matters.
- Conditions are evaluated against the state **after** the superstep's writes
  land, so a condition reads what the step just wrote.
- `once` channels raise on a second write. That is intended: it surfaces a real
  race instead of letting one write clobber the other.
- `retries=2` means up to **three** calls.
- A node with a side effect and `retries > 0` must be idempotent.

## Cross-refs

- `specs/agent-graph-runtime_spec.md` — design rationale, non-goals
- `.claude/rules/task-budgets.md` — budget policy this implements
- `backend/services/llm_runtime.py` — the model call path agent nodes use
- `backend/services/os_projects.py` — the sequential planner this could back
