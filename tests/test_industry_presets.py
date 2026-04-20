"""Tests for industry-specific presets (pipeline stages, form presets)."""

import os
os.environ["TESTING"] = "1"

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestPipelinePresets:
    """Verify pipeline presets cover all major industries."""

    def test_all_preset_types_exist(self):
        from backend.routers.pipeline import _INDUSTRY_STAGES
        expected = {"realestate", "contractor", "dental", "legal", "restaurant", "salon", "fitness"}
        assert expected.issubset(set(_INDUSTRY_STAGES.keys()))

    def test_each_preset_has_won_and_lost(self):
        from backend.routers.pipeline import _INDUSTRY_STAGES
        for industry, stages in _INDUSTRY_STAGES.items():
            has_won = any(s.get("is_won") for s in stages)
            has_lost = any(s.get("is_lost") for s in stages)
            assert has_won, f"{industry} pipeline missing a 'won' stage"
            assert has_lost, f"{industry} pipeline missing a 'lost' stage"

    def test_stages_have_sequential_sort_order(self):
        from backend.routers.pipeline import _INDUSTRY_STAGES
        for industry, stages in _INDUSTRY_STAGES.items():
            orders = [s["sort_order"] for s in stages]
            assert orders == sorted(orders), f"{industry} stages not in order"

    def test_type_aliases_resolve(self):
        from backend.routers.pipeline import _INDUSTRY_STAGES, _TYPE_ALIASES
        for alias, target in _TYPE_ALIASES.items():
            assert target in _INDUSTRY_STAGES, f"Alias {alias}→{target} doesn't resolve"

    def test_default_stages_exist(self):
        from backend.routers.pipeline import DEFAULT_STAGES
        assert len(DEFAULT_STAGES) >= 4
        assert any(s.get("is_won") for s in DEFAULT_STAGES)

    def test_home_service_aliases_cover_hvac_and_related_trades(self):
        from backend.routers.pipeline import _TYPE_ALIASES
        expected_aliases = {
            "hvac": "contractor",
            "electrical": "contractor",
            "roofing": "contractor",
            "pest_control": "contractor",
            "painting": "contractor",
            "flooring": "contractor",
            "general_contractor": "contractor",
        }
        for alias, target in expected_aliases.items():
            assert _TYPE_ALIASES.get(alias) == target


class TestFormPresets:
    """Verify form presets for all industries."""

    def test_all_presets_exist(self):
        from backend.routers.forms import _FORM_PRESETS
        expected = {"dental_intake", "medical_intake", "contractor_estimate", "legal_intake", "fitness_waiver", "catering_inquiry"}
        assert expected.issubset(set(_FORM_PRESETS.keys()))

    def test_each_preset_has_required_keys(self):
        from backend.routers.forms import _FORM_PRESETS
        for key, preset in _FORM_PRESETS.items():
            assert "name" in preset, f"{key} missing name"
            assert "fields" in preset, f"{key} missing fields"
            assert "success_message" in preset, f"{key} missing success_message"

    def test_each_preset_has_consent_field(self):
        from backend.routers.forms import _FORM_PRESETS
        consent_types = {"dental_intake", "medical_intake", "legal_intake", "fitness_waiver"}
        for key in consent_types:
            preset = _FORM_PRESETS[key]
            consent_fields = [f for f in preset["fields"] if f.get("type") == "checkbox" and "consent" in f.get("id", "").lower() or "waiver" in f.get("id", "").lower()]
            assert consent_fields, f"{key} should have a consent/waiver checkbox"

    def test_field_counts(self):
        from backend.routers.forms import _FORM_PRESETS
        # Each preset should have at least 5 fields
        for key, preset in _FORM_PRESETS.items():
            assert len(preset["fields"]) >= 5, f"{key} has too few fields ({len(preset['fields'])})"


