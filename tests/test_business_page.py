"""Tests for business page endpoints — public page + dashboard settings."""

import os
os.environ["TESTING"] = "1"

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.routers.business_page import (
    _allowed_tier_fields,
    _ensure_unique_slug,
    _sanitize_slug,
    _slugify,
    _strip_disallowed_tier_fields,
    VALID_COLOR_THEMES,
    VALID_FONTS,
)


# ── Slug helpers ─────────────────────────────────────────────


class TestSlugify:
    def test_basic(self):
        assert _slugify("My Business") == "my-business"

    def test_unicode(self):
        assert _slugify("Café Délice") == "cafe-delice"

    def test_special_chars(self):
        assert _slugify("Joe's Auto & Repair!") == "joe-s-auto-repair"

    def test_empty(self):
        assert _slugify("") == "business"

    def test_numbers(self):
        assert _slugify("Studio 54") == "studio-54"

    def test_leading_trailing_dashes(self):
        assert _slugify("--hello--") == "hello"


class TestSanitizeSlug:
    def test_valid(self):
        assert _sanitize_slug("my-business") == "my-business"

    def test_uppercase(self):
        assert _sanitize_slug("My-Business") == "my-business"

    def test_strips_slashes(self):
        assert _sanitize_slug("/my-biz/") == "my-biz"

    def test_too_short(self):
        with pytest.raises(Exception) as exc_info:
            _sanitize_slug("a")
        assert "at least 2" in str(exc_info.value.detail)

    def test_too_long(self):
        with pytest.raises(Exception) as exc_info:
            _sanitize_slug("x" * 81)
        assert "80 characters" in str(exc_info.value.detail)


class TestEnsureUniqueSlug:
    def test_unique_slug_returns_as_is(self, mock_supabase):
        mock_supabase.set_table_data("tenants", [])
        result = _ensure_unique_slug(mock_supabase, "my-biz")
        assert result == "my-biz"

    def test_conflict_appends_number(self, mock_supabase):
        """When slug exists, should try slug-2, slug-3, etc."""
        call_count = 0
        original_table = mock_supabase.table

        def table_side_effect(name):
            nonlocal call_count
            t = original_table(name)
            if name == "tenants":
                call_count += 1
                # First call finds a conflict, second is clear
                if call_count <= 1:
                    t._data = [{"id": "existing-tenant"}]
                else:
                    t._data = []
            return t

        mock_supabase.table = table_side_effect
        result = _ensure_unique_slug(mock_supabase, "my-biz")
        assert result == "my-biz-2"


# ── Tier gating ──────────────────────────────────────────────


class TestTierGating:
    def test_free_plan_gets_no_tier_fields(self):
        allowed = _allowed_tier_fields("free")
        assert len(allowed) == 0

    def test_growth_plan_gets_no_tier_fields(self):
        allowed = _allowed_tier_fields("growth")
        assert len(allowed) == 0

    def test_professional_plan_gets_theme_and_seo(self):
        allowed = _allowed_tier_fields("professional")
        assert "bp_color_theme" in allowed
        assert "bp_font_family" in allowed
        assert "bp_hide_powered_by" in allowed
        assert "bp_meta_title" in allowed
        assert "bp_custom_css" not in allowed

    def test_enterprise_plan_gets_all(self):
        allowed = _allowed_tier_fields("enterprise")
        assert "bp_color_theme" in allowed
        assert "bp_custom_css" in allowed

    def test_strip_disallowed_free(self):
        updates = {"business_description": "test", "bp_color_theme": "ocean", "bp_custom_css": ".foo{}"}
        result = _strip_disallowed_tier_fields(updates, "free")
        assert "business_description" in result
        assert "bp_color_theme" not in result
        assert "bp_custom_css" not in result

    def test_strip_disallowed_professional(self):
        updates = {"bp_color_theme": "ocean", "bp_custom_css": ".foo{}"}
        result = _strip_disallowed_tier_fields(updates, "professional")
        assert "bp_color_theme" in result
        assert "bp_custom_css" not in result  # enterprise only


# ── Public endpoint logic ────────────────────────────────────


class TestBusinessPagePublicData:
    """Test the data mapping for the public business page."""

    def test_valid_color_themes(self):
        assert "default" in VALID_COLOR_THEMES
        assert "ocean" in VALID_COLOR_THEMES
        assert len(VALID_COLOR_THEMES) == 10

    def test_valid_fonts(self):
        assert "Inter" in VALID_FONTS
        assert "Poppins" in VALID_FONTS
        assert len(VALID_FONTS) == 10

    def test_plan_rank_ordering(self):
        from backend.routers.business_page import _PLAN_RANK
        assert _PLAN_RANK["free"] < _PLAN_RANK["growth"]
        assert _PLAN_RANK["growth"] < _PLAN_RANK["professional"]
        assert _PLAN_RANK["professional"] < _PLAN_RANK["enterprise"]


# =========================================================================
# Integration tests: HTTP endpoints via TestClient
# =========================================================================


