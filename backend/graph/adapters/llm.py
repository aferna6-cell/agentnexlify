"""Agent nodes — a graph node backed by ``llm_runtime.call_claude_messages``.

``llm_runtime`` has no ``tools`` parameter and deliberately keeps no inner
agentic loop, so an agent node here is exactly one model turn. That is the
design, not a limitation: a tool-using agent is expressed as *nodes and edges*
rather than as an opaque loop inside a single call. The graph then gets what an
inner loop cannot give it — a per-step audit trail, a resume point between
turns, and a budget that can see how many turns have actually happened.

Token usage is reported on ``NodeResult.meta["tokens"]``; the runtime charges it
to the run budget. That closes the gap named in `.claude/rules/task-budgets.md`:
loop-level token accounting that a per-call ``max_tokens`` cannot provide.
"""

import json
import logging
from collections.abc import Callable
from typing import Any

from backend.graph.budget import RunBudget
from backend.graph.errors import BudgetExhausted
from backend.graph.nodes import NodeContext, NodeResult
from backend.services.llm_runtime import ClaudeCallResult, call_claude_messages

logger = logging.getLogger(__name__)

# A prompt is either a literal string or a function of state, which is how
# state reaches the model.
PromptSpec = str | Callable[[dict[str, Any]], str]


def _render(spec: PromptSpec | None, state: dict[str, Any]) -> str | None:
    if spec is None:
        return None
    return spec(state) if callable(spec) else spec


def _total_tokens(result: ClaudeCallResult) -> int:
    return sum(
        value or 0
        for value in (
            result.input_tokens,
            result.output_tokens,
            result.cache_creation_input_tokens,
            result.cache_read_input_tokens,
        )
    )


def _strip_fences(text: str) -> str:
    """Drop ```json fences a model sometimes adds despite instructions."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else ""
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[: -len("```")]
    return cleaned.strip()


def agent_node(
    *,
    operation: str,
    model: str,
    prompt: PromptSpec,
    system: PromptSpec | None = None,
    max_tokens: int = 1024,
    output_key: str = "reply",
    temperature: float | None = 0.0,
    timeout: float = 30.0,
    max_retries: int = 1,
    fallback_models: list[str] | None = None,
    response_schema: dict[str, Any] | None = None,
    parse_json: bool = False,
    output_config: dict[str, Any] | None = None,
    cache_system: bool = False,
    messages: Callable[[dict[str, Any]], list[dict[str, Any]]] | None = None,
    updates: Callable[[dict[str, Any], Any], dict[str, Any]] | None = None,
) -> Callable[[NodeContext], Any]:
    """Build a node function that performs one Claude turn.

    Args:
        prompt: literal text, or ``state -> text``. Ignored when ``messages``
            is given.
        messages: ``state -> [{"role": ..., "content": ...}]`` for multi-turn
            history — use this when the graph accumulates a message channel.
        output_key: state channel the reply is written to.
        parse_json: parse the reply as JSON before writing it. Implied by
            ``response_schema``, which constrains the model to valid JSON.
        updates: ``(state, parsed_or_text) -> delta`` when the reply should
            fan out into several channels rather than one.

    Returns a callable suitable for ``Graph.add_node(..., kind="agent")``.
    """
    if response_schema is not None:
        parse_json = True

    async def _node(ctx: NodeContext) -> NodeResult:
        budget: RunBudget | None = ctx.extras.get("budget")
        if budget is not None and budget.max_tokens is not None:
            if budget.tokens >= budget.max_tokens:
                raise BudgetExhausted(
                    "tokens",
                    f"node {ctx.node!r} refused to call {model}: run has spent "
                    f"{budget.tokens} of {budget.max_tokens} tokens",
                )

        payload = (
            messages(ctx.state)
            if messages is not None
            else [{"role": "user", "content": _render(prompt, ctx.state)}]
        )

        result = await call_claude_messages(
            operation=operation,
            model=model,
            max_tokens=max_tokens,
            messages=payload,
            temperature=temperature,
            system=_render(system, ctx.state),
            timeout=timeout,
            max_retries=max_retries,
            fallback_models=fallback_models,
            response_schema=response_schema,
            output_config=output_config,
            cache_system=cache_system,
            metadata={
                "graph_run_id": ctx.run_id,
                "graph_node": ctx.node,
                "superstep": ctx.superstep,
            },
        )

        value: Any = result.text
        if parse_json:
            try:
                value = json.loads(_strip_fences(result.text))
            except json.JSONDecodeError as exc:
                # Surfaced as a node failure so the graph's retry and on_error
                # policy decide what happens — not swallowed into a fallback.
                raise ValueError(
                    f"node {ctx.node!r} expected JSON from {model}, got "
                    f"{result.text[:200]!r}"
                ) from exc

        delta = updates(ctx.state, value) if updates else {output_key: value}

        return NodeResult(
            updates=delta,
            meta={
                "tokens": _total_tokens(result),
                "model": model,
                "duration_ms": result.duration_ms,
                "stop_reason": result.stop_reason,
            },
        )

    _node.__name__ = f"agent_node[{operation}]"
    return _node
