"""Scheduling & Operations bucket (library §6).

* ``booking`` — appointment booking/reschedule/cancel/confirm messages. QA
  fixes: strip markdown from SMS, pick one confirmation frame (no
  "would that work?" + "consider this confirmed" contradiction), never
  fabricate scheduling state.
* ``appointment_reminder`` — day-before SMS reminders (one per appointment).
"""

from __future__ import annotations

from agent_os.base import BaseAgent
from agent_os.channels import CHANNEL_SOFT_MAX_CHARS
from agent_os.context import SharedContext
from agent_os.result import AgentResult, OwnerAsk
from agent_os.schema import (
    Bucket,
    Channel,
    Example,
    PermissionScope,
    Priority,
    SendCaps,
    Status,
    TriggerType,
)
from agent_os.trace import ReasoningTrace

from ._helpers import build_spec, field_input, sms_optout, topic_from


class BookingAgent(BaseAgent):
    spec = build_spec(
        agent_id="booking",
        display_name="Booking",
        bucket=Bucket.scheduling_ops,
        status=Status.existing,
        build_priority=Priority.P1,
        purpose=(
            "Drafts appointment booking, rescheduling, cancellation, and "
            "confirmation messages to a specific customer."
        ),
        routes_here_when=(
            "Owner asks to text or email a customer about an appointment slot",
            "Owner asks to confirm, reschedule, or cancel an appointment",
        ),
        channel=Channel.sms,
        secondary_channels=(Channel.email,),
        inputs=(
            field_input("customer_name", required=True, description="Customer's name."),
            field_input("subject", description="e.g. 'consultation'."),
            field_input("offered_slot", description="The slot being offered."),
            field_input("requested_day", description="Day the customer wanted."),
            field_input("service_type", description="Service, if relevant."),
            field_input("intent", description="offer | confirm | reschedule | cancel."),
            field_input("notes", description="Anything extra (verbatim only)."),
        ),
        permission_scope=PermissionScope(
            require_owner_approval=True,
            send_caps=SendCaps(per_day=30),
            notes="30 SMS/day default cap once auto-send ships (Phase 4).",
        ),
        title_format="SMS to {customer_name} — {day} {time} booking",
        body_format="Plain text, ≤280 chars, no markdown, opt-out where applicable.",
        reasoning_trace_steps=("Business profile", "Appointment state", "Drafted message"),
        routing_keywords=(
            "book",
            "booking",
            "appointment",
            "schedule",
            "reschedule",
            "cancel",
            "confirm",
            "slot",
            "text the customer",
            "set up a time",
        ),
        example_interactions=(
            Example(
                owner_ask=(
                    "Text Dana to confirm her consultation Thursday at 2pm."
                ),
                expected_route="booking",
                expected_output_excerpt="Thursday",
            ),
        ),
    )

    def build(
        self, ask: OwnerAsk, context: SharedContext, trace: ReasoningTrace
    ) -> AgentResult:
        profile = context.business_profile
        channel = self.channel_for(ask)

        customer_name = ask.param("customer_name") or topic_from(ask.text, default="there")
        subject = ask.param("subject") or "your appointment"
        slot = ask.param("offered_slot")
        intent = (ask.param("intent") or _infer_intent(ask.text)).lower()
        biz = profile.value("business_name") or "us"

        # Honest scheduling state: only describe slots we were actually told about.
        # Never fabricate "fully booked" — if we don't know, we don't say.
        existing = context.lead_for(customer_name)
        trace.record_load(
            "Appointment state",
            slot or existing,
            describe=lambda _: f"working from the slot the owner provided ({slot})"
            if slot
            else "matched an existing lead record",
            skip_if_empty=True,
        )

        # QA fix: pick ONE confirmation frame. If we're confirming, state it as
        # confirmed. If we're offering, ask once. Never both.
        if intent == "confirm" and slot:
            fallback = (
                f"Hi {customer_name}, confirming {subject} on {slot} with {biz}. "
                f"See you then! Reply here if anything changes."
            )
        elif intent == "cancel":
            fallback = (
                f"Hi {customer_name}, your {subject} with {biz} is cancelled. "
                f"Just reach out whenever you'd like to rebook."
            )
        elif intent == "reschedule" and slot:
            fallback = (
                f"Hi {customer_name}, we'd like to move {subject} to {slot}. "
                f"Does that work for you? Reply yes and I'll lock it in."
            )
        elif slot:
            fallback = (
                f"Hi {customer_name}, we can do {subject} on {slot}. Does that work "
                f"for you? Reply yes and I'll get you booked with {biz}."
            )
        else:
            # No slot given: don't invent availability. Ask for the customer's
            # preference instead of claiming a schedule we don't know.
            fallback = (
                f"Hi {customer_name}, happy to get {subject} on the calendar with "
                f"{biz}. What day and time work best for you?"
            )

        if channel == Channel.sms:
            fallback = f"{fallback} {sms_optout()}"
            cap = CHANNEL_SOFT_MAX_CHARS[Channel.sms]
            if len(fallback) > cap:
                fallback = fallback[: cap - 1].rstrip() + "…"

        system = (
            "You draft a booking message for a small business. Pick ONE frame: "
            "either confirm the appointment as set, or offer a slot and ask once "
            "— never both in the same message. Never invent availability the owner "
            "didn't state. SMS must be plain text, no markdown, under 280 chars. "
            "Use the real business name. Never use bracketed placeholders."
        )
        prompt = (
            f"Business: {profile.loaded_summary() or 'unknown'}\n"
            f"Customer: {customer_name}\nSubject: {subject}\n"
            f"Slot: {slot or '(none given — ask for preference)'}\n"
            f"Intent: {intent}\nChannel: {channel.value}\nDraft the message."
        )
        body, _ = self.draft(
            trace=trace, system=system, prompt=prompt, fallback=fallback,
            step_name="Drafted message",
        )

        when = slot or "open"
        title = f"{'SMS' if channel == Channel.sms else 'Email'} to {customer_name} — {when} booking"
        return AgentResult(
            agent_id=self.spec.agent_id,
            channel=channel,
            title=title,
            body=body,
            trace=trace,
            metadata={"intent": intent, "slot": slot},
        )


