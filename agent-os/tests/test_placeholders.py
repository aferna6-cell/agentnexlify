"""Bracketed-placeholder detection (rule 2)."""

from __future__ import annotations

from agent_os.placeholders import (
    PLACEHOLDER_TO_FIELD,
    find_placeholders,
    placeholders_for_present_fields,
)
from agent_os.profile import BusinessProfile


def test_finds_known_placeholders():
    found = find_placeholders("Hi from [Shop Name], call [Phone].")
    tokens = {f.token for f in found}
    assert "[Shop Name]" in tokens
    assert "[Phone]" in tokens


def test_maps_placeholder_to_profile_field():
    found = find_placeholders("[Your Name]")
    assert found[0].maps_to_field == "owner_name"


def test_footnote_markers_not_flagged():
    # "[1]" is a footnote, not a placeholder — must not match.
    assert find_placeholders("See reference [1] and [2].") == []


def test_clean_text_has_no_placeholders():
    assert find_placeholders("Hi Mike, this is Sam at Bright Auto.") == []


def test_present_field_placeholder_is_violation():
    profile = BusinessProfile(business_name="Bright Auto")
    offenders = placeholders_for_present_fields("We are [Business Name].", profile)
    assert offenders
    assert offenders[0].maps_to_field == "business_name"


def test_absent_field_placeholder_is_tolerated_for_reports():
    profile = BusinessProfile()  # no business_name
    offenders = placeholders_for_present_fields("We are [Business Name].", profile)
    assert offenders == []


def test_placeholder_field_map_targets_real_profile_attributes():
    profile = BusinessProfile()
    for field_name in set(PLACEHOLDER_TO_FIELD.values()):
        # value() must accept every mapped field without error.
        assert profile.value(field_name) is None
