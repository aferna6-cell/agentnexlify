"""Smoke tests for backend/models/onboarding_v2.py.

Verifies all Pydantic models instantiate correctly with valid data and that
enum values match the spec. No external dependencies needed.
"""

import pytest
from pydantic import ValidationError

from backend.models.onboarding_v2 import (
    IntegrationKeyProvider,
    IntegrationKeyStatus,
    IntegrationKeysResponse,
    ReadinessCriteria,
    ReadinessResponse,
    SaveIntegrationKeyRequest,
    VerticalPreset,
    WidgetHealthResponse,
    WizardCompleteResponse,
    WizardStartRequest,
    WizardStepRequest,
)


class TestVerticalPreset:
    def test_all_six_verticals_exist(self):
        expected = {
            "plumbing",
            "hvac",
            "cleaning",
            "power_washing",
            "landscaping",
            "electrical",
        }
        actual = {v.value for v in VerticalPreset}
        assert actual == expected

    def test_string_coercion(self):
        assert VerticalPreset("plumbing") == VerticalPreset.plumbing


class TestWizardStartRequest:
    def test_no_vertical(self):
        req = WizardStartRequest()
        assert req.vertical is None

    def test_with_valid_vertical(self):
        req = WizardStartRequest(vertical="plumbing")
        assert req.vertical == VerticalPreset.plumbing

    def test_invalid_vertical_raises(self):
        with pytest.raises(ValidationError):
            WizardStartRequest(vertical="nonexistent")


class TestWizardStepRequest:
    def test_instantiation(self):
        req = WizardStepRequest(field_updates={"business_name": "Acme Plumbing"})
        assert req.field_updates == {"business_name": "Acme Plumbing"}

    def test_empty_dict_allowed(self):
        req = WizardStepRequest(field_updates={})
        assert req.field_updates == {}


class TestWizardCompleteResponse:
    def test_instantiation(self):
        resp = WizardCompleteResponse(ready_to_launch=True, widget_api_key="key_abc123")
        assert resp.ready_to_launch is True
        assert resp.widget_api_key == "key_abc123"


class TestReadinessCriteria:
    def test_defaults(self):
        rc = ReadinessCriteria()
        assert rc.services_count == 0
        assert rc.hours_filled is False
        assert rc.faqs_count == 0
        assert rc.logo_uploaded is False

    def test_set_values(self):
        rc = ReadinessCriteria(
            services_count=5, hours_filled=True, faqs_count=10, logo_uploaded=True
        )
        assert rc.services_count == 5
        assert rc.hours_filled is True


class TestReadinessResponse:
    def test_not_ready(self):
        criteria = ReadinessCriteria()
        resp = ReadinessResponse(criteria=criteria, ready_to_launch=False)
        assert resp.ready_to_launch is False
        assert resp.criteria.services_count == 0

    def test_ready(self):
        criteria = ReadinessCriteria(
            services_count=5, hours_filled=True, faqs_count=6, logo_uploaded=True
        )
        resp = ReadinessResponse(criteria=criteria, ready_to_launch=True)
        assert resp.ready_to_launch is True


class TestIntegrationKeyProvider:
    def test_all_providers_exist(self):
        expected = {"stripe", "twilio", "resend"}
        actual = {p.value for p in IntegrationKeyProvider}
        assert actual == expected


class TestSaveIntegrationKeyRequest:
    def test_valid_stripe_key(self):
        req = SaveIntegrationKeyRequest(provider="stripe", api_key="live_key_abcdef12")
        assert req.provider == IntegrationKeyProvider.stripe
        assert req.api_key == "live_key_abcdef12"

    def test_optional_metadata(self):
        req = SaveIntegrationKeyRequest(
            provider="twilio",
            api_key="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            metadata={"account_sid": "AC123"},
        )
        assert req.metadata == {"account_sid": "AC123"}

    def test_key_too_short_raises(self):
        with pytest.raises(ValidationError):
            SaveIntegrationKeyRequest(provider="stripe", api_key="short")

    def test_invalid_provider_raises(self):
        with pytest.raises(ValidationError):
            SaveIntegrationKeyRequest(provider="paypal", api_key="validlongkey")


class TestIntegrationKeyStatus:
    def test_instantiation(self):
        status = IntegrationKeyStatus(
            provider="stripe",
            masked_key="sk_live_••••••••1234",
            health="green",
        )
        assert status.health == "green"
        assert status.last_verified_at is None

    def test_with_last_verified(self):
        status = IntegrationKeyStatus(
            provider="twilio",
            masked_key="AC••••••••5678",
            health="yellow",
            last_verified_at="2026-04-23T10:00:00Z",
        )
        assert status.last_verified_at == "2026-04-23T10:00:00Z"


class TestIntegrationKeysResponse:
    def test_empty_providers(self):
        resp = IntegrationKeysResponse(providers=[])
        assert resp.providers == []

    def test_multiple_providers(self):
        providers = [
            IntegrationKeyStatus(
                provider="stripe", masked_key="sk••••1234", health="green"
            ),
            IntegrationKeyStatus(
                provider="twilio", masked_key="AC••••5678", health="red"
            ),
        ]
        resp = IntegrationKeysResponse(providers=providers)
        assert len(resp.providers) == 2


class TestWidgetHealthResponse:
    def test_healthy(self):
        resp = WidgetHealthResponse(
            loaded=True, reachable=True, origin_allowed=True, domain="acme.com"
        )
        assert resp.loaded is True
        assert resp.last_ping_at is None

    def test_unhealthy(self):
        resp = WidgetHealthResponse(
            loaded=False, reachable=False, origin_allowed=False, domain="acme.com"
        )
        assert resp.loaded is False
