"""Agent OS data-plane tool registry — auto-discovers every module here.

Drop a module in this package that defines a module-level ``SPEC: ToolSpec``
and it registers automatically. Same discovery mechanism as
``backend/services/os_actions/``.

The registry is an allow-list, and that is the point: an agent (or a model
inventing a plausible tool id) can only reach a capability that a human put in
this package. ``run_tool`` refuses anything else.
"""

import importlib
import logging
import pkgutil

from backend.services.os_tools.base import (
    ToolContext,
    ToolOutcome,
    ToolSpec,
    VerificationOutcome,
    now_iso,
)

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, ToolSpec] = {}
_DISCOVERED = False


def _discover() -> None:
    """Import every tool module once and collect its ``SPEC``."""
    global _DISCOVERED
    if _DISCOVERED:
        return
    _DISCOVERED = True
    package = importlib.import_module(__name__)
    for info in pkgutil.iter_modules(package.__path__):
        if info.name == "base" or info.name.startswith("_"):
            continue
        try:
            module = importlib.import_module(f"{__name__}.{info.name}")
        except Exception:
            logger.exception("os_tools: failed to import module %s", info.name)
            continue
        spec = getattr(module, "SPEC", None)
        if isinstance(spec, ToolSpec):
            _REGISTRY[spec.tool_id] = spec
        else:
            logger.warning("os_tools: module %s has no ToolSpec SPEC", info.name)


def all_tools() -> dict[str, ToolSpec]:
    _discover()
    return dict(_REGISTRY)


def get_tool(tool_id: str) -> ToolSpec | None:
    _discover()
    return _REGISTRY.get(tool_id)


def has_tool(tool_id: str) -> bool:
    return get_tool(tool_id) is not None


async def run_tool(ctx: ToolContext) -> tuple[ToolOutcome, VerificationOutcome]:
    """Validate, execute and verify one data-plane tool.

    The caller (``routers/os_tool_executions.py``) has already claimed the
    durable execution row with a conditional update, so reaching this function
    means exactly one approval won the right to run this tool once.

    Input is re-validated here against the tool's own Pydantic model even
    though the engine validated it with the equivalent Zod schema: the stored
    input crossed a process, a database and possibly a deploy since then, and
    this plane is the one holding the credentials. Never trust the shape.

    Returns ``(outcome, verification)``. Verification is a separate return
    value, never folded into the outcome, because "it ran" and "we confirmed
    it landed" must stay independently representable.
    """
    spec = get_tool(ctx.tool_id)
    if spec is None:
        return (
            ToolOutcome(
                status="failed",
                error={"code": "unknown_tool", "message": f"unknown tool '{ctx.tool_id}'"},
            ),
            VerificationOutcome(state="not_applicable", detail="the tool was never run"),
        )

    try:
        validated = spec.input_model(**(ctx.input or {}))
    except Exception as e:
        return (
            ToolOutcome(
                status="failed",
                error={"code": "invalid_input", "message": str(e)[:500]},
            ),
            VerificationOutcome(state="not_applicable", detail="the tool was never run"),
        )

    ctx.input = validated.model_dump()

    try:
        outcome = await spec.execute(ctx)
    except Exception as e:
        logger.exception(
            "os_tools: %s raised client_id=%s execution_id=%s",
            ctx.tool_id,
            ctx.client_id,
            ctx.execution_id,
        )
        return (
            ToolOutcome(
                status="failed",
                error={"code": "tool_error", "message": str(e)[:500]},
            ),
            VerificationOutcome(
                state="failed",
                detail="the tool raised, so whether the side effect happened is unknown",
            ),
        )

    if outcome.status != "succeeded" or spec.verify is None:
        state = "not_applicable" if spec.verify is None else "not_applicable"
        detail = (
            "this tool declares no verifier"
            if spec.verify is None
            else "the tool did not succeed, so there is nothing to verify"
        )
        return outcome, VerificationOutcome(state=state, detail=detail)

    try:
        verification = await spec.verify(ctx, outcome)
    except Exception as e:
        logger.exception(
            "os_tools: %s verifier raised client_id=%s", ctx.tool_id, ctx.client_id
        )
        verification = VerificationOutcome(
            state="failed", detail=f"the verifier could not run: {str(e)[:200]}"
        )
    return outcome, verification


__all__ = [
    "ToolContext",
    "ToolOutcome",
    "ToolSpec",
    "VerificationOutcome",
    "all_tools",
    "get_tool",
    "has_tool",
    "now_iso",
    "run_tool",
]
