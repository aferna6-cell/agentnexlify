"""Route registration for the AURA-inspired additions (2026-08-06).

Proves main.py actually mounts the new routers — a missed include_router
is a silent 404 in prod.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _app_paths():
    from backend.main import app

    return {getattr(r, "path", "") for r in app.routes}


def test_insights_routes_registered():
    paths = _app_paths()
    assert "/api/v1/insights/{tenant_id}/daily-focus" in paths
    assert "/api/v1/insights/{tenant_id}/response-score" in paths


def test_appointment_brief_routes_registered():
    paths = _app_paths()
    assert "/api/v1/appointments/{tenant_id}/{appointment_id}/brief" in paths
    assert "/api/v1/appointments/{tenant_id}/{appointment_id}/follow-up-draft" in paths


def test_billing_ai_usage_route_registered():
    paths = _app_paths()
    assert "/api/v1/billing/ai-usage" in paths
