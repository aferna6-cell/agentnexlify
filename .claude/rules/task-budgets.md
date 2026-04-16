# Task Budgets — Opus 4.7 API Feature

## What it is
Public-beta API parameter introduced with Opus 4.7 (2026-04-16). Lets developers cap Claude's token spend on a task so the model prioritizes work across longer runs instead of burning budget early.

Lives on the Claude Platform (Anthropic API). Not a Claude Code feature; a runtime feature for agents we build IN this project.

## Where to apply in AgentNexLiFy

Every place we call `anthropic.Messages.create()` with Opus 4.7 in a long-running context MUST consider a task budget:

| Call site | Why budget applies | Suggested budget |
|---|---|---|
| `backend/services/llm_runtime.py::call_claude_messages` | Shared runtime for all agents | Configurable per call |
| `backend/services/advisor_executor.py::advised_*` | Opus advises Sonnet — full Opus cost | Cap advisor at ~5k output tokens |
| `backend/services/managed_agents_registry.py` | Background agents — autonomous runs | Per-agent budget tier |
| `backend/services/automation/scheduled_jobs.py` — any Claude call | Periodic workflows, scaled across tenants | Tight budget; bail early |
| `scripts/daily/nightly-commit-review.sh` Sonnet fixes | Long autonomous run | Cap at session-level |
| `scripts/daily/kb-autopopulate.sh` | Twice-daily compile | Cap per article |
| `autopilot-loop` / `issue-to-pr-loop` | 15-min polling | Per-issue cap |

## When to NOT use a budget
- Interactive chat widget — user expects full response
- One-shot API endpoint triggered by user — no long-running context
- Test fixtures / mocked calls
- Short classification calls (Haiku handles these anyway)

## Suggested defaults by workload

| Workload | Budget (output tokens) | Rationale |
|---|---|---|
| Widget chat reply | none | interactive, user-facing |
| Lead qualifier | 1,500 | structured extraction, short output |
| Advisor brief | 5,000 | planning, reasonable depth |
| Executor implementation | 50,000 | full code generation |
| Nightly commit review (Haiku triage) | 10,000 | batch of commits |
| Nightly fix (Sonnet) | 30,000 | single low-risk fix |
| KB article compile | 8,000 | per article |
| Issue-to-PR (full loop) | 80,000 | multi-file implementation |

## Implementation pattern

Until the SDK exposes task_budget as first-class, gate via explicit `max_tokens` + early-exit checks in our own loop logic. When the SDK lands:

```python
response = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=..., # hard cap
    task_budget={"output_tokens": 5000},  # soft prioritization
    ...
)
```

## Monitoring
Log output token usage per call site (already in `llm_runtime.py` via `usage` field). Track against budget — alert if >80% consistently hit to re-tune.

## Anti-patterns
- Never set a budget so tight the model truncates mid-thought
- Never skip budget on a cron job — budget = insurance against runaway loops
- Never set a budget on latency-sensitive user paths — correctness beats saving pennies
- Never hardcode budgets in dozens of places — centralize in `llm_runtime.py` config

## Cross-refs
- `rules/opus-4-7.md`
- `rules/model-routing.md` — for picking the right model before setting budget
- `backend/services/llm_runtime.py`
- `backend/services/advisor_executor.py`
