"""Tests for #82 — scheduled_jobs dead code / import chain integrity.

Issue #82 flagged backend/services/automation/scheduled/ subpackage as
potentially dead code shadowed by backend/services/automation/scheduled_jobs.py.

Investigation shows the code is correctly structured:
  - scheduled_jobs.py is a thin RE-EXPORT SHIM (not an implementation)
  - scheduled/__init__.py is the real aggregator of implementations
  - scheduled/{lead_checks,appointment_jobs,...}.py are the real implementations
  - scheduled_jobs_ext.py provides additional functions re-exported by the shim

The shim exists to preserve the public import path
`backend.services.automation.scheduled_jobs` without modification.

These tests prove the chain works end-to-end.
"""

import importlib
import types

import pytest


class TestScheduledJobsImportChain:
    """Verify that all public names survive the full import chain."""

    EXPECTED_NAMES = [
        "check_no_response_leads",
        "send_appointment_reminders",
        "send_rebook_suggestions",
        "send_aftercare_instructions",
        "send_pending_review_requests",
        "_send_review_followups",
        "send_monthly_reports",
        "send_portal_links",
        "send_csat_surveys",
        "check_new_reviews",
        "send_onboarding_emails",
        "send_invoice_payment_reminders",
        # ext module names
        "send_weekly_intelligence_briefs",
        "send_weekly_digest",
        "send_birthday_greetings",
        "process_recurring_invoices",
    ]

    def test_shim_module_importable(self):
        """scheduled_jobs.py shim must be importable without errors."""
        mod = importlib.import_module("backend.services.automation.scheduled_jobs")
        assert isinstance(mod, types.ModuleType)

    def test_subpackage_importable(self):
        """scheduled/__init__.py subpackage must be importable without errors."""
        mod = importlib.import_module("backend.services.automation.scheduled")
        assert isinstance(mod, types.ModuleType)

    def test_shim_exports_all_expected_names(self):
        """Every name in __all__ must exist as an attribute on the shim module."""
        mod = importlib.import_module("backend.services.automation.scheduled_jobs")
        for name in self.EXPECTED_NAMES:
            assert hasattr(mod, name), f"shim missing: {name}"

    def test_subpackage_exports_core_names(self):
        """The scheduled/ subpackage __init__ must export the core job functions."""
        core_names = [
            "check_no_response_leads",
            "send_appointment_reminders",
            "send_invoice_payment_reminders",
            "send_monthly_reports",
        ]
        mod = importlib.import_module("backend.services.automation.scheduled")
        for name in core_names:
            assert hasattr(mod, name), f"subpackage missing: {name}"

    def test_shim_and_subpackage_share_same_callable(self):
        """Functions from the shim must be identical objects to subpackage functions.

        This proves the shim is a pure re-export and not a shadowing duplicate.
        """
        shim = importlib.import_module("backend.services.automation.scheduled_jobs")
        sub = importlib.import_module("backend.services.automation.scheduled")

        shared = [
            "check_no_response_leads",
            "send_appointment_reminders",
            "send_rebook_suggestions",
            "send_aftercare_instructions",
            "send_pending_review_requests",
            "send_monthly_reports",
            "send_portal_links",
            "send_csat_surveys",
            "send_onboarding_emails",
            "send_invoice_payment_reminders",
        ]
        for name in shared:
            shim_obj = getattr(shim, name)
            sub_obj = getattr(sub, name)
            assert shim_obj is sub_obj, (
                f"shim.{name} is not the same object as subpackage.{name} — "
                "the shim must re-export, not shadow"
            )

    def test_automation_engine_can_import_scheduled_jobs(self):
        """automation_engine.py imports from scheduled_jobs; it must succeed."""
        mod = importlib.import_module("backend.services.automation_engine")
        assert isinstance(mod, types.ModuleType)

    def test_automation_package_init_re_exports_scheduled_jobs(self):
        """backend.services.automation __init__ must expose all scheduled functions."""
        mod = importlib.import_module("backend.services.automation")
        for name in self.EXPECTED_NAMES:
            assert hasattr(mod, name), f"automation package __init__ missing: {name}"

    def test_individual_submodules_importable(self):
        """Each scheduled sub-module must be directly importable."""
        submodules = [
            "backend.services.automation.scheduled.lead_checks",
            "backend.services.automation.scheduled.appointment_jobs",
            "backend.services.automation.scheduled.review_jobs",
            "backend.services.automation.scheduled.email_jobs",
            "backend.services.automation.scheduled.billing_jobs",
        ]
        for modname in submodules:
            mod = importlib.import_module(modname)
            assert isinstance(mod, types.ModuleType), f"Failed to import {modname}"
