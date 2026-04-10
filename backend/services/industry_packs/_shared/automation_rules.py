"""Factory functions for reusable automation rule templates.

Rules map to the existing `automation_rules` table (see
`backend/services/automation_engine.py` for the executor). Each rule is a
declarative spec: on {trigger_event} [+ condition] do {action}.
"""

from backend.services.industry_packs.base import AutomationRuleTemplate


def make_reminder_on_booking_rule(
    *, key: str = "rule_reminder_on_booking", reminder_sequence_key: str = "appt_reminder",
) -> AutomationRuleTemplate:
    """When an appointment is booked → enroll in the reminder sequence."""
    return AutomationRuleTemplate(
        key=key,
        name="Start reminder sequence on booking",
        trigger_event="appointment_created",
        condition={},
        action={
            "type": "enroll_in_sequence",
            "sequence_key": reminder_sequence_key,
        },
        description="Automatically start the reminder sequence when an appointment is booked.",
    )


def make_post_appointment_review_trigger(
    *, key: str = "rule_post_appt_review", sequence_key: str = "post_appt_review",
) -> AutomationRuleTemplate:
    """When an appointment is marked completed → start CSAT/review sequence."""
    return AutomationRuleTemplate(
        key=key,
        name="Send CSAT after completed appointment",
        trigger_event="appointment_completed",
        condition={},
        action={
            "type": "enroll_in_sequence",
            "sequence_key": sequence_key,
        },
        description=(
            "After an appointment is marked completed, wait 2 hours and send a CSAT "
            "survey. The CSAT gate rules then branch on the rating."
        ),
    )


def make_csat_gate_rules(
    *,
    happy_key: str = "rule_csat_happy",
    unhappy_key: str = "rule_csat_unhappy",
    happy_threshold: int = 4,
) -> list[AutomationRuleTemplate]:
    """Pair of rules: happy → send GBP review link, unhappy → private flag."""
    return [
        AutomationRuleTemplate(
            key=happy_key,
            name="Send Google review link on high CSAT",
            trigger_event="csat_response",
            condition={"rating": {"gte": happy_threshold}},
            action={
                "type": "send_template",
                "channel": "sms_or_email",
                "template_key": "google_review_link",
            },
            description=(
                f"When a customer rates {happy_threshold}+ on CSAT, send them the Google "
                "review link. Happy customers are the only ones who see the public "
                "review funnel."
            ),
        ),
        AutomationRuleTemplate(
            key=unhappy_key,
            name="Flag unhappy CSAT for private follow-up",
            trigger_event="csat_response",
            condition={"rating": {"lt": happy_threshold}},
            action={
                "type": "create_action_item",
                "title": "Follow up with unhappy customer: {{name}}",
                "priority": "high",
                "suppress_review_link": True,
            },
            description=(
                "When a customer rates below threshold, create a private action item "
                "for staff to call them back — and suppress the Google review link so "
                "they don't post publicly while unhappy."
            ),
        ),
    ]


def make_dunning_trigger_rule(
    *,
    key: str = "rule_dunning_start",
    dunning_sequence_key: str = "dunning_ladder",
    days_overdue_trigger: int = 3,
) -> AutomationRuleTemplate:
    """When invoice goes N days overdue → enroll in dunning ladder."""
    return AutomationRuleTemplate(
        key=key,
        name="Start dunning ladder on overdue invoice",
        trigger_event="invoice_overdue",
        condition={"days_overdue": {"eq": days_overdue_trigger}},
        action={
            "type": "enroll_in_sequence",
            "sequence_key": dunning_sequence_key,
        },
        description=(
            f"When an invoice is {days_overdue_trigger} days overdue, enroll the lead "
            "in the polite→firm→final dunning ladder."
        ),
    )


def make_overdue_invoice_rule(
    *, key: str = "rule_invoice_final_escalate", final_days: int = 14,
) -> AutomationRuleTemplate:
    """When invoice hits N days overdue → create escalation action item."""
    return AutomationRuleTemplate(
        key=key,
        name="Escalate unpaid invoice at 14 days",
        trigger_event="invoice_overdue",
        condition={"days_overdue": {"gte": final_days}},
        action={
            "type": "create_action_item",
            "title": "Escalate unpaid invoice {{invoice_number}} for {{name}}",
            "priority": "high",
        },
        description=(
            f"When an invoice hits {final_days} days overdue, create a high-priority "
            "action item for staff to call or escalate."
        ),
    )


def make_reactivation_weekly_rule(
    *,
    key: str = "rule_reactivation_weekly",
    sequence_key: str = "reactivation",
    months_since_last_visit: int = 6,
) -> AutomationRuleTemplate:
    """Weekly cron → enroll lapsed clients in reactivation sequence."""
    return AutomationRuleTemplate(
        key=key,
        name=f"Weekly: enroll {months_since_last_visit}mo+ lapsed clients",
        trigger_event="weekly_cron",
        condition={
            "smart_list_key": "lapsed_clients",
            "not_enrolled_in": sequence_key,
        },
        action={
            "type": "enroll_in_sequence",
            "sequence_key": sequence_key,
        },
        description=(
            f"Every week, find clients whose last visit is {months_since_last_visit}+ "
            "months ago and aren't already in the reactivation sequence — enroll them."
        ),
    )
