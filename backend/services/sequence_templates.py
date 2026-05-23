"""Pre-built automation sequence templates.

Pulled out of `backend/routers/sequences.py` so the router stays focused
on auth + HTTP. Owns the canonical TEMPLATES catalog used by the
`create_from_template` endpoint.
"""

from typing import Any

TEMPLATES: dict[str, dict[str, Any]] = {
    "welcome": {
        "name": "Welcome Email Series",
        "trigger_event": "new_lead",
        "trigger_config": {},
        "steps": [
            {
                "step_order": 1,
                "delay_minutes": 0,
                "subject_template": "Welcome to {{business_name}}!",
                "body_template": (
                    "<h2>Hi {{name}},</h2>"
                    "<p>Thanks for reaching out to {{business_name}}! "
                    "We received your inquiry and wanted to personally welcome you.</p>"
                    "<p>One of our team members will be in touch shortly to help "
                    "with whatever you need.</p>"
                    "<p>In the meantime, feel free to reply to this email with any questions.</p>"
                    "<p>Best regards,<br>The {{business_name}} Team</p>"
                ),
            },
            {
                "step_order": 2,
                "delay_minutes": 1440,
                "subject_template": "Following up — {{business_name}}",
                "body_template": (
                    "<h2>Hi {{name}},</h2>"
                    "<p>Just wanted to follow up on your recent inquiry. "
                    "We'd love to learn more about what you're looking for.</p>"
                    "<p>Is there a good time for a quick chat? We're here to help!</p>"
                    "<p>Best,<br>The {{business_name}} Team</p>"
                ),
            },
        ],
    },
    "no_response": {
        "name": "No Response Follow-Up",
        "trigger_event": "no_response_24h",
        "trigger_config": {},
        "steps": [
            {
                "step_order": 1,
                "delay_minutes": 0,
                "subject_template": "We're still here to help — {{business_name}}",
                "body_template": (
                    "<h2>Hi {{name}},</h2>"
                    "<p>We noticed we haven't heard back from you. "
                    "No worries — we know life gets busy!</p>"
                    "<p>If you're still interested, we'd love to pick up "
                    "where we left off. Just reply to this email.</p>"
                    "<p>Best,<br>The {{business_name}} Team</p>"
                ),
            },
        ],
    },
    "appointment": {
        "name": "Appointment Booked Series",
        "trigger_event": "lead_stage_change",
        "trigger_config": {"target_stage": "appointment_booked"},
        "steps": [
            {
                "step_order": 1,
                "delay_minutes": 0,
                "subject_template": "Your appointment is confirmed — {{business_name}}",
                "body_template": (
                    "<h2>Hi {{name}},</h2>"
                    "<p>Great news! Your appointment with {{business_name}} has been confirmed.</p>"
                    "<p>We're looking forward to speaking with you. "
                    "If you need to reschedule, just reply to this email.</p>"
                    "<p>See you soon!<br>The {{business_name}} Team</p>"
                ),
            },
            {
                "step_order": 2,
                "delay_minutes": 1440,
                "subject_template": "Reminder: Your upcoming appointment",
                "body_template": (
                    "<h2>Hi {{name}},</h2>"
                    "<p>Just a friendly reminder about your appointment with {{business_name}}.</p>"
                    "<p>We can't wait to connect! If anything comes up, "
                    "don't hesitate to reach out.</p>"
                    "<p>Best,<br>The {{business_name}} Team</p>"
                ),
            },
        ],
    },
    "review_request": {
        "name": "Review Request",
        "trigger_event": "appointment_completed",
        "trigger_config": {},
        "steps": [
            {
                "step_order": 1,
                "delay_minutes": 60,
                "subject_template": "How was your visit, {{name}}?",
                "body_template": (
                    "<h2>Hi {{name}},</h2>"
                    "<p>Thank you for visiting {{business_name}}! "
                    "We'd love to hear about your experience.</p>"
                    "<p>If you have a moment, please leave us a quick review:</p>"
                    "<p><a href=\"{{review_link}}\">{{review_link}}</a></p>"
                    "<p>Your feedback helps us improve and helps others find us. Thank you!</p>"
                    "<p>&mdash; The {{business_name}} Team</p>"
                ),
            },
            {
                "step_order": 2,
                "delay_minutes": 4320,
                "subject_template": "Quick reminder, {{name}}",
                "body_template": (
                    "<h2>Hi {{name}},</h2>"
                    "<p>Just a friendly reminder &mdash; if you enjoyed your visit to "
                    "{{business_name}}, we'd really appreciate a quick review:</p>"
                    "<p><a href=\"{{review_link}}\">{{review_link}}</a></p>"
                    "<p>Thank you for your support!</p>"
                    "<p>&mdash; The {{business_name}} Team</p>"
                ),
            },
        ],
    },
}


def build_sequence_from_template(db: Any, tenant_id: str, template_id: str) -> dict[str, Any]:
    """Insert a sequence + its steps from the named template.

    Raises KeyError if `template_id` is unknown — caller maps to HTTP 400.
    Returns `{"sequence": ..., "steps_created": int}`.
    """
    if template_id not in TEMPLATES:
        raise KeyError(template_id)

    template = TEMPLATES[template_id]

    seq_result = db.table("automation_sequences").insert({
        "tenant_id": tenant_id,
        "name": template["name"],
        "trigger_event": template["trigger_event"],
        "trigger_config": template["trigger_config"],
    }).execute()
    seq = seq_result.data[0]

    steps_data = []
    for step in template["steps"]:
        steps_data.append({
            "sequence_id": seq["id"],
            **step,
            "action_type": "email",
        })

    if steps_data:
        db.table("automation_steps").insert(steps_data).execute()

    return {"sequence": seq, "steps_created": len(steps_data)}
