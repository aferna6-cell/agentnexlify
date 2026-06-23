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


# ---------------------------------------------------------------------------
# New alias tests: law_firm
# ---------------------------------------------------------------------------


def test_law_alias_maps_to_law_firm():
    assert _greeting("law") == _greeting("law_firm")


def test_lawyer_alias_maps_to_law_firm():
    assert _greeting("lawyer") == _greeting("law_firm")


def test_attorney_alias_maps_to_law_firm():
    assert _greeting("attorney") == _greeting("law_firm")


def test_legal_alias_maps_to_law_firm():
    assert _greeting("legal") == _greeting("law_firm")


def test_law_firm_direct_key_resolves():
    assert _greeting("law_firm")


# ---------------------------------------------------------------------------
# New alias tests: restaurant
# ---------------------------------------------------------------------------


def test_restaurant_direct_key_resolves():
    assert _greeting("restaurant")


def test_cafe_alias_maps_to_restaurant():
    assert _greeting("cafe") == _greeting("restaurant")


def test_food_alias_maps_to_restaurant():
    assert _greeting("food") == _greeting("restaurant")


def test_dining_alias_maps_to_restaurant():
    assert _greeting("dining") == _greeting("restaurant")


# ---------------------------------------------------------------------------
# New alias tests: fitness_studio
# ---------------------------------------------------------------------------


def test_fitness_studio_direct_key_resolves():
    assert _greeting("fitness_studio")


def test_gym_alias_maps_to_fitness_studio():
    assert _greeting("gym") == _greeting("fitness_studio")


def test_fitness_alias_maps_to_fitness_studio():
    assert _greeting("fitness") == _greeting("fitness_studio")


def test_studio_alias_maps_to_fitness_studio():
    assert _greeting("studio") == _greeting("fitness_studio")


def test_yoga_alias_maps_to_fitness_studio():
    assert _greeting("yoga") == _greeting("fitness_studio")


def test_pilates_alias_maps_to_fitness_studio():
    assert _greeting("pilates") == _greeting("fitness_studio")
