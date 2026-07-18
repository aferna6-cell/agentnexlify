"""Backward-compatibility shim. See backend/services/automation/ for the real code."""
from backend.models.database import get_service_supabase  # re-export for tests + back-compat
from backend.services.automation.templates import (
    _AFTERCARE_TEMPLATES, _REBOOK_INTERVALS, _REMINDER_EXTRAS, _ONBOARDING_STEPS,
)
from backend.services.automation.trigger import (
    BATCH_LIMIT, VALID_TRIGGER_EVENTS, trigger_sequence,
)
from backend.services.automation.orchestrator import (
    process_pending_steps, execute_step, _generate_ai_email, _advance_execution,
)
from backend.services.automation.scheduled_jobs import (
    _get_reminder_extras, auto_complete_past_appointments, check_no_response_leads,
    send_appointment_reminders,
    send_rebook_suggestions, send_aftercare_instructions, send_pending_review_requests,
    _send_review_followups, send_monthly_reports, send_portal_links, send_csat_surveys,
    check_new_reviews, send_onboarding_emails, send_invoice_payment_reminders,
    send_weekly_intelligence_briefs, send_weekly_digest, send_birthday_greetings,
    process_recurring_invoices, run_monthly_conversation_insights,
    run_churn_watch,
)
from backend.services.automation.rule_engine import (
    evaluate_trigger, _evaluate_conditions, _get_nested_field, _parse_utc_datetime,
    _scheduled_rule_already_fired, execute_automation_rule, _execute_action,
    _send_campaign_for_rule, check_lead_captured_triggers, check_tag_triggers,
    check_form_submission_triggers, check_appointment_triggers, schedule_automation_check,
)
