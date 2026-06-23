"""Tests for backend/services/internal_tenants.py.

Verifies:
  - Known internal account names are correctly identified
  - Real customer names are NOT identified as internal
  - Case-insensitive matching works
  - Extra whitespace is stripped before matching
  - Missing / null business_name is treated as NOT internal (conservative)
  - INTERNAL_TENANT_NAME_PATTERNS is a non-empty tuple

Run with:
    pytest backend/tests/test_internal_tenants.py --noconftest -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")


from backend.services.internal_tenants import (
    INTERNAL_TENANT_NAME_PATTERNS,
    is_internal_tenant,
)


class TestInternalTenantPatterns:
    """Validate the INTERNAL_TENANT_NAME_PATTERNS constant."""

    def test_patterns_is_a_tuple(self):
        assert isinstance(INTERNAL_TENANT_NAME_PATTERNS, tuple)

    def test_patterns_is_not_empty(self):
        assert len(INTERNAL_TENANT_NAME_PATTERNS) > 0

    def test_all_patterns_are_lowercase(self):
        """Patterns must be lowercase so case-insensitive matching works correctly."""
        for pattern in INTERNAL_TENANT_NAME_PATTERNS:
            assert pattern == pattern.lower(), (
                f"Pattern {pattern!r} is not lowercase — matching logic lowercases "
                "business_name but not the pattern, so mixed-case patterns would never match."
            )

    def test_agentnexlify_pattern_present(self):
        assert "agentnexlify" in INTERNAL_TENANT_NAME_PATTERNS


class TestIsInternalTenant:
    """Unit tests for is_internal_tenant()."""

    # --- Known internal accounts must be identified ---

    def test_agentnexlify_exact(self):
        assert is_internal_tenant({"business_name": "AgentNexLiFy"}) is True

    def test_agentnexlify_smoke_test(self):
        assert is_internal_tenant({"business_name": "AgentNexLiFy Smoke Test"}) is True

    def test_agent_nexlify_variant(self):
        """'Agent Nexlify' is a variant name used in older seeds."""
        assert is_internal_tenant({"business_name": "Agent Nexlify"}) is True

    def test_agentnexlify_lowercase(self):
        assert is_internal_tenant({"business_name": "agentnexlify"}) is True

    def test_agentnexlify_uppercase(self):
        assert is_internal_tenant({"business_name": "AGENTNEXLIFY"}) is True

    def test_agentnexlify_mixed_case(self):
        assert is_internal_tenant({"business_name": "AgEnTnExLiFy"}) is True

    def test_smoke_test_standalone(self):
        assert is_internal_tenant({"business_name": "Smoke Test Tenant"}) is True

    def test_test_account_standalone(self):
        assert is_internal_tenant({"business_name": "Test Account"}) is True

    def test_test_account_mixed_case(self):
        assert is_internal_tenant({"business_name": "My Test Account"}) is True

    # --- Leading/trailing whitespace is stripped before matching ---

    def test_leading_whitespace_stripped(self):
        assert is_internal_tenant({"business_name": "  AgentNexLiFy"}) is True

    def test_trailing_whitespace_stripped(self):
        assert is_internal_tenant({"business_name": "AgentNexLiFy  "}) is True

    def test_surrounding_whitespace_stripped(self):
        assert is_internal_tenant({"business_name": "  AgentNexLiFy Smoke Test  "}) is True

    # --- Real customer names must NOT be identified as internal ---

    def test_acme_corp_is_real(self):
        assert is_internal_tenant({"business_name": "Acme Corp"}) is False

    def test_acme_plumbing_is_real(self):
        assert is_internal_tenant({"business_name": "Acme Plumbing"}) is False

    def test_downtown_dental_is_real(self):
        assert is_internal_tenant({"business_name": "Downtown Dental"}) is False

    def test_sunrise_salon_is_real(self):
        assert is_internal_tenant({"business_name": "Sunrise Salon"}) is False

    def test_smith_hvac_is_real(self):
        assert is_internal_tenant({"business_name": "Smith HVAC"}) is False

    def test_generic_test_word_not_enough(self):
        """A business called 'The Testing Ground' should NOT be internal.

        The pattern 'test account' requires BOTH words together; a bare 'test'
        substring would be too aggressive.  Confirm the denylist doesn't
        false-positive on random 'test' occurrences.
        """
        # "test" alone is not in the pattern — only "test account" is.
        # "The Testing Ground" should pass through.
        assert is_internal_tenant({"business_name": "The Testing Ground"}) is False

    # --- Missing / null / empty name is conservatively treated as NOT internal ---

    def test_none_business_name_is_not_internal(self):
        assert is_internal_tenant({"business_name": None}) is False

    def test_missing_business_name_key_is_not_internal(self):
        assert is_internal_tenant({}) is False

    def test_empty_string_business_name_is_not_internal(self):
        assert is_internal_tenant({"business_name": ""}) is False

    def test_whitespace_only_business_name_is_not_internal(self):
        # Strips to empty string → treated as no name → not internal
        assert is_internal_tenant({"business_name": "   "}) is False

    # --- Extra fields in the dict don't break matching ---

    def test_extra_fields_ignored(self):
        tenant = {
            "id": "some-uuid",
            "business_name": "AgentNexLiFy Smoke Test",
            "plan": "agent_os",
            "plan_status": "active",
        }
        assert is_internal_tenant(tenant) is True

    def test_extra_fields_on_real_tenant(self):
        tenant = {
            "id": "customer-uuid",
            "business_name": "Sunrise Auto Shop",
            "plan": "chatbot",
            "plan_status": "active",
        }
        assert is_internal_tenant(tenant) is False
