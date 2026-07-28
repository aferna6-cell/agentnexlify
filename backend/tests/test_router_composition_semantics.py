"""Characterization tests for router composition — the gate in front of #265.

`backend/requirements.txt` caps `fastapi<0.136`. #600 showed the stated reason
for that cap is wrong: 0.136 does not "silently register zero routes", it stops
flattening included routers into `app.routes`, so `len(app.routes)` stops being
an endpoint count. Routes are still registered and still served.

That correction removes the *stated* justification for the cap. It does not
establish that the bump is safe, because the router internals really did change
and four behaviors that ride on them were never pinned by a test:

1. middleware execution order across an `include_router` boundary
2. `dependencies=` declared on `include_router`, and their order relative to
   route-level dependencies
3. `prefix=` composition — nested includes, empty prefixes, trailing slashes
4. `app.mount()` sub-app resolution and precedence against sibling routes

Every assertion below is written against **observable behavior** — response
bodies, recorded call order, resolved status codes — and never against route
object shapes. That is deliberate: an assertion about `app.routes` internals
would break on the bump for reasons that do not matter, which is exactly the
mistake that produced the cap in the first place. These tests should survive the
bump; if one fails afterward, a real behavior moved and #265 needs to stop.

Pinned pair when written: fastapi 0.135.4 / starlette 0.49.3.
"""

import pytest
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient


# --------------------------------------------------------------------------
# 1. Middleware ordering across an include_router boundary
# --------------------------------------------------------------------------


def test_middleware_runs_outside_in_and_wraps_included_routes():
    """Middleware order must not depend on whether a route was included.

    Starlette applies middleware outside-in on the way down and inside-out on
    the way back up. A route reached through `include_router` has to see the
    identical stack as one declared on the app directly, or auth/CORS/tenant
    middleware could silently stop covering half the API after a bump.
    """
    calls = []

    app = FastAPI()

    @app.middleware("http")
    async def outer(request, call_next):
        calls.append("outer:enter")
        response = await call_next(request)
        calls.append("outer:exit")
        return response

    @app.middleware("http")
    async def inner(request, call_next):
        calls.append("inner:enter")
        response = await call_next(request)
        calls.append("inner:exit")
        return response

    router = APIRouter()

    @router.get("/included")
    def included_endpoint():
        calls.append("handler")
        return {"ok": True}

    app.include_router(router, prefix="/api")

    @app.get("/direct")
    def direct_endpoint():
        calls.append("handler")
        return {"ok": True}

    client = TestClient(app)

    calls.clear()
    assert client.get("/api/included").status_code == 200
    included_order = list(calls)

    calls.clear()
    assert client.get("/direct").status_code == 200
    direct_order = list(calls)

    # The last-registered middleware is outermost, so `inner` wraps `outer`.
    # The names are positional, not semantic — what is pinned is the shape.
    assert included_order == [
        "inner:enter",
        "outer:enter",
        "handler",
        "outer:exit",
        "inner:exit",
    ]
    assert included_order == direct_order


# --------------------------------------------------------------------------
# 2. dependencies= inheritance from include_router
# --------------------------------------------------------------------------


def test_include_router_dependencies_apply_to_every_child_route():
    """A dependency on `include_router` must cover all of that router's routes.

    This is how whole route groups get gated in this codebase. If inheritance
    regressed, an admin router could start serving unauthenticated.
    """
    seen = []

    def record_group_dependency():
        seen.append("group")

    router = APIRouter()

    @router.get("/first")
    def first():
        return {"route": "first"}

    @router.get("/second")
    def second():
        return {"route": "second"}

    app = FastAPI()
    app.include_router(
        router,
        prefix="/guarded",
        dependencies=[Depends(record_group_dependency)],
    )

    client = TestClient(app)

    seen.clear()
    assert client.get("/guarded/first").json() == {"route": "first"}
    assert seen == ["group"]

    seen.clear()
    assert client.get("/guarded/second").json() == {"route": "second"}
    assert seen == ["group"]


def test_router_dependencies_resolve_before_route_dependencies():
    """Group dependencies run before route-level ones, outermost first.

    Order is load-bearing whenever the outer dependency is the authorization
    check and the inner one assumes an authorized caller.
    """
    order = []

    def app_level():
        order.append("app")

    def group_level():
        order.append("group")

    def route_level():
        order.append("route")

    router = APIRouter(dependencies=[Depends(group_level)])

    @router.get("/thing", dependencies=[Depends(route_level)])
    def thing():
        order.append("handler")
        return {}

    app = FastAPI(dependencies=[Depends(app_level)])
    app.include_router(router)

    client = TestClient(app)
    order.clear()
    assert client.get("/thing").status_code == 200

    assert order == ["app", "group", "route", "handler"]


def test_include_router_dependency_can_reject_the_whole_group():
    """A raising group dependency must block the handler, not just annotate it."""
    handled = []

    def deny():
        raise HTTPException(status_code=403, detail="nope")

    router = APIRouter()

    @router.get("/secret")
    def secret():
        handled.append("ran")
        return {"leaked": True}

    app = FastAPI()
    app.include_router(router, dependencies=[Depends(deny)])

    response = TestClient(app).get("/secret")

    assert response.status_code == 403
    assert response.json() == {"detail": "nope"}
    assert handled == []


# --------------------------------------------------------------------------
# 3. prefix composition
# --------------------------------------------------------------------------


