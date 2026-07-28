"""Graph registry — name+version lookup for graphs defined anywhere in the app.

Mirrors the auto-discovery pattern already used by ``backend/services/os_actions``:
a module that registers itself is reachable without editing a central file. That
is the property that keeps this from becoming another hand-maintained list like
the ~35 ``_safe_run(...)`` calls in ``backend/main.py``.
"""

import logging
from collections.abc import Callable

from backend.graph.graph import Graph

logger = logging.getLogger(__name__)

# Graphs are stored lazily as factories: importing this module must not build
# every graph in the app, and a graph that closes over settings should be
# constructed when it is asked for, not at import time.
_FACTORIES: dict[tuple[str, str], Callable[[], Graph]] = {}


def register(name: str, version: str = "1"):
    """Decorator registering a zero-argument factory that returns a Graph.

        @register("lead_qualification", version="2")
        def build() -> Graph:
            ...
    """

    def decorator(factory: Callable[[], Graph]) -> Callable[[], Graph]:
        key = (name, version)
        if key in _FACTORIES:
            raise ValueError(f"graph {name!r} v{version} is already registered")
        _FACTORIES[key] = factory
        logger.debug("graph.registry.register name=%s version=%s", name, version)
        return factory

    return decorator


def get(name: str, version: str | None = None) -> Graph:
    """Build and return a registered graph.

    ``version=None`` selects the highest registered version, so callers that do
    not care about pinning keep working when a v2 lands.
    """
    if version is None:
        versions = [v for (n, v) in _FACTORIES if n == name]
        if not versions:
            raise KeyError(f"no graph registered under {name!r}")
        version = max(versions, key=_version_key)

    factory = _FACTORIES.get((name, version))
    if factory is None:
        raise KeyError(f"no graph registered under {name!r} v{version}")
    return factory()


def _version_key(version: str) -> tuple:
    """Sort '10' after '9'. Falls back to string order for non-numeric versions."""
    parts = version.split(".")
    try:
        return (0, tuple(int(p) for p in parts))
    except ValueError:
        return (1, version)


def names() -> list[tuple[str, str]]:
    """Every registered (name, version), sorted."""
    return sorted(_FACTORIES)


def clear() -> None:
    """Drop all registrations. Test-support only."""
    _FACTORIES.clear()
