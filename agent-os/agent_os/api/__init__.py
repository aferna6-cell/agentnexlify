"""HTTP surface for Agent OS.

A thin FastAPI app over the orchestrator + registry. It serves the static web
demo and exposes JSON endpoints to route asks, list agents by bucket, and read
back the wishlist and routing log. The app holds one orchestrator and one
sample context per process, so the wishlist and decision log accumulate across
requests the way they would in a live session.

Note: ``app`` (in ``agent_os.api.app``) deliberately omits
``from __future__ import annotations`` — deferred annotations make Pydantic
resolve request bodies as strings and every request 422s.
"""