def test_nested_include_router_prefixes_compose_left_to_right():
    """Prefixes concatenate outermost-first through nested includes."""
    leaf = APIRouter()

    @leaf.get("/leaf")
    def leaf_endpoint():
        return {"depth": 3}

    middle = APIRouter()
    middle.include_router(leaf, prefix="/inner")

    app = FastAPI()
    app.include_router(middle, prefix="/outer")

    client = TestClient(app)

    assert client.get("/outer/inner/leaf").json() == {"depth": 3}
    assert client.get("/inner/leaf").status_code == 404
    assert client.get("/leaf").status_code == 404


def test_empty_prefix_leaves_paths_untouched():
    """An empty prefix is a no-op, not an extra path segment."""
    router = APIRouter()

    @router.get("/plain")
    def plain():
        return {"ok": True}

    app = FastAPI()
    app.include_router(router, prefix="")

    client = TestClient(app)

    assert client.get("/plain").status_code == 200
    assert client.get("//plain").status_code in (307, 404)


def test_trailing_slash_paths_stay_distinct_from_bare_paths():
    """`/x` and `/x/` are different routes; FastAPI redirects between them.

    Pinned because tenant-facing clients follow redirects inconsistently, so a
    change from 307 to 404 here would be a visible API break.
    """
    router = APIRouter()

    @router.get("/collection/")
    def collection():
        return {"trailing": True}

    app = FastAPI()
    app.include_router(router, prefix="/api")

    client = TestClient(app)

    assert client.get("/api/collection/").json() == {"trailing": True}

    no_redirect = client.get("/api/collection", follow_redirects=False)
    assert no_redirect.status_code == 307
    assert no_redirect.headers["location"].endswith("/api/collection/")

    assert client.get("/api/collection").json() == {"trailing": True}


def test_same_router_included_under_two_prefixes_serves_both():
    """Including one router twice must produce two independently routable trees.

    Versioned mounts (`/api/v1` and `/api/v2`) depend on this.
    """
    router = APIRouter()

    @router.get("/ping")
    def ping():
        return {"pong": True}

    app = FastAPI()
    app.include_router(router, prefix="/v1")
    app.include_router(router, prefix="/v2")

    client = TestClient(app)

    assert client.get("/v1/ping").json() == {"pong": True}
    assert client.get("/v2/ping").json() == {"pong": True}


# --------------------------------------------------------------------------
# 4. Mounted sub-apps
# --------------------------------------------------------------------------


def test_mounted_subapp_serves_its_own_routes_under_the_mount_path():
    sub = FastAPI()

    @sub.get("/status")
    def sub_status():
        return {"from": "sub"}

    app = FastAPI()

    @app.get("/status")
    def app_status():
        return {"from": "parent"}

    app.mount("/sub", sub)

    client = TestClient(app)

    assert client.get("/status").json() == {"from": "parent"}
    assert client.get("/sub/status").json() == {"from": "sub"}


def test_mount_does_not_shadow_a_sibling_route_at_a_different_path():
    """A mount claims its subtree and nothing outside it."""
    sub = FastAPI()

    @sub.get("/thing")
    def sub_thing():
        return {"from": "sub"}

    app = FastAPI()
    app.mount("/mounted", sub)

    router = APIRouter()

    @router.get("/thing")
    def router_thing():
        return {"from": "router"}

    app.include_router(router, prefix="/included")

    client = TestClient(app)

    assert client.get("/mounted/thing").json() == {"from": "sub"}
    assert client.get("/included/thing").json() == {"from": "router"}
    assert client.get("/thing").status_code == 404


def test_parent_middleware_wraps_mounted_subapp_requests():
    """Parent HTTP middleware DOES run for requests into a mounted sub-app.

    Worth stating plainly because the intuition points the other way: a mounted
    app is a separate ASGI app, so it is easy to assume the parent's middleware
    stops at the mount boundary. It does not — Starlette builds user middleware
    into the parent's ASGI stack *above* routing, so the mount is reached
    through it and sees the unmodified path.

    This is the most security-relevant line in the file. Whatever the parent
    enforces in middleware — auth, tenant scoping, rate limits — currently
    covers mounted sub-apps too. If a FastAPI/starlette bump moved middleware
    below routing, that protection would disappear silently. Pinned so it
    becomes a test failure instead.
    """
    calls = []

    app = FastAPI()

    @app.middleware("http")
    async def tracker(request, call_next):
        calls.append(request.url.path)
        return await call_next(request)

    sub = FastAPI()

    @sub.get("/inside")
    def inside():
        return {"ok": True}

    app.mount("/sub", sub)

    @app.get("/outside")
    def outside():
        return {"ok": True}

    client = TestClient(app)

    calls.clear()
    assert client.get("/outside").status_code == 200
    assert calls == ["/outside"]

    calls.clear()
    assert client.get("/sub/inside").status_code == 200
    assert calls == ["/sub/inside"]


@pytest.mark.parametrize("path", ["/sub", "/sub/"])
def test_mount_root_is_reachable_with_and_without_trailing_slash(path):
    sub = FastAPI()

    @sub.get("/")
    def sub_root():
        return {"root": True}

    app = FastAPI()
    app.mount("/sub", sub)

    response = TestClient(app).get(path)

    assert response.status_code == 200
    assert response.json() == {"root": True}
