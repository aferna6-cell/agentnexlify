"""Smoke test for the analytics router package split (commit 1f69417).

`backend/routers/analytics.py` (2,023 lines, 14 endpoints) was split into a
package `backend/routers/analytics/` with 5 sub-modules. Route registration
order, URL paths, and HTTP-layer contract must match the pre-split behavior.

This test hits every one of the 14 paths through the real ASGI app using
the project's conftest fixtures (JWT auth + mocked Supabase). It asserts:

  1. Every route is REGISTERED (status_code != 404)
  2. Every route is accessible with a valid JWT (status_code != 401/403)
  3. Handler executes at the HTTP layer (if it 500s on Mock'd data, that's
     handler logic assuming a real DB response shape — pre-existing
     behavior, not caused by the split since no handler code was changed).

Why not assert 200 uniformly: the shared MagicMock Supabase returns
MagicMock objects that don't satisfy every handler's expectations (some
expect `.data or []` to iterate; MagicMock.data is itself a MagicMock, not
a list). That's a test-fixture limitation, not a refactor regression.
A handler that 500s under Mock'd data today would have 500'd before the
split too because zero handler code changed — only module boundaries.

If this smoke ever fires with a fresh 404 on one of the 14 paths, the
split lost a route. That's the regression signal to catch.
"""

import pytest


# 14 paths — identical order/spelling to pre-split `git log --grep="split analytics"`
# All parametrized against the same tenant_id used by the auth_headers fixture.
ANALYTICS_ROUTES = [
    "/api/v1/analytics/{tid}/overview",
    "/api/v1/analytics/{tid}/conversations",
    "/api/v1/analytics/{tid}/leads",
    "/api/v1/analytics/{tid}/widget",
    "/api/v1/analytics/{tid}/response-times",
    "/api/v1/analytics/{tid}/missed-opportunities",
    "/api/v1/analytics/{tid}/missed-calls",
    "/api/v1/analytics/{tid}/ai-insights",
    "/api/v1/analytics/{tid}/lead-sources",
    "/api/v1/analytics/{tid}/kpi-deltas",
    "/api/v1/analytics/{tid}/control-center",
    "/api/v1/analytics/{tid}/health",
    "/api/v1/analytics/{tid}/snapshot",
    "/api/v1/analytics/{tid}/recovery-stats",
    # Added post-split: Front Desk Health dashboard card endpoint.
    "/api/v1/analytics/{tid}/front-desk-health",
    # Added 2026-07 (GH #453): lead attribution breakdown for AttributionPage.
    "/api/v1/analytics/{tid}/attribution",
]

TENANT_ID = "00000000-0000-0000-0000-000000000001"


def test_all_analytics_routes_registered(client, auth_headers):
    """Sanity check: the package's __init__.py wired every route into app.

    Count grows as endpoints are added (front-desk-health added 2026-06). The
    regression this guards against is a route LOST or duplicated, caught by the
    exact path-set comparison below.
    """
    from backend.routers import analytics
    expected = len(ANALYTICS_ROUTES)
    assert len(analytics.router.routes) == expected, (
        f"Expected {expected} routes in analytics package, got "
        f"{len(analytics.router.routes)}. A route was lost or duplicated."
    )
    # Registered paths match the parametrized list
    got = sorted(r.path for r in analytics.router.routes)
    want = sorted(p.format(tid="{tenant_id}") for p in ANALYTICS_ROUTES)
    assert got == want, (
        f"Route path drift post-split.\n"
        f"  Got:  {got}\n"
        f"  Want: {want}"
    )


@pytest.mark.parametrize("path_template", ANALYTICS_ROUTES)
def test_route_reaches_handler(client, auth_headers, path_template):
    """Each route must pass auth + reach its handler (no 404, no 401/403).

    Whatever status the handler returns (200 on simple ones, 500 where
    the MagicMock Supabase shape trips a real-data assumption) is fine —
    the split only moved code, did not change it. What we're proving
    here is that the URL → handler binding survived.
    """
    url = path_template.format(tid=TENANT_ID)
    response = client.get(url, headers=auth_headers)

    # 404 would mean the route is not registered — the refactor regression
    assert response.status_code != 404, (
        f"Route {url} returned 404 — split did not register this path. "
        f"Response body: {response.text[:200]}"
    )
    # 401/403 would mean the JWT didn't match or auth dep broke during split
    assert response.status_code not in (401, 403), (
        f"Route {url} returned {response.status_code} — auth dependency "
        f"broke in the split. Response: {response.text[:200]}"
    )
    # 405 would mean method mismatch — shouldn't happen since all are GET
    assert response.status_code != 405, (
        f"Route {url} returned 405 — HTTP method binding wrong."
    )
