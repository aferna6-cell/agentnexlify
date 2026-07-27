"""Version-stable route introspection.

FastAPI changed the shape of ``routes`` in 0.136. Before it, ``include_router``
flattened a child router's routes into the parent, so ``app.routes`` was a flat
list of endpoints and ``len(app.routes)`` was an endpoint count. From 0.136 it
appends a single ``_IncludedRouter`` wrapper per include, and the real routes
live behind ``wrapper.original_router`` with the include's prefix carried on
``wrapper.include_context.prefix``.

Nothing breaks in the app — requests still route, and the OpenAPI schema is
unchanged. What breaks is every piece of code that *inspects* routes by walking
the list, which in this repo is the managed-agents preflight check and five
route-registration smoke tests. Those read as "hundreds of routes disappeared"
when nothing disappeared at all; that misreading is recorded as fact in
``backend/requirements.txt`` and in GH #265, and it is why the ``fastapi<0.136``
cap exists.

This module is the one place that knows about both shapes. Callers ask for
paths or signatures and get the same answer on either version.
"""

from collections.abc import Iterator
from typing import Any

# Verbs that are auto-added by the framework rather than declared by a handler.
# Counting them makes a route look like two or three.
IMPLICIT_METHODS = frozenset({"HEAD", "OPTIONS"})


def iter_routes(target: Any, prefix: str = "") -> Iterator[tuple[str, Any]]:
    """Yield ``(full_path, route)`` for every real route reachable from ``target``.

    ``target`` is an app or a router. Include wrappers are transparently
    recursed through, accumulating each include's prefix so the emitted path is
    the one a client would call. On FastAPI < 0.136 there are no wrappers and
    this degrades to a flat walk, which is why callers need no version check.

    A ``Mount`` is yielded as a single entry rather than descended into: it owns
    its own routing, its sub-app may not be a FastAPI app at all, and the old
    flat walk treated it the same way.
    """
    routes = getattr(target, "routes", None)
    if routes is None:
        return

    for route in routes:
        included = getattr(route, "original_router", None)
        if included is not None:
            context = getattr(route, "include_context", None)
            yield from iter_routes(
                included, prefix + (getattr(context, "prefix", "") or "")
            )
            continue

        path = getattr(route, "path", None)
        if path is None:
            continue
        yield prefix + path, route


def route_paths(target: Any) -> list[str]:
    """Every route path, in declaration order. Duplicates preserved — a repeated
    path is usually the bug the caller is looking for."""
    return [path for path, _ in iter_routes(target)]


def route_signatures(target: Any) -> set[tuple[str, str]]:
    """``{(METHOD, path)}`` for every explicitly declared verb.

    ``HEAD`` and ``OPTIONS`` are dropped: the framework adds them, so including
    them makes route counts depend on framework behavior rather than on what
    the code declares.
    """
    signatures: set[tuple[str, str]] = set()
    for path, route in iter_routes(target):
        for method in getattr(route, "methods", None) or ():
            if method not in IMPLICIT_METHODS:
                signatures.add((method, path))
    return signatures


def count_routes(target: Any) -> int:
    """How many real routes ``target`` exposes.

    This is what ``len(app.routes)`` used to mean and no longer does.
    """
    return sum(1 for _ in iter_routes(target))
