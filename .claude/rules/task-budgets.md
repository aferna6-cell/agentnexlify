# Budgets — two different primitives, do not confuse them

| | Session budget | Task budget |
|---|---|---|
| Enforced by | The platform, **hard** | The model, **advisory** |
| Denominated in | US cents (dollars) | Tokens |
| Scope | One Managed Agents session | One Messages-API agentic loop |
| Model can see it | No | Yes — it paces itself |
| Status in this repo | **IMPLEMENTED** (2026-08-24) | **NOT IMPLEMENTED** |

**A task budget cannot stop a runaway** — the model may ignore it. Only a
session budget is a real ceiling. Reach for the session budget on anything
autonomous; reach for the task budget only to improve pacing/quality.

---

## Session budgets (hard cap) — IMPLEMENTED

`backend/services/managed_agents.build_budget(cents)` builds the object;
`ManagedAgentsClient.create_session(..., budget_cents=N)` attaches it.
`scripts/managed_agents/_smoke_common.run_agent_session` applies
`DEFAULT_SESSION_BUDGET_CENTS = 500` ($5) to **every** script-launched session,
overridable per call or via `MANAGED_AGENTS_SESSION_BUDGET_CENTS` (`0` disables).

Semantics that bite if you don't know them:
- The cap is checked **between** model requests, so the in-flight request
  finishes and a 50-cent cap can settle at 53. Size with that margin.
- Hitting the cap makes the session go **idle**, not terminated —
  `stop_reason.type == "budget_reached"`, history and sandbox preserved.
  Raising the budget resumes it automatically.
- **Removing a budget is one-way.** A session created without one can never be
  given one; one whose budget was removed can never get it back. Change it,
  don't remove it.
- Multiagent sessions share **one** budget across all threads, advisor
  consultations included.
- A budgeted session whose model has no public list price is rejected (400).

Where to apply: every non-interactive session — cron, batch, autonomous loops,
smokes. Where NOT to: user-facing interactive paths (widget chat), where
correctness beats cost pacing.

Deployments take the same `budget` object and copy it onto **each run**, so it
bounds every firing separately rather than cumulative spend. See
`backend/services/managed_agents_deployments.create_deployment`.

---

## Task budgets (advisory) — NOT IMPLEMENTED

> **Status check, 2026-08-24.** The call-site table below describes an
> *intended* design. `grep -rn "task_budget\|task-budgets-2026-03-13" backend/`
> returns nothing: neither the parameter nor its beta header exists anywhere in
> this codebase. Treat this section as a proposal, not as documentation of
> shipped behavior. If you are here to control spend on an autonomous loop, use
> a **session budget** above — that one is real.

## What it is
Public-beta API parameter introduced with Opus 4.7 (2026-04-16). It lets Claude see an advisory token budget for a full agentic loop so it can prioritize work and finish gracefully as the budget is consumed.

Task budgets live on the Claude Platform API. They are not a Claude Code feature. They are for runtime agents we build in this project.

Important distinction:
- `task_budget`: advisory budget Claude can see and pace against.
- `max_tokens`: hard per-request generation cap Claude does not see.

Task budgets require the beta header `task-budgets-2026-03-13`, live under `output_config`, and currently have a minimum value of 20k tokens.

## Where to apply in AgentNexLiFy

Every place we call Opus 4.7 in a long-running context MUST consider a task budget. Short calls can use `max_tokens` or no budget instead.

| Call site | Why budget applies | Budget rule |
|---|---|---|
| `backend/services/llm_runtime.py::call_claude_messages` | Shared runtime for all agents | Centralized optional budget config |
| `backend/services/advisor_executor.py::advised_*` | Opus advises Sonnet and may reason/tool across context | Use `max_tokens` for compact briefs; use task budget only when the advisor is doing a real loop |
| `backend/services/managed_agents_registry.py` | Background agents and autonomous runs | Per-agent budget tier, minimum 20k when enabled |
| `backend/services/automation/scheduled_jobs.py` | Periodic workflows scaled across tenants | Budget long loops; bail early when quality would be poor |
| `scripts/daily/nightly-commit-review.sh` | Batch triage/fix loops | Session-level budget when using Opus 4.7 |
| `scripts/daily/kb-autopopulate.sh` | Twice-daily compile | Budget per article only for long compile loops |
| `autopilot-loop` / `issue-to-pr-loop` | 15-min polling and issue execution | Per-issue budget when using Opus 4.7 |

## When to NOT use a task budget
- Interactive chat widget: user-facing correctness beats cost pacing.
- One-shot API endpoints triggered by a user.
- Test fixtures or mocked calls.
- Short classification/extraction calls. Use Haiku or a low `max_tokens` cap instead.
- Open-ended agentic tasks where quality matters more than speed.

## Suggested controls by workload

| Workload | Control | Rationale |
|---|---|---|
| Widget chat reply | No task budget | Interactive, user-facing |
| Lead qualifier | Haiku or low `max_tokens` | Structured extraction is too small for a task budget |
| Advisor brief | `max_tokens` target around 5k output | Compact plan, not a full agentic loop |
| Executor implementation | Task budget 50k+ when Opus runs the loop | Full code generation and tool use |
| Nightly commit review | Task budget 20k-50k when Opus runs batch triage | Budgeted batch work |
| Nightly fix | Task budget 30k+ when Opus runs the fix | Single low-risk fix loop |
| KB article compile | Task budget 20k+ for long compile loops | Per-article pacing |
| Issue-to-PR full loop | Task budget 80k+ | Multi-file implementation |

## Implementation pattern

```python
response = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=64000,  # hard output ceiling
    thinking={"type": "adaptive"},
    output_config={
        "effort": "xhigh",
        "task_budget": {"type": "tokens", "total": 80000},
    },
    extra_headers={"anthropic-beta": "task-budgets-2026-03-13"},
    messages=[...],
)
```

Use `task_budget` only when the model needs to self-moderate across a larger loop. For compact outputs, prefer explicit prompt scope plus `max_tokens`.

## Monitoring
Log output token usage per call site (already in `llm_runtime.py` via `usage` field). Track actual usage against budget and alert when loops consistently hit >80%, because that usually means the budget is too tight or the task needs decomposition.

## Anti-patterns
- Never set a task budget below 20k tokens.
- Never treat task budget as a hard cap.
- Never skip budget consideration on cron or autonomous loops.
- Never set a budget so tight the model references the budget instead of solving the task.
- Never set a task budget on latency-sensitive user paths.
- Never hardcode budgets in dozens of places; centralize in `llm_runtime.py` config.

## Cross-refs
- `rules/opus-4-7.md`
- `rules/model-routing.md` - for picking the right model before setting budget
- `backend/services/llm_runtime.py`
- `backend/services/advisor_executor.py`
