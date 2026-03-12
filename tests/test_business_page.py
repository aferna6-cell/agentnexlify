"""Tests for business page endpoints — public page + dashboard settings."""

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
