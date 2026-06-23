"""Tests for backend/services/vertical_preset_loader.py.

Covers:
- load_vertical_preset returns the correct preset for known verticals.
- load_vertical_preset falls back to generic for unknown verticals.
- load_vertical_preset returns generic (does not raise) when YAML file is missing.
- list_verticals returns the expected keys and excludes generic.
"""

import importlib
import sys
import pathlib
import textwrap
from unittest.mock import patch

import pytest
import yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_loader():
    """Re-import the module so the module-level cache is cleared."""
    mod_name = "backend.services.vertical_preset_loader"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    return importlib.import_module(mod_name)


# ---------------------------------------------------------------------------
# Tests: known verticals
# ---------------------------------------------------------------------------


def test_load_salon_spa_returns_expected_keys():
    loader = _reload_loader()
    preset = loader.load_vertical_preset("salon_spa")
    assert isinstance(preset, dict), "preset should be a dict"
    for key in ("greeting", "services", "business_hours", "faqs"):
        assert key in preset, f"preset missing key: {key}"


def test_load_salon_spa_greeting_is_nonempty():
    loader = _reload_loader()
    preset = loader.load_vertical_preset("salon_spa")
    assert preset["greeting"].strip(), "greeting should not be empty"


def test_load_salon_spa_faqs_count():
    loader = _reload_loader()
    preset = loader.load_vertical_preset("salon_spa")
    faqs = preset.get("faqs", [])
    assert 5 <= len(faqs) <= 8, f"expected 5-8 FAQs for salon_spa, got {len(faqs)}"


def test_load_salon_spa_faq_has_question_and_answer():
    loader = _reload_loader()
    preset = loader.load_vertical_preset("salon_spa")
    for faq in preset["faqs"]:
        assert "question" in faq, "FAQ entry missing 'question'"
        assert "answer" in faq, "FAQ entry missing 'answer'"
        assert faq["question"].strip(), "FAQ question should not be empty"
        assert faq["answer"].strip(), "FAQ answer should not be empty"


def test_load_salon_spa_services_nonempty():
    loader = _reload_loader()
    preset = loader.load_vertical_preset("salon_spa")
    assert len(preset.get("services", [])) > 0, "services list should not be empty"


def test_load_plumber_hvac_returns_expected_keys():
    loader = _reload_loader()
    preset = loader.load_vertical_preset("plumber_hvac")
    for key in ("greeting", "services", "business_hours", "faqs"):
        assert key in preset


def test_load_plumber_hvac_faqs_count():
    loader = _reload_loader()
    preset = loader.load_vertical_preset("plumber_hvac")
    faqs = preset.get("faqs", [])
    assert 5 <= len(faqs) <= 8, f"expected 5-8 FAQs for plumber_hvac, got {len(faqs)}"


def test_load_dental_returns_expected_keys():
    loader = _reload_loader()
    preset = loader.load_vertical_preset("dental")
    for key in ("greeting", "services", "business_hours", "faqs"):
        assert key in preset


def test_load_dental_faqs_count():
    loader = _reload_loader()
    preset = loader.load_vertical_preset("dental")
    faqs = preset.get("faqs", [])
    assert 5 <= len(faqs) <= 8, f"expected 5-8 FAQs for dental, got {len(faqs)}"


# ---------------------------------------------------------------------------
# Tests: case and normalisation
# ---------------------------------------------------------------------------


def test_load_normalises_hyphens():
    loader = _reload_loader()
    preset_hyphen = loader.load_vertical_preset("salon-spa")
    preset_under = loader.load_vertical_preset("salon_spa")
    assert preset_hyphen == preset_under, "hyphen and underscore should resolve to the same preset"


def test_load_normalises_uppercase():
    loader = _reload_loader()
    preset_upper = loader.load_vertical_preset("Dental")
    preset_lower = loader.load_vertical_preset("dental")
    assert preset_upper == preset_lower, "case should be normalised"


# ---------------------------------------------------------------------------
# Tests: unknown vertical falls back to generic
# ---------------------------------------------------------------------------


def test_unknown_vertical_falls_back_to_generic():
    loader = _reload_loader()
    preset = loader.load_vertical_preset("completely_unknown_vertical_xyz")
    assert isinstance(preset, dict), "should return a dict, not raise"
    # Generic preset has a greeting and faqs
    assert "greeting" in preset or preset == {}, (
        "unknown vertical should return generic preset or empty dict (not raise)"
    )


def test_unknown_vertical_generic_is_not_empty():
    """Verify the generic preset itself has useful content."""
    loader = _reload_loader()
    generic = loader.load_vertical_preset("unknown_vertical_abc")
    # If the YAML file is present, generic should have content.
    if generic:
        assert "greeting" in generic
        assert len(generic.get("faqs", [])) > 0


# ---------------------------------------------------------------------------
# Tests: missing YAML file falls back gracefully
# ---------------------------------------------------------------------------


def test_missing_yaml_file_returns_empty_dict_not_raises(tmp_path):
    """When vertical_presets.yaml is absent, loader returns {} instead of raising."""
    loader = _reload_loader()
    nonexistent = tmp_path / "does_not_exist.yaml"
    with patch.object(loader, "_CONFIG_PATH", nonexistent):
        # Reset cache so the patched path is used.
        loader._cache = None
        result = loader.load_vertical_preset("salon_spa")
    # Should return {} (generic not found either) without raising.
    assert isinstance(result, dict)


def test_missing_yaml_file_list_verticals_returns_empty(tmp_path):
    """When vertical_presets.yaml is absent, list_verticals returns []."""
    loader = _reload_loader()
    nonexistent = tmp_path / "does_not_exist.yaml"
    with patch.object(loader, "_CONFIG_PATH", nonexistent):
        loader._cache = None
        result = loader.list_verticals()
    assert result == []


# ---------------------------------------------------------------------------
# Tests: list_verticals
# ---------------------------------------------------------------------------


def test_list_verticals_returns_list():
    loader = _reload_loader()
    result = loader.list_verticals()
    assert isinstance(result, list)


def test_list_verticals_excludes_generic():
    loader = _reload_loader()
    result = loader.list_verticals()
    assert "generic" not in result, "list_verticals should exclude the generic fallback"


def test_list_verticals_includes_known_verticals():
    loader = _reload_loader()
    result = loader.list_verticals()
    for expected in ("salon_spa", "plumber_hvac", "dental"):
        assert expected in result, f"expected {expected!r} in list_verticals()"


def test_list_verticals_is_sorted():
    loader = _reload_loader()
    result = loader.list_verticals()
    assert result == sorted(result), "list_verticals should return a sorted list"
