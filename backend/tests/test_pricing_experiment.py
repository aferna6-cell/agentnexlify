"""Tests for the pricing page A/B experiment (rubric 9.3).

Covers:
  - deterministic variant assignment (same visitor_id → same variant, both
    variants reachable across visitor ids)
  - invalid visitor_id rejected
  - event recorded with server-derived variant
  - invalid event type rejected (422)
  - DB error swallowed (analytics never break the page)
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

os.environ.setdefault("TESTING", "1")

from backend.limiter import limiter
from backend.routers.pricing_experiment import VARIANTS, assign_variant


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """30/minute on both endpoints — reset shared limiter state between tests."""
    limiter.reset()
    yield


_VID = "11111111-2222-3333-4444-555555555555"


class TestAssignment:
    def test_deterministic(self):
        assert assign_variant(_VID) == assign_variant(_VID)

    def test_both_variants_reachable(self):
        seen = {assign_variant(f"visitor-{i:04d}") for i in range(200)}
        assert seen == set(VARIANTS)

    def test_get_endpoint_returns_same_variant(self, client):
        first = client.get(f"/api/v1/public/pricing-experiment?visitor_id={_VID}")
        second = client.get(f"/api/v1/public/pricing-experiment?visitor_id={_VID}")
        assert first.status_code == 200
        assert first.json()["variant"] in VARIANTS
        assert first.json()["variant"] == second.json()["variant"]

    def test_invalid_visitor_id_rejected(self, client):
        resp = client.get("/api/v1/public/pricing-experiment?visitor_id=short")
        assert resp.status_code == 422

    def test_visitor_id_with_bad_chars_rejected(self, client):
        resp = client.get(
            "/api/v1/public/pricing-experiment?visitor_id=abcd1234%3Bdrop%20table"
        )
        assert resp.status_code == 422


class TestEvents:
    def test_event_recorded_with_server_variant(self, client, mock_supabase):
        resp = client.post(
            "/api/v1/public/pricing-experiment/event",
            json={"visitor_id": _VID, "event": "cta_click", "plan": "free"},
        )
        assert resp.status_code == 202
        assert resp.json() == {"recorded": True}
        inserted = mock_supabase.table.return_value.insert.call_args[0][0]
        assert inserted["visitor_id"] == _VID
        assert inserted["event"] == "cta_click"
        assert inserted["plan"] == "free"
        # Variant is derived server-side, never trusted from the client
        assert inserted["variant"] == assign_variant(_VID)

    def test_view_event_without_plan(self, client, mock_supabase):
        resp = client.post(
            "/api/v1/public/pricing-experiment/event",
            json={"visitor_id": _VID, "event": "view"},
        )
        assert resp.status_code == 202
        inserted = mock_supabase.table.return_value.insert.call_args[0][0]
        assert inserted["plan"] is None

    def test_invalid_event_rejected(self, client):
        resp = client.post(
            "/api/v1/public/pricing-experiment/event",
            json={"visitor_id": _VID, "event": "purchase"},
        )
        assert resp.status_code == 422

    def test_invalid_plan_rejected(self, client):
        resp = client.post(
            "/api/v1/public/pricing-experiment/event",
            json={"visitor_id": _VID, "event": "view", "plan": "foundation"},
        )
        assert resp.status_code == 422

    def test_db_error_swallowed(self, client, mock_supabase):
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = (
            RuntimeError("db down")
        )
        resp = client.post(
            "/api/v1/public/pricing-experiment/event",
            json={"visitor_id": _VID, "event": "view"},
        )
        assert resp.status_code == 202
        assert resp.json() == {"recorded": False}
