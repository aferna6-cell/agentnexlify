"""Terminal demo for Agent OS.

Run without arguments to walk every routing path against the Bright Auto
fixture::

    python -m agent_os.demo.cli

Pass an ask to route a single request::

    python -m agent_os.demo.cli "text Mike a reminder about his appointment"

Add ``--interactive`` for a REPL. The demo runs offline (deterministic provider)
unless ``ANTHROPIC_API_KEY`` is set, in which case drafts upgrade to Claude.
"""

from __future__ import annotations

import argparse
import sys

from agent_os.demo.sample_data import sample_asks, sample_context
from agent_os.llm import default_provider
from agent_os.orchestrator import Orchestrator, RoutingDecision
from agent_os.registry import REGISTRY
from agent_os.result import AgentResult, OwnerAsk

_RULE = "─" * 72


def _provider_banner() -> str:
    provider = default_provider()
    if provider.name == "anthropic" and provider.available:
        return "LLM: Anthropic (live drafts)"
    return "LLM: deterministic (offline templates — no API key)"


def _print_decision(decision: RoutingDecision) -> None:
    if decision.is_bucket_query:
        print("Routed: bucket query (no agent run)")
        print()
        print(decision.bucket_listing)
        return

    if decision.needs_owner_choice:
        a, b = decision.choice or ("?", "?")
        print(f"Routed: ambiguous — owner must choose between {a} and {b}")
        print(f"  {decision.choice_prompt}")
        return

    tag = ""
    if decision.short_circuited:
        tag = " [short-circuit]"
    elif decision.used_specialty_rule:
        tag = " [specialty rule]"
    elif decision.is_generalist:
        tag = " [generalist fallback]"
    print(f"Routed: {decision.agent_id}{tag}  (confidence {decision.confidence:.2f})")
    print(f"  reason: {decision.reason}")
    if decision.channel_override is not None:
        print(f"  channel inferred: {decision.channel_override.value}")
    if decision.runner_up_id:
        print(
            f"  runner-up: {decision.runner_up_id} "
            f"({decision.runner_up_confidence:.2f})"
        )


def _print_result(result: AgentResult | None) -> None:
    if result is None:
        return
    print()
    if not result.has_draft:
        print("Draft: (none — service surfaced a reason instead)")
    else:
        flag = "  ⚠ FLAGGED" if result.flagged else ""
        approval = "needs approval" if result.requires_approval else "no approval needed"
        print(f"Draft [{result.channel.value}] — {approval}{flag}")
        print(f"  {result.title}")
        print()
        for line in result.body.splitlines():
            print(f"  {line}")
    if result.orchestrator_messages:
        print()
        print("Orchestrator chat (owner-only, never sent to customer):")
        for msg in result.orchestrator_messages:
            print(f"  • {msg}")
    print()
    print("Reasoning trace (honest — ✓ loaded, ○ not loaded):")
    for line in result.trace.render().splitlines():
        print(f"  {line}")


def route_one(orch: Orchestrator, context, ask: OwnerAsk | str) -> None:
    text = ask.text if isinstance(ask, OwnerAsk) else ask
    print(_RULE)
    print(f'Ask: "{text}"')
    print()
    decision, result = orch.handle(ask, context)
    _print_decision(decision)
    _print_result(result)
    print()


def run_walkthrough() -> None:
    context = sample_context()
    orch = Orchestrator()
    print(_RULE)
    print("AGENT OS — demo walkthrough")
    print(f"{_provider_banner()}")
    print(f"Registered agents: {len(REGISTRY)} across 8 buckets")
    print(f'Business: {context.business_profile.signoff()} ({context.business_profile.city})')
    print()
    for ask in sample_asks():
        route_one(orch, context, ask)

    print(_RULE)
    print("Wishlist (demand for agents that don't exist yet):")
    if not orch.wishlist:
        print("  (empty)")
    for entry in orch.wishlist:
        near = entry.closest_agent_id or "no near match"
        print(f'  • "{entry.ask_text}"  (closest: {near} @ {entry.closest_score:.2f})')
    print()
    print(f"Routing log: {len(orch.log)} decision(s) recorded.")
    print(_RULE)


def run_interactive() -> None:
    context = sample_context()
    orch = Orchestrator()
    print(_RULE)
    print("AGENT OS — interactive demo")
    print(f"{_provider_banner()}")
    print('Type an ask, "buckets" to list everything, or "quit" to exit.')
    print(_RULE)
    while True:
        try:
            ask = input("\nowner> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not ask:
            continue
        if ask.lower() in {"quit", "exit", "q"}:
            break
        if ask.lower() in {"buckets", "agents", "help"}:
            print()
            print(orch.list_buckets())
            continue
        route_one(orch, context, ask)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agent-os-demo", description="Agent OS routing + drafting demo."
    )
    parser.add_argument("ask", nargs="*", help="A single ask to route (optional).")
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="Start a REPL."
    )
    args = parser.parse_args(argv)

    if args.interactive:
        run_interactive()
        return 0
    if args.ask:
        context = sample_context()
        orch = Orchestrator()
        route_one(orch, context, " ".join(args.ask))
        return 0
    run_walkthrough()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
