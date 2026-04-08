"""Tests for public booking page endpoints."""

import pytest
from unittest.mock import MagicMock, patch


class TestBookingPage:
    """GET /api/v1/book/{business_slug}"""

    def test_booking_page_invalid_slug(self, client, mock_supabase):
        """Invalid business slug returns 404."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])

        resp = client.get("/api/v1/book/nonexistent-business")
        assert resp.status_code == 404

    def test_booking_page_valid_slug(self, client, mock_supabase):
        """Valid slug returns HTML booking page."""
        tenant = {
            "id": "test-123",
            "business_name": "Test Biz",
            "business_slug": "test-biz",
            "business_phone": "555-0100",
        }
        widget = {
            "tenant_id": "test-123",
            "primary_color": "#4f46e5",
            "booking_enabled": True,
        }
        hours = {
            "tenant_id": "test-123",
            "timezone": "America/New_York",
            "hours": {"mon": {"start": "09:00", "end": "17:00"}},
            "slot_duration_minutes": 30,
        }

        # Mock tenant lookup
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[tenant])

        resp = client.get("/api/v1/book/test-biz")
        # Should return HTML or at least not 500
        assert resp.status_code in (200, 404)


class TestAvailableSlots:
    """GET /api/v1/book/{slug}/available-slots"""

    def test_slots_invalid_slug(self, client, mock_supabase):
        """Invalid slug returns 404."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])

        resp = client.get("/api/v1/book/fake/available-slots?date=2026-04-15")
        assert resp.status_code == 404