class AppointmentReminderAgent(BaseAgent):
    spec = build_spec(
        agent_id="appointment_reminder",
        display_name="Appointment Reminder",
        bucket=Bucket.scheduling_ops,
        status=Status.new,
        build_priority=Priority.P4,
        purpose="Drafts a short day-before SMS reminder for an upcoming appointment.",
        routes_here_when=(
            "Owner asks to send reminders for tomorrow's appointments",
        ),
        channel=Channel.sms,
        inputs=(
            field_input("customer_name", description="From appointment record."),
            field_input("service", description="The booked service."),
            field_input("when", description="Appointment time."),
        ),
        shared_context_reads=("business_profile", "appointments"),
        tool_dependencies=("google_calendar",),
        permission_scope=PermissionScope(
            require_owner_approval=True,
            recipient_filter="completed_service_only",
            send_caps=SendCaps(per_day=None),
            notes="1 reminder per appointment (hardcoded). Auto-send candidate post-Phase 4.",
        ),
        triggers_supported=(TriggerType.manual, TriggerType.scheduled),
        title_format="Reminder SMS — {customer_name}, {service}",
        body_format="One short plain-text SMS per appointment.",
        reasoning_trace_steps=("Business profile", "Tomorrow's appointments", "Drafted reminders"),
        routing_keywords=(
            "reminder",
            "remind",
            "tomorrow's appointments",
            "day before",
            "upcoming appointments",
        ),
        example_interactions=(
            Example(
                owner_ask="Send reminders for tomorrow's appointments.",
                expected_route="appointment_reminder",
                expected_output_excerpt="reminder",
            ),
        ),
    )

    def build(
        self, ask: OwnerAsk, context: SharedContext, trace: ReasoningTrace
    ) -> AgentResult:
        profile = context.business_profile
        channel = self.channel_for(ask)
        biz = profile.value("business_name") or "us"

        tomorrow = context.today.fromordinal(context.today.toordinal() + 1)
        appts = context.appointments_on(tomorrow)
        loaded = trace.record_load(
            "Tomorrow's appointments",
            appts,
            describe=lambda a: f"{len(a)} appointment(s) on {tomorrow.isoformat()}",
        )

        # Single-customer ask path (owner provided a name directly).
        named = ask.param("customer_name")
        if not loaded and not named:
            result = AgentResult(
                agent_id=self.spec.agent_id,
                channel=channel,
                title=f"Reminder SMS — none for {tomorrow.isoformat()}",
                body=(
                    f"No appointments on the calendar for {tomorrow.isoformat()}, "
                    f"so there's nothing to remind anyone about."
                ),
                trace=trace,
                metadata={"count": 0},
            )
            # Report-style honest no-op surfaced to owner; body is informational
            # (internal-style), so route it as a report-safe note via chat too.
            result.add_orchestrator_message(
                f"No appointments found for {tomorrow.isoformat()} — no reminders to send."
            )
            # Channel is sms but this is a status line, keep it plain text (it is).
            return result

        reminders: list[str] = []
        records = appts or []
        if named and not records:
            service = ask.param("service") or "your appointment"
            when = ask.param("when") or "tomorrow"
            reminders.append(
                f"Hi {named}, a quick reminder about {service} with {biz} {when}. "
                f"Reply here if you need to change anything. {sms_optout()}"
            )
        for appt in records:
            reminders.append(
                f"Hi {appt.customer_name}, reminder: {appt.service} with {biz} "
                f"tomorrow at {appt.when.strftime('%-I:%M %p')}. See you then! "
                f"{sms_optout()}"
            )

        fallback = "\n\n".join(reminders).strip()
        system = (
            "You draft short day-before appointment reminders for a small business. "
            "One SMS per appointment, plain text, under 280 chars each, warm and "
            "brief. Use the real business name. Never use bracketed placeholders."
        )
        prompt = (
            f"Business: {profile.loaded_summary() or 'unknown'}\n"
            f"Appointments: {len(records)}\nDraft one reminder each."
        )
        body, _ = self.draft(
            trace=trace, system=system, prompt=prompt, fallback=fallback,
            step_name="Drafted reminders",
        )

        count = len(records) if records else 1
        title = f"Reminder SMS — {count} appointment(s)"
        return AgentResult(
            agent_id=self.spec.agent_id,
            channel=channel,
            title=title,
            body=body,
            trace=trace,
            metadata={"count": count},
        )


def _infer_intent(text: str) -> str:
    low = text.lower()
    if "cancel" in low:
        return "cancel"
    if "reschedule" in low or "move" in low or "change" in low:
        return "reschedule"
    if "confirm" in low:
        return "confirm"
    return "offer"
