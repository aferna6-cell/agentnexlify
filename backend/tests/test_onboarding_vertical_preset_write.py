"""Tests for vertical preset injection into the onboarding WRITE path.

Proves:
  (a) A salon_spa tenant gets the preset greeting applied when no explicit
      greeting is provided and no existing widget config value is set.
  (b) An existing tenant-set greeting_message is NOT overwritten by the preset.
  (c) An unknown vertical falls back to generic or leaves the field alone
      (does not raise and does not inject garbage).

Tests target `_apply_vertical_preset_defaults` which is a module-level
pure function in backend/routers/onboarding.py. We import it by running
the module in a way that skips FastAPI route-registration inspection.

Run with:
    .venv/bin/python -m pytest backend/tests/test_onboarding_vertical_preset_write.py -q --noconftest
"""

import os
import sys
import importlib
import types

os.environ.setdefault("TESTING", "1")


# ---------------------------------------------------------------------------
# Import the helper directly without triggering FastAPI route registration
# ---------------------------------------------------------------------------

def _get_apply_fn():
    """Return the _apply_vertical_preset_defaults function via a normal import.

    onboarding.py imports cleanly under the project venv (the earlier fastapi-
    mocking shim broke Pydantic model resolution with
    'no signature found for builtin type dict'). Direct import is correct.
    """
    from backend.routers.onboarding import _apply_vertical_preset_defaults
    return _apply_vertical_preset_defaults


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestApplyVerticalPresetDefaults:
    """Unit-test the helper that merges preset greeting into widget_updates."""

    def setup_method(self):
        # Clear cached module so each test gets a fresh import if needed
        sys.modules.pop("backend.routers.onboarding", None)

    def _fn(self):
        return _get_apply_fn()

    # --- (a) salon preset is applied when no explicit or existing value ---

    def test_salon_preset_greeting_applied_when_no_explicit_value(self):
        """Salon vertical preset greeting fills in when tenant has no existing greeting."""
        fn = self._fn()

        # Start with the business_profiles.py generic default (what the code
        # would have placed before this feature)
        widget_updates = {
            "bot_name": "Salon Assistant",
            "primary_color": "#db2777",
            "greeting_message": "Hello from business_profiles!",
            "position": "bottom-right",
        }

        fn(
            widget_updates=widget_updates,
            business_type="salon_spa",
            explicit_greeting=None,
            existing_greeting=None,
        )

        greeting = widget_updates.get("greeting_message", "")
        assert greeting, "greeting_message should not be empty after preset applied"
        # The salon_spa YAML greeting talks about booking / appointment / service
        assert any(
            kw in greeting.lower()
            for kw in ("book", "appointment", "service", "availability", "pricing")
        ), f"Expected salon-flavoured greeting, got: {greeting!r}"
        # Crucially: must NOT be the generic business_profiles.py placeholder
        assert greeting != "Hello from business_profiles!", (
            f"Preset should override the generic business_profiles default; "
            f"got: {greeting!r}"
        )

    # --- (b) existing tenant value is NOT overwritten ---

    def test_existing_greeting_not_overwritten(self):
        """Existing DB greeting must survive preset application unchanged."""
        fn = self._fn()

        tenant_greeting = "Welcome to Maria's Salon! How can I help you?"
        widget_updates = {
            "greeting_message": tenant_greeting,
        }

        fn(
            widget_updates=widget_updates,
            business_type="salon_spa",
            explicit_greeting=None,
            existing_greeting=tenant_greeting,
        )

        assert widget_updates["greeting_message"] == tenant_greeting, (
            f"Existing tenant greeting was overwritten! Got: {widget_updates['greeting_message']!r}"
        )

    def test_explicit_request_value_not_overwritten(self):
        """An explicit value in the request body is never replaced by preset."""
        fn = self._fn()

        explicit_greeting = "Come in and relax at our spa!"
        widget_updates = {
            "greeting_message": explicit_greeting,
        }

        fn(
            widget_updates=widget_updates,
            business_type="salon_spa",
            explicit_greeting=explicit_greeting,
            existing_greeting=None,
        )

        assert widget_updates["greeting_message"] == explicit_greeting, (
            f"Explicit request greeting was overwritten. Got: {widget_updates['greeting_message']!r}"
        )

    # --- (c) unknown vertical falls back gracefully ---

    def test_unknown_vertical_does_not_raise(self):
        """Unknown vertical falls back to generic or leaves greeting unchanged — never raises."""
        fn = self._fn()

        original_greeting = "Hello from business_profiles!"
        widget_updates = {
            "greeting_message": original_greeting,
        }

        # Must not raise
        fn(
            widget_updates=widget_updates,
            business_type="completely_unknown_vertical_xyz",
            explicit_greeting=None,
            existing_greeting=None,
        )

        # greeting_message must still be a non-empty string
        result = widget_updates.get("greeting_message")
        assert isinstance(result, str) and result, (
            f"greeting_message must remain a non-empty string; got {result!r}"
        )

    def test_unknown_vertical_does_not_insert_garbage(self):
        """Unknown vertical either uses generic preset or keeps original — never empty string."""
        fn = self._fn()

        widget_updates = {"greeting_message": "Generic default."}

        fn(
            widget_updates=widget_updates,
            business_type="unknown_xyz_99999",
            explicit_greeting=None,
            existing_greeting=None,
        )

        result = widget_updates["greeting_message"]
        assert isinstance(result, str) and result.strip(), (
            f"greeting_message must not be empty or whitespace-only; got {result!r}"
        )

    def test_none_business_type_does_not_raise(self):
        """None business_type is handled gracefully (generic fallback or original kept)."""
        fn = self._fn()

        widget_updates = {"greeting_message": "Hello!"}

        fn(
            widget_updates=widget_updates,
            business_type=None,
            explicit_greeting=None,
            existing_greeting=None,
        )

        result = widget_updates.get("greeting_message")
        assert isinstance(result, str) and result

    # --- Additional verticals: plumber_hvac and dental ---

    def test_plumber_hvac_preset_applied_when_no_existing_value(self):
        """plumber_hvac vertical preset greeting replaces business_profiles default."""
        fn = self._fn()

        original = "Hello from business_profiles!"
        widget_updates = {"greeting_message": original}

        fn(
            widget_updates=widget_updates,
            business_type="plumber_hvac",
            explicit_greeting=None,
            existing_greeting=None,
        )

        greeting = widget_updates["greeting_message"]
        assert greeting != original, (
            f"Expected plumber_hvac preset to override business_profiles default; "
            f"got: {greeting!r}"
        )
        assert greeting, "greeting_message should not be empty"

    def test_dental_preset_applied_when_no_existing_value(self):
        """dental vertical preset greeting replaces business_profiles default."""
        fn = self._fn()

        original = "Hello from business_profiles!"
        widget_updates = {"greeting_message": original}

        fn(
            widget_updates=widget_updates,
            business_type="dental",
            explicit_greeting=None,
            existing_greeting=None,
        )

        greeting = widget_updates["greeting_message"]
        assert greeting != original, (
            f"Expected dental preset to override business_profiles default; "
            f"got: {greeting!r}"
        )
        assert greeting, "greeting_message should not be empty"

    def test_generic_preset_applied_for_unlisted_vertical_when_no_existing(self):
        """For a vertical not in the YAML, generic preset greeting is used as fallback."""
        fn = self._fn()

        original = "Hello from business_profiles!"
        widget_updates = {"greeting_message": original}

        fn(
            widget_updates=widget_updates,
            business_type="some_unlisted_vertical",
            explicit_greeting=None,
            existing_greeting=None,
        )

        result = widget_updates["greeting_message"]
        # Either the generic preset was used (non-empty) or the original was kept
        assert isinstance(result, str) and result.strip(), (
            f"Expected a non-empty greeting; got {result!r}"
        )

    # --- tenant-level fields: services + business_hours_display ---

    def test_tenant_services_and_hours_applied_when_empty(self):
        """salon preset fills business_services + business_hours_display when unset."""
        fn = self._fn()
        tenant_updates = {}
        fn(
            widget_updates={},
            business_type="salon",
            explicit_greeting=None,
            existing_greeting=None,
            tenant_updates=tenant_updates,
            explicit_services=None,
            existing_services=None,
            explicit_hours_display=None,
            existing_hours_display=None,
        )
        assert tenant_updates.get("business_services"), "expected preset services applied"
        assert tenant_updates.get("business_hours_display"), "expected preset hours applied"

    def test_explicit_services_not_overwritten(self):
        """A tenant-supplied services value blocks the preset."""
        fn = self._fn()
        tenant_updates = {}
        fn(
            widget_updates={},
            business_type="salon",
            explicit_greeting=None,
            existing_greeting=None,
            tenant_updates=tenant_updates,
            explicit_services=["my own service"],
            existing_services=None,
            explicit_hours_display=None,
            existing_hours_display="Mon-Fri 9-5",
        )
        assert "business_services" not in tenant_updates
        assert "business_hours_display" not in tenant_updates

    def test_no_tenant_updates_dict_skips_tenant_fields(self):
        """Without a tenant_updates dict, only widget greeting is touched (back-compat)."""
        fn = self._fn()
        widget_updates = {}
        fn(
            widget_updates=widget_updates,
            business_type="salon",
            explicit_greeting=None,
            existing_greeting=None,
        )
        assert widget_updates.get("greeting_message")
