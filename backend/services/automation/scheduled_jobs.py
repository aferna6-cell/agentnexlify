"""Automation scheduled jobs — thin re-export shim.

All implementations have been moved to backend/services/automation/scheduled/:
  lead_checks.py      — check_no_response_leads
  appointment_jobs.py — send_appointment_reminders, send_rebook_suggestions,
                        send_aftercare_instructions, _get_reminder_extras
  review_jobs.py      — send_pending_review_requests, _send_review_followups,
                        check_new_reviews
  email_jobs.py       — send_monthly_reports, send_portal_links,
                        send_csat_surveys, send_onboarding_emails
  billing_jobs.py     — send_invoice_payment_reminders

Move map (2026-04-17):
  check_no_response_leads        -> scheduled/lead_checks.py
  send_appointment_reminders     -> scheduled/appointment_jobs.py
  send_rebook_suggestions        -> scheduled/appointment_jobs.py
  send_aftercare_instructions    -> scheduled/appointment_jobs.py
  _get_reminder_extras           -> scheduled/appointment_jobs.py
  send_pending_review_requests   -> scheduled/review_jobs.py
  _send_review_followups         -> scheduled/review_jobs.py
  check_new_reviews              -> scheduled/review_jobs.py
  send_monthly_reports           -> scheduled/email_jobs.py
  send_portal_links              -> scheduled/email_jobs.py
  send_csat_surveys              -> scheduled/email_jobs.py
  send_onboarding_emails         -> scheduled/email_jobs.py
  send_invoice_payment_reminders -> scheduled/billing_jobs.py

This shim preserves the public import path so all existing callers continue
to work without modification.
"""

from backend.services.automation.scheduled import (
    _get_reminder_extras,
    check_no_response_leads,
    send_appointment_reminders,
    send_rebook_suggestions,
    send_aftercare_instructions,
    send_pending_review_requests,
    _send_review_followups,
    send_monthly_reports,
    send_portal_links,
    send_csat_surveys,
    check_new_reviews,
    send_onboarding_emails,
    send_invoice_payment_reminders,
    run_monthly_conversation_insights,
)

# Re-export from scheduled_jobs_ext to keep the public API of this module intact
from backend.services.automation.scheduled_jobs_ext import (
    send_weekly_intelligence_briefs,
    send_weekly_digest,
    send_birthday_greetings,
    process_recurring_invoices,
    run_churn_watch,
)

__all__ = [
    "_get_reminder_extras",
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
    "run_monthly_conversation_insights",
    "send_weekly_intelligence_briefs",
    "send_weekly_digest",
    "send_birthday_greetings",
    "process_recurring_invoices",
    "run_churn_watch",
]
