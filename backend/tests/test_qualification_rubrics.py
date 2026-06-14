"""Tests for per-vertical lead-qualification rubrics (GH #216 / migration 147).

Pure functions over a static rubric table — no DB, no network. Validates that
every canonical vertical resolves to a non-empty, on-topic rubric and that
free-text / unknown business types fall back to the generic default.
"""

import pytest

from backend.services.qualification_rubrics import (
    _RUBRICS,
    get_qualification_rubric,
)


class TestRubricTable:
    def test_default_rubric_exists_and_nonempty(self):
        assert "default" in _RUBRICS
        assert len(_RUBRICS["default"]) > 0

    def test_all_rubrics_nonempty_strings(self):
        for key, text in _RUBRICS.items():
            assert isinstance(text, str)
            assert text.strip(), f"empty rubric for {key}"

    def test_covers_core_verticals(self):
        # The verticals the product actively sells to must each have a rubric.
        for key in ("hvac", "dental", "legal", "real_estate", "salon", "restaurant"):
            assert key in _RUBRICS


class TestGetQualificationRubric:
    def test_known_canonical_key(self):
        rubric = get_qualification_rubric("hvac")
        assert rubric == _RUBRICS["hvac"]
        # HVAC's strongest signal is the emergency no-heat/no-cool call.
        assert "no-heat" in rubric.lower() or "no heat" in rubric.lower()

    def test_free_text_resolves_to_canonical(self):
        # Free-text business_type values map through resolve_business_profile_key.
        assert get_qualification_rubric("plumbing")  # resolves to a real rubric
        assert get_qualification_rubric("Plumbing") == get_qualification_rubric("plumbing")

    def test_medical_rubric_has_diagnosis_guardrail(self):
        # Safety: the medical rubric must instruct the model not to infer diagnoses.
        rubric = get_qualification_rubric("medical").lower()
        assert "diagnos" in rubric

    def test_unknown_type_falls_back_to_default(self):
        assert get_qualification_rubric("zzz-not-a-real-type") == _RUBRICS["default"]

    def test_none_falls_back_to_default(self):
        assert get_qualification_rubric(None) == _RUBRICS["default"]

    def test_empty_string_falls_back_to_default(self):
        assert get_qualification_rubric("") == _RUBRICS["default"]

    @pytest.mark.parametrize("key", list(_RUBRICS.keys()))
    def test_every_table_key_returns_its_own_rubric(self, key):
        # Each canonical key in the table round-trips to its own rubric text.
        assert get_qualification_rubric(key) == _RUBRICS[key]
