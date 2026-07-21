"""The automation loop's lazy import block must always resolve.

Incident 2026-07-21 (second finding): the photo-quote merge wired
``purge_photo_quote_images_30d`` into main._automation_loop's import block,
but ``automation_engine`` never re-exported it. The app booted fine (the
imports are lazy, inside the coroutine), every route worked, and the loop
died on ImportError at startup - killing ALL scheduled automations in prod
with no failing test. This test executes the same imports eagerly so a
missing name fails CI instead of prod.
"""

import os

os.environ.setdefault("TESTING", "1")


def test_loop_import_block_resolves():
    # Mirrors backend/main.py::_automation_loop's import block. When adding
    # an import to the loop, add it here too.
    from backend.services.daily_briefing import send_daily_briefings  # noqa: F401
    from backend.services.noshow_recovery import process_noshow_recovery  # noqa: F401
    from backend.services.automation_engine import (  # noqa: F401
        auto_complete_past_appointments,
        check_new_reviews,
        check_no_response_leads,
        process_pending_steps,
        send_appointment_reminders,
        send_csat_surveys,
        send_invoice_payment_reminders,
        send_monthly_reports,
        process_recurring_invoices,
        send_pending_review_requests,
        send_rebook_suggestions,
        send_onboarding_emails,
        send_portal_links,
        send_weekly_intelligence_briefs,
        send_weekly_digest,
        send_birthday_greetings,
        send_aftercare_instructions,
        schedule_automation_check,
        run_monthly_conversation_insights,
        run_churn_watch,
        purge_photo_quote_images_30d,
    )
    from backend.services.weekly_funnel_report import send_weekly_funnel_report  # noqa: F401
    from backend.services.os_sync import run_due_syncs  # noqa: F401
    from backend.services.os_opportunities import run_opportunity_scan  # noqa: F401
    from backend.services.os_draft_expiry import run_draft_expiry_sweep  # noqa: F401
    from backend.services.drive_kb_sync import run_drive_kb_sync_due  # noqa: F401
    from backend.services.twilio_webhook_sync import sync_twilio_number_webhooks  # noqa: F401
    from backend.services.demo_reset_job import reset_demo_tenants  # noqa: F401
    from backend.services.activation_nudges import send_activation_nudges  # noqa: F401
    from backend.services.conversation_enrichment_job import (  # noqa: F401
        run_pending_enrichment,
    )
    from backend.services.os_scheduled_tasks import run_due_tasks  # noqa: F401
    from backend.services.os_projects import run_project_ticks  # noqa: F401
    from backend.services.platform_flags import flag_enabled  # noqa: F401
    from backend.services.os_approval_rollup import send_approval_rollups  # noqa: F401
    # Lazily imported inside process_user_turn (chat BI fast path)
    from backend.services.os_data_answers import try_data_answer  # noqa: F401
