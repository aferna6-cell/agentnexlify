"""Factory functions for reusable sequence templates across industry packs.

Each factory accepts vertical-specific copy (subject line, body copy,
entity noun like "appointment" vs "consult" vs "visit") and returns a
`SequenceTemplate`. The timing and trigger structure is fixed; only the
wording varies.

Timing constants (minutes):
    DAY = 1440
    HOUR = 60
"""

from backend.services.industry_packs.base import SequenceStep, SequenceTemplate

HOUR = 60
DAY = 1440


def make_appointment_reminder_sequence(
    *,
    key: str = "appt_reminder",
    entity_noun: str = "appointment",
    business_label: str = "{{business_name}}",
) -> SequenceTemplate:
    """-2 day reminder + morning-of reminder. Email + SMS."""
    return SequenceTemplate(
        key=key,
        name=f"{entity_noun.title()} Reminder (-2d / morning-of)",
        trigger_event="appointment_booked",
        trigger_config={},
        steps=[
            SequenceStep(
                step_order=1,
                delay_minutes=-2 * DAY,  # 2 days before
                action_type="email",
                subject_template=f"Reminder: Your {entity_noun} with {business_label} is in 2 days",
                body_template=(
                    f"<h2>Hi {{{{name}}}},</h2>"
                    f"<p>This is a friendly reminder that your {entity_noun} "
                    f"with {business_label} is coming up on {{{{appointment_date}}}} "
                    f"at {{{{appointment_time}}}}.</p>"
                    f"<p>If you need to reschedule, reply to this email or call us.</p>"
                    f"<p>See you soon!<br>{business_label}</p>"
                ),
            ),
            SequenceStep(
                step_order=2,
                delay_minutes=-2 * DAY,  # 2 days before
                action_type="sms",
                subject_template="",
                body_template=(
                    f"Reminder: Your {entity_noun} with {business_label} is in "
                    f"2 days on {{{{appointment_date}}}} at {{{{appointment_time}}}}. "
                    f"Reply STOP to opt out."
                ),
            ),
            SequenceStep(
                step_order=3,
                delay_minutes=-8 * HOUR,  # morning of (assumes PM appt)
                action_type="sms",
                subject_template="",
                body_template=(
                    f"See you today at {{{{appointment_time}}}} for your {entity_noun} "
                    f"with {business_label}. Reply R to reschedule."
                ),
            ),
        ],
    )


def make_dunning_ladder_sequence(
    *,
    key: str = "dunning_ladder",
    business_label: str = "{{business_name}}",
) -> SequenceTemplate:
    """Day 3 polite → Day 7 firmer → Day 14 final + escalate."""
    return SequenceTemplate(
        key=key,
        name="Overdue Invoice Ladder (3d / 7d / 14d)",
        trigger_event="invoice_overdue",
        trigger_config={"days_overdue_trigger": 3},
        steps=[
            SequenceStep(
                step_order=1,
                delay_minutes=0,
                action_type="email",
                subject_template=f"Friendly reminder: Invoice {{{{invoice_number}}}} from {business_label}",
                body_template=(
                    "<h2>Hi {{name}},</h2>"
                    f"<p>Just a friendly reminder that invoice "
                    "<strong>{{invoice_number}}</strong> for "
                    "<strong>${{total}}</strong> is now overdue.</p>"
                    "<p>You can pay online here: <a href=\"{{payment_link}}\">{{payment_link}}</a></p>"
                    "<p>If you've already paid, please disregard this email. "
                    "If you have any questions, just reply.</p>"
                    f"<p>Thanks,<br>{business_label}</p>"
                ),
            ),
            SequenceStep(
                step_order=2,
                delay_minutes=4 * DAY,  # day 7 total
                action_type="email",
                subject_template="Second notice: Invoice {{invoice_number}} past due",
                body_template=(
                    "<h2>Hi {{name}},</h2>"
                    "<p>We haven't received payment for invoice "
                    "<strong>{{invoice_number}}</strong> (${{total}}), which is now "
                    "7 days past due.</p>"
                    "<p>Please pay at your earliest convenience: "
                    "<a href=\"{{payment_link}}\">{{payment_link}}</a></p>"
                    "<p>If there's an issue with the invoice or you need to "
                    "discuss a payment plan, please reply and let us know.</p>"
                    f"<p>Thanks,<br>{business_label}</p>"
                ),
            ),
            SequenceStep(
                step_order=3,
                delay_minutes=7 * DAY,  # day 14 total
                action_type="email",
                subject_template="FINAL NOTICE: Invoice {{invoice_number}}",
                body_template=(
                    "<h2>Hi {{name}},</h2>"
                    "<p>This is a final notice that invoice "
                    "<strong>{{invoice_number}}</strong> for <strong>${{total}}</strong> "
                    "is now 14 days past due.</p>"
                    "<p>Please pay immediately to avoid further action: "
                    "<a href=\"{{payment_link}}\">{{payment_link}}</a></p>"
                    "<p>If there's something we should know, please reply today. "
                    "Otherwise we'll need to escalate this matter.</p>"
                    f"<p>{business_label}</p>"
                ),
            ),
        ],
    )


