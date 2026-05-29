"""Shared test fixtures and helpers.

Adds the package root to ``sys.path`` so ``import agent_os`` resolves no matter
how pytest is invoked (``pytest`` from the repo root, the ``agent-os/`` dir, or
CI). ``pyproject.toml`` also sets ``pythonpath`` — this is the belt-and-braces.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PKG_ROOT = Path(__file__).resolve().parents[1]
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

from agent_os.agents._helpers import build_spec  # noqa: E402
from agent_os.context import SharedContext  # noqa: E402
from agent_os.demo.sample_data import sample_context  # noqa: E402
from agent_os.orchestrator import Orchestrator  # noqa: E402
from agent_os.profile import BusinessProfile  # noqa: E402
from agent_os.registry import AgentRegistry  # noqa: E402
from agent_os.schema import (  # noqa: E402
    Bucket,
    Channel,
    Example,
    Priority,
    Status,
)


@pytest.fixture
def context() -> SharedContext:
    """The fully-populated Bright Auto demo context."""

    return sample_context()


@pytest.fixture
def profile(context: SharedContext) -> BusinessProfile:
    return context.business_profile


@pytest.fixture
def orchestrator() -> Orchestrator:
    """A fresh orchestrator over the global registry (own wishlist + log)."""

    return Orchestrator()


@pytest.fixture
def empty_registry() -> AgentRegistry:
    """An empty registry for registration / duplicate / unknown-id tests."""

    return AgentRegistry()


def make_spec(channel: Channel, agent_id: str = "test_agent"):
    """Build a minimal, schema-valid spec on *channel* for rule tests."""

    return build_spec(
        agent_id=agent_id,
        display_name="Test Agent",
        bucket=Bucket.system,
        status=Status.new,
        build_priority=Priority.P4,
        purpose="A throwaway agent used only to exercise the rule validator.",
        routes_here_when=("never — test only",),
        channel=channel,
        title_format="Test — {x}",
        body_format="plain",
        reasoning_trace_steps=("Business profile",),
        example_interactions=(
            Example(
                owner_ask="test",
                expected_route=agent_id,
                expected_output_excerpt="",
            ),
        ),
    )
