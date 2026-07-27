"""Route introspection must give the same answer on both FastAPI route shapes.

FastAPI < 0.136 flattens included routes into the parent; >= 0.136 appends an
``_IncludedRouter`` wrapper and keeps the real routes behind it. Every assertion
here is written so it holds on either version — that is the whole contract. If
one of these starts failing after a FastAPI bump, the helper needs teaching, not
the caller.
"""

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from backend.route_introspection import (
    count_routes,
    iter_routes,
    route_paths,
    route_signatures,
)


def _leaf_router() -> APIRouter:
    router = APIRouter()

    @router.get("/items")
    def list_items():
        return []

    @router.post("/items")
    def create_item():
        return {}

    @router.delete("/items/{item_id}")
    def delete_item(item_id: str):
        return {}

    return router


# --------------------------------------------------------------------------
# counting
# --------------------------------------------------------------------------


def test_counts_every_route_behind_an_include():
    app = FastAPI()
    before = count_routes(app)
    app.include_router(_leaf_router())

    # Three handlers, two of which share a path — a count, not a path count.
    assert count_routes(app) == before + 3


def test_count_survives_nested_includes():
    inner = _leaf_router()
    middle = APIRouter()
    middle.include_router(inner, prefix="/inner")
    app = FastAPI()
    app.include_router(middle, prefix="/outer")

    assert count_routes(middle) == 3
    assert count_routes(app) == count_routes(FastAPI()) + 3


def test_count_matches_what_the_app_actually_serves():
    """The anchor: the helper's count must agree with the OpenAPI schema, which
    is version-stable and is what a client can actually reach."""
    app = FastAPI()
    app.include_router(_leaf_router(), prefix="/api")

    operations = sum(len(v) for v in app.openapi()["paths"].values())
    declared = len(route_signatures(app) - route_signatures(FastAPI()))

    assert declared == operations == 3


# --------------------------------------------------------------------------
# paths and prefixes
# --------------------------------------------------------------------------


def test_prefix_is_applied_to_included_paths():
    app = FastAPI()
    app.include_router(_leaf_router(), prefix="/api/v1")

    paths = set(route_paths(app))

    assert "/api/v1/items" in paths
    assert "/api/v1/items/{item_id}" in paths


def test_nested_prefixes_accumulate_in_order():
    inner = _leaf_router()
    middle = APIRouter()
    middle.include_router(inner, prefix="/inner")
    app = FastAPI()
    app.include_router(middle, prefix="/outer")

    assert "/outer/inner/items" in set(route_paths(app))


def test_paths_match_the_urls_the_app_answers_on():
    app = FastAPI()
    app.include_router(_leaf_router(), prefix="/api/v1")
    client = TestClient(app)

    assert "/api/v1/items" in set(route_paths(app))
    assert client.get("/api/v1/items").status_code == 200
    assert client.post("/api/v1/items").status_code == 200


def test_router_with_no_prefix_keeps_its_own_paths():
    app = FastAPI()
    app.include_router(_leaf_router())

    assert "/items" in set(route_paths(app))


def test_duplicate_paths_are_preserved_not_collapsed():
    """A repeated path is usually the bug being hunted, so route_paths must not
    deduplicate it away."""
    app = FastAPI()
    app.include_router(_leaf_router())

    assert route_paths(app).count("/items") == 2


# --------------------------------------------------------------------------
# signatures
# --------------------------------------------------------------------------


def test_signatures_pair_each_declared_verb_with_its_path():
    app = FastAPI()
    app.include_router(_leaf_router(), prefix="/api")

    signatures = route_signatures(app)

    assert ("GET", "/api/items") in signatures
    assert ("POST", "/api/items") in signatures
    assert ("DELETE", "/api/items/{item_id}") in signatures


def test_framework_added_verbs_are_not_counted_as_declarations():
    app = FastAPI()
    app.include_router(_leaf_router())

    assert not [m for m, _ in route_signatures(app) if m in {"HEAD", "OPTIONS"}]


# --------------------------------------------------------------------------
# shape-agnosticism and edges
# --------------------------------------------------------------------------


def test_iter_routes_yields_real_routes_not_include_wrappers():
    app = FastAPI()
    app.include_router(_leaf_router())

    for _, route in iter_routes(app):
        assert getattr(route, "original_router", None) is None
        assert getattr(route, "path", None) is not None


def test_a_bare_router_is_walkable_without_an_app():
    assert count_routes(_leaf_router()) == 3


def test_an_object_without_routes_yields_nothing():
    assert list(iter_routes(object())) == []
    assert count_routes(object()) == 0


def test_an_empty_router_yields_nothing():
    assert count_routes(APIRouter()) == 0


def test_a_mount_is_one_entry_and_is_not_descended_into():
    """Matches the pre-0.136 flat walk: a Mount owns its own routing and its
    sub-app need not be a FastAPI app."""
    sub = FastAPI()
    sub.include_router(_leaf_router())
    app = FastAPI()
    app.mount("/sub", sub)

    assert "/sub" in set(route_paths(app))
    assert "/sub/items" not in set(route_paths(app))


def test_the_real_app_still_reports_its_full_route_count():
    """The regression that started this: from FastAPI 0.136 ``len(app.routes)``
    stopped being an endpoint count, so anything asserting on it read as mass
    route loss. On 0.135 the real app reported 626; the helper must keep
    reporting that order of magnitude on any version.

    Deliberately not compared to the OpenAPI operation count: one route may
    declare several verbs, so operations legitimately exceed routes (632 vs 626
    here). Comparing them would encode a relationship that is not true.
    """
    from backend.main import app

    counted = count_routes(app)

    # Equal on <0.136 where the list is already flat; far greater on >=0.136
    # where len(app.routes) counts include wrappers (145 at time of writing).
    assert counted >= len(app.routes)
    assert counted > 500