def make_post_appointment_review_sequence(
    *,
    key: str = "post_appt_review",
    entity_noun: str = "visit",
    business_label: str = "{{business_name}}",
) -> SequenceTemplate:
    """2h after appointment → CSAT survey. Happy path → Google review link.

    The CSAT gate logic (branch on rating) lives in an automation rule,
    not in the sequence itself. This sequence just sends the initial
    CSAT survey link.
    """
    return SequenceTemplate(
        key=key,
        name=f"Post-{entity_noun.title()} Review Collection",
        trigger_event="appointment_completed",
        trigger_config={},
        steps=[
            SequenceStep(
                step_order=1,
                delay_minutes=2 * HOUR,
                action_type="sms",
                subject_template="",
                body_template=(
                    f"Hi {{{{name}}}}, how was your {entity_noun} with "
                    f"{business_label} today? "
                    f"Tap to share: {{{{csat_link}}}}"
                ),
            ),
            SequenceStep(
                step_order=2,
                delay_minutes=2 * HOUR,
                action_type="email",
                subject_template=f"How was your {entity_noun} with {business_label}?",
                body_template=(
                    "<h2>Hi {{name}},</h2>"
                    f"<p>Thanks for choosing {business_label} today! "
                    f"We'd love to hear how your {entity_noun} went.</p>"
                    "<p><a href=\"{{csat_link}}\" style=\"background:#0ea5e9;color:#fff;"
                    "padding:12px 24px;border-radius:6px;text-decoration:none;\">"
                    "Rate Your Experience</a></p>"
                    "<p>Takes 10 seconds. Helps us a lot.</p>"
                    f"<p>— {business_label}</p>"
                ),
            ),
        ],
    )


def make_reactivation_sequence(
    *,
    key: str = "reactivation",
    entity_noun: str = "visit",
    business_label: str = "{{business_name}}",
    months_since_last_visit: int = 6,
) -> SequenceTemplate:
    """Day 0 email → Day 3 SMS → Day 10 email w/ discount offer."""
    return SequenceTemplate(
        key=key,
        name=f"Reactivation — {months_since_last_visit}mo+ lapsed",
        trigger_event="lapsed_client_weekly_cron",
        trigger_config={"months_since_last_visit": months_since_last_visit},
        steps=[
            SequenceStep(
                step_order=1,
                delay_minutes=0,
                action_type="email",
                subject_template=f"It's been a while, {{{{name}}}} — {business_label}",
                body_template=(
                    "<h2>Hi {{name}},</h2>"
                    f"<p>We noticed it's been about {months_since_last_visit} months "
                    f"since your last {entity_noun} at {business_label}.</p>"
                    f"<p>Ready to come back in? We'd love to see you again. "
                    "Tap below to book:</p>"
                    "<p><a href=\"{{booking_link}}\">Book Now</a></p>"
                    f"<p>— {business_label}</p>"
                ),
            ),
            SequenceStep(
                step_order=2,
                delay_minutes=3 * DAY,
                action_type="sms",
                subject_template="",
                body_template=(
                    f"Hi {{{{name}}}}, it's {business_label}. "
                    f"Been a while — ready to book your next {entity_noun}? "
                    f"{{{{booking_link}}}} Reply STOP to opt out."
                ),
            ),
            SequenceStep(
                step_order=3,
                delay_minutes=10 * DAY,
                action_type="email",
                subject_template=f"Here's 10% off your next {entity_noun} — {business_label}",
                body_template=(
                    "<h2>Hi {{name}},</h2>"
                    f"<p>We'd really love to see you back at {business_label}. "
                    f"Here's <strong>10% off</strong> your next {entity_noun} as a thank-you "
                    "for being a customer.</p>"
                    "<p>Use code <strong>WELCOMEBACK</strong> when you book: "
                    "<a href=\"{{booking_link}}\">{{booking_link}}</a></p>"
                    "<p>Offer expires in 14 days. Hope to see you soon!</p>"
                    f"<p>— {business_label}</p>"
                ),
            ),
        ],
    )


def make_welcome_sequence(
    *,
    key: str = "welcome",
    business_label: str = "{{business_name}}",
) -> SequenceTemplate:
    """Generic welcome series for new leads. One email immediate, one at +24h."""
    return SequenceTemplate(
        key=key,
        name="Welcome Series",
        trigger_event="new_lead",
        trigger_config={},
        steps=[
            SequenceStep(
                step_order=1,
                delay_minutes=0,
                action_type="email",
                subject_template=f"Welcome to {business_label}, {{{{name}}}}!",
                body_template=(
                    "<h2>Hi {{name}},</h2>"
                    f"<p>Thanks for reaching out to {business_label}! "
                    "We received your inquiry and one of our team will be "
                    "in touch shortly.</p>"
                    "<p>In the meantime, feel free to reply with any questions.</p>"
                    f"<p>— {business_label}</p>"
                ),
            ),
            SequenceStep(
                step_order=2,
                delay_minutes=DAY,
                action_type="email",
                subject_template=f"Following up — {business_label}",
                body_template=(
                    "<h2>Hi {{name}},</h2>"
                    "<p>Just wanted to follow up on your inquiry. "
                    "Is there a good time for a quick chat?</p>"
                    f"<p>— {business_label}</p>"
                ),
            ),
        ],
    )
