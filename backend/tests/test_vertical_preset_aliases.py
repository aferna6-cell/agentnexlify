"""Vertical preset alias resolution.

Onboarding sends business_type values like "salon", "hvac", "dentist" — not the
canonical preset keys ("salon_spa", "plumber_hvac", "dental"). Without alias
resolution these silently fall back to the generic preset, so the vertical
auto-apply (lane 4) never delivers vertical-specific defaults.
"""

from backend.services.vertical_preset_loader import load_vertical_preset


def _greeting(vertical: str) -> str:
    return (load_vertical_preset(vertical).get("greeting") or "").strip()


def test_direct_key_still_resolves():
    assert _greeting("salon_spa")


def test_salon_alias_maps_to_salon_spa():
    assert _greeting("salon") == _greeting("salon_spa")


def test_spa_and_barber_alias_to_salon_spa():
    assert _greeting("spa") == _greeting("salon_spa")
    assert _greeting("barber") == _greeting("salon_spa")


def test_hvac_and_plumber_alias_to_plumber_hvac():
    assert _greeting("hvac") == _greeting("plumber_hvac")
    assert _greeting("plumbing") == _greeting("plumber_hvac")


def test_dentist_alias_maps_to_dental():
    assert _greeting("dentist") == _greeting("dental")


def test_unknown_vertical_falls_back_to_generic():
    assert _greeting("spaceship_repair") == _greeting("generic")


def test_case_and_spacing_insensitive():
    assert _greeting("Hair Salon") == _greeting("salon_spa")