def _setup_table_mock(db_mock, table_responses):
    """Configure db_mock.table() to return different data per table name."""
    call_counts = {}

    def mock_table(name):
        call_counts.setdefault(name, 0)
        call_counts[name] += 1

        table = MagicMock()
        data = table_responses.get(name, [])

        if data and isinstance(data[0], list):
            idx = min(call_counts[name] - 1, len(data) - 1)
            current_data = data[idx]
        else:
            current_data = data

        for method in [
            "select", "insert", "update", "delete", "eq", "neq",
            "gte", "lte", "gt", "lt", "limit", "order", "ilike",
            "in_", "is_", "or_", "contains", "not_",
        ]:
            getattr(table, method).return_value = table

        result = MagicMock()
        result.data = current_data
        result.count = len(current_data) if current_data else 0
        table.execute.return_value = result

        return table

    db_mock.table = mock_table


@pytest.fixture
def http_client(mock_settings):
    """Create a FastAPI TestClient with mocked Supabase for endpoint tests."""
    mock_settings.sentry_dsn = None
    mock_settings.supabase_service_key = "fake-key"

    db_mock = MagicMock()
    patches = [
        patch("backend.models.database.get_supabase", return_value=db_mock),
        patch("backend.routers.auth.get_service_supabase", return_value=db_mock),
        patch("backend.routers.auth.settings", mock_settings),
        patch("backend.routers.widget_chat.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_config.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_lead.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_booking.get_service_supabase", return_value=db_mock),
        patch("backend.routers.widget_chat_helpers.get_service_supabase", return_value=db_mock),
        patch("backend.routers.business_page.get_service_supabase", return_value=db_mock),
        patch("backend.routers.team.get_service_supabase", return_value=db_mock),
        patch("backend.services.activity.get_service_supabase", return_value=db_mock),
        patch("backend.services.webhook_dispatcher.get_service_supabase", return_value=db_mock),
        patch("backend.services.lead_scoring.get_service_supabase", return_value=db_mock),
    ]
    for p in patches:
        p.start()

    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)

    yield client, db_mock

    try:
        from backend.routers.widget_chat_helpers import _cache
        _cache.clear()
    except Exception:
        pass

    for p in patches:
        p.stop()


# ── Public business page endpoint tests ─────────────────────


class TestBusinessPageEndpoints:
    """Integration tests for GET /biz/{slug} endpoint."""

    def test_business_page_valid_slug(self, http_client):
        """GET /biz/{slug} with a valid, enabled slug returns 200 with page data."""
        client, db_mock = http_client

        _setup_table_mock(db_mock, {
            "tenants": [{
                "id": "tenant-biz-001",
                "business_name": "Joe's Plumbing",
                "business_description": "Expert plumbers in Denver",
                "business_phone": "+15559876543",
                "business_address": "123 Main St",
                "business_city": "Denver",
                "business_state": "CO",
                "business_hours_display": "Mon-Fri 9-5",
                "business_logo_url": None,
                "business_cover_url": None,
                "business_page_enabled": True,
                "business_services": ["Pipe repair", "Drain cleaning"],
                "plan": "growth",
                "bp_color_theme": "ocean",
                "bp_font_family": None,
                "bp_hide_powered_by": False,
                "bp_custom_css": None,
                "bp_meta_title": None,
                "bp_meta_description": None,
            }],
            "widget_configs": [{
                "api_key": "anx_biz_key",
                "primary_color": "#FF6600",
                "bot_name": "Joe Bot",
                "greeting_message": "Need a plumber?",
                "position": "bottom-right",
            }],
        })

        response = client.get("/biz/joes-plumbing")
        assert response.status_code == 200
        data = response.json()
        assert data["business_name"] == "Joe's Plumbing"
        assert data["description"] == "Expert plumbers in Denver"
        assert data["widget_api_key"] == "anx_biz_key"
        assert data["widget_bot_name"] == "Joe Bot"
        assert data["services"] == ["Pipe repair", "Drain cleaning"]

    def test_business_page_nonexistent_slug(self, http_client):
        """GET /biz/{slug} with a slug that does not exist returns 404."""
        client, db_mock = http_client

        _setup_table_mock(db_mock, {
            "tenants": [],  # no matching tenant
        })

        response = client.get("/biz/nonexistent-business-xyz")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_business_page_special_chars(self, http_client):
        """GET /biz/{slug} with special chars in the slug is handled gracefully.

        FastAPI will URL-decode the path parameter. The endpoint queries the DB
        with whatever string arrives. Special characters should not cause a 500.
        """
        client, db_mock = http_client

        _setup_table_mock(db_mock, {
            "tenants": [],  # no match expected
        })

        # URL-encoded special characters; FastAPI will decode them
        response = client.get("/biz/test%20slug%21%40%23")
        assert response.status_code == 404
        # The important thing is no 500 error
        assert "not found" in response.json()["detail"].lower()


# ── Team invite validation endpoint test ────────────────────


class TestTeamInviteValidate:
    """Test GET /api/v1/team/invite/{token} — public invite validation."""

    def test_team_invite_validate(self, http_client):
        """GET /api/v1/team/invite/{token} with a valid token returns member info."""
        client, db_mock = http_client

        _setup_table_mock(db_mock, {
            "team_members": [{
                "email": "invited@example.com",
                "role": "admin",
                "tenant_id": "tenant-team-001",
                "invite_accepted": False,
            }],
            "tenants": [{
                "business_name": "Team Test Biz",
            }],
        })

        response = client.get("/api/v1/team/invite/some-valid-token-abc123")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "invited@example.com"
        assert data["role"] == "admin"
        assert data["business_name"] == "Team Test Biz"