class TestReminderExtras:
    """Verify reminder extras cover key industries."""

    def test_reminder_extras_exist(self):
        from backend.services.automation_engine import _REMINDER_EXTRAS
        expected = {"dental", "medical", "salon", "auto_shop", "legal", "fitness"}
        assert expected.issubset(set(_REMINDER_EXTRAS.keys()))

    def test_each_has_at_least_2_items(self):
        from backend.services.automation_engine import _REMINDER_EXTRAS
        for industry, items in _REMINDER_EXTRAS.items():
            assert len(items) >= 2, f"{industry} needs at least 2 reminder items"


class TestAftercareTemplates:
    """Verify aftercare templates cover key industries."""

    def test_aftercare_templates_exist(self):
        from backend.services.automation_engine import _AFTERCARE_TEMPLATES
        expected = {"dental", "medical", "salon", "fitness", "auto_shop"}
        assert expected.issubset(set(_AFTERCARE_TEMPLATES.keys()))

    def test_each_has_default(self):
        from backend.services.automation_engine import _AFTERCARE_TEMPLATES
        for industry, templates in _AFTERCARE_TEMPLATES.items():
            assert "default" in templates, f"{industry} aftercare missing 'default' template"


class TestRebookIntervals:
    """Verify rebook intervals for applicable industries."""

    def test_rebook_intervals_exist(self):
        from backend.services.automation_engine import _REBOOK_INTERVALS
        expected = {"dental", "medical", "salon", "fitness"}
        assert expected.issubset(set(_REBOOK_INTERVALS.keys()))

    def test_intervals_are_positive(self):
        from backend.services.automation_engine import _REBOOK_INTERVALS
        for industry, (days, desc) in _REBOOK_INTERVALS.items():
            assert days > 0, f"{industry} has non-positive rebook interval"
            assert desc, f"{industry} has empty rebook description"


class TestBusinessProfiles:
    """Verify business-profile dashboard defaults for key verticals."""

    def test_hvac_widget_defaults_are_dispatch_focused(self):
        from backend.services.business_profiles import get_widget_defaults

        defaults = get_widget_defaults("hvac", "Polar Air")

        assert defaults["bot_name"] == "Polar Air Dispatch"
        assert defaults["primary_color"] == "#f97316"
        assert "AC repair" in defaults["greeting_message"]

    def test_real_estate_alias_resolves_cleanly(self):
        from backend.services.business_profiles import resolve_business_profile_key

        assert resolve_business_profile_key("real_estate") == "real_estate"
        assert resolve_business_profile_key("realestate") == "real_estate"

    def test_business_type_aliases_keep_general_until_specific_selection(self):
        from backend.services.business_profiles import resolve_business_profile_key

        assert resolve_business_profile_key("other") == "default"
        assert resolve_business_profile_key("") == "default"
        assert resolve_business_profile_key("beauty") == "salon"
        assert resolve_business_profile_key("automotive") == "auto_shop"
        assert resolve_business_profile_key("health_wellness") == "medical"
        assert resolve_business_profile_key("moving") == "home_services"

    def test_contractor_profile_exposes_proof_metric(self):
        from backend.services.business_profiles import get_dashboard_business_profile

        profile = get_dashboard_business_profile("plumbing", "Acme Plumbing")

        assert profile["key"] == "home_services"
        assert profile["proof_metric_label"] == "Quote-ready jobs captured"
        assert "estimate" in profile["proof_metric_empty_hint"].lower()

    def test_widget_prompt_personalizes_after_business_type_selection(self):
        from backend.routers.widget_helpers import _build_system_prompt

        general_prompt = _build_system_prompt(
            {"business_name": "Acme", "business_type": "other"},
            [],
        )
        contractor_prompt = _build_system_prompt(
            {"business_name": "Acme", "business_type": "plumbing"},
            [],
        )

        assert "INDUSTRY PERSONALIZATION" not in general_prompt
        assert "INDUSTRY PERSONALIZATION (Contractors / Home Services" in contractor_prompt
        assert "Quote" in contractor_prompt or "estimate" in contractor_prompt
