"""Tool nodes — named side-effecting callables usable as graph nodes.

The registry exists so a graph can name a tool as a string rather than closing
over an import. That is what makes a graph serializable, and it is the same
self-registration shape as ``backend/services/os_actions``.
"""

import inspect
import logging
from collections.abc import Callable
from typing import Any

from backend.graph.nodes import NodeContext, NodeResult

logger = logging.getLogger(__name__)

_TOOLS: dict[str, Callable[..., Any]] = {}


def tool(name: str):
    """Register a callable under ``name``.

        @tool("crm.update_stage")
        async def update_stage(*, lead_id: str, stage: str) -> dict: ...
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        if name in _TOOLS:
            raise ValueError(f"tool {name!r} is already registered")
        _TOOLS[name] = fn
        return fn

    return decorator


def get_tool(name: str) -> Callable[..., Any]:
    if name not in _TOOLS:
        raise KeyError(
            f"no tool registered as {name!r}; registered: {sorted(_TOOLS) or 'none'}"
        )
    return _TOOLS[name]


def registered() -> list[str]:
    return sorted(_TOOLS)


def clear() -> None:
    """Test-support only."""
    _TOOLS.clear()


def tool_node(
    name: str,
    *,
    args: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    output_key: str = "tool_result",
    updates: Callable[[dict[str, Any], Any], dict[str, Any]] | None = None,
) -> Callable[[NodeContext], Any]:
    """Build a node that calls the registered tool ``name``.

    Args:
        args: ``state -> kwargs`` for the tool. Defaults to no arguments.
        output_key: channel the return value is written to.
        updates: ``(state, return_value) -> delta`` when one channel is not enough.

    The tool is looked up at call time, not build time, so a graph can be
    defined before the module registering its tools has been imported.
    """

    async def _node(ctx: NodeContext) -> NodeResult:
        fn = get_tool(name)
        kwargs = args(ctx.state) if args else {}
        value = fn(**kwargs)
        if inspect.isawaitable(value):
            value = await value
        delta = updates(ctx.state, value) if updates else {output_key: value}
        return NodeResult(updates=delta, meta={"tool": name})

    _node.__name__ = f"tool_node[{name}]"
    return _node
