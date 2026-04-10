"""Shared template factories reused across industry packs.

Most sequences (appt reminder, dunning ladder, review request, reactivation)
have the same structure across verticals — only the copy changes. These
factories let each pack customize the wording without duplicating the
timing/trigger logic.
"""

from backend.services.industry_packs._shared.sequence_templates import (
    make_appointment_reminder_sequence,
    make_dunning_ladder_sequence,
    make_post_appointment_review_sequence,
    make_reactivation_sequence,
    make_welcome_sequence,
)
from backend.services.industry_packs._shared.automation_rules import (
    make_csat_gate_rules,
    make_dunning_trigger_rule,
    make_overdue_invoice_rule,
    make_post_appointment_review_trigger,
    make_reactivation_weekly_rule,
    make_reminder_on_booking_rule,
)
from backend.services.industry_packs._shared.smart_list_templates import (
    make_lapsed_clients_list,
    make_overdue_invoices_list,
    make_unresponded_leads_list,
)

__all__ = [
    "make_appointment_reminder_sequence",
    "make_dunning_ladder_sequence",
    "make_post_appointment_review_sequence",
    "make_reactivation_sequence",
    "make_welcome_sequence",
    "make_csat_gate_rules",
    "make_dunning_trigger_rule",
    "make_overdue_invoice_rule",
    "make_post_appointment_review_trigger",
    "make_reactivation_weekly_rule",
    "make_reminder_on_booking_rule",
    "make_lapsed_clients_list",
    "make_overdue_invoices_list",
    "make_unresponded_leads_list",
]
