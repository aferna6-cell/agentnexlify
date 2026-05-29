"""Customer Service bucket (library §3).

* ``customer_question`` — drafts answers to inbound customer questions. Fixes
  the high-severity bug where an empty KB produced a customer-facing draft that
  was actually an internal request to the owner.
* ``complaint_handler`` — empathetic complaint replies, flagged red, hardcoded
  to always require owner approval.
"""

from __future__ import annotations

from agent_os.base import BaseAgent
from agent_os.context import SharedContext
from agent_os.result import AgentResult, OwnerAsk
from agent_os.schema import (
    Bucket,
    Channel,
    Example,
    PermissionScope,
    Priority,
    Status,
)
from agent_os.trace import ReasoningTrace

from ._helpers import build_spec, field_input, topic_from


class CustomerQuestionAgent(BaseAgent):
    spec = build_spec(
        agent_id="customer_question",
        display_name="Customer Question",
        bucket=Bucket.customer_service,
        status=Status.existing,
        build_priority=Priority.P1,
        purpose=(
            "Drafts written answers to customer questions about hours, "
            "services, pricing, policies, or products."
        ),
        routes_here_when=(
            "Owner pastes a customer question and asks for a reply",
            "A widget conversation is classified as question intent (Phase 4)",
        ),
        channel=Channel.widget_reply,
        secondary_channels=(Channel.email, Channel.sms),
        inputs=(
            field_input(
                "customer_question",
                required=True,
                description="The customer's question, verbatim.",
            ),
            field_input("customer_name", description="Customer's name if known."),
            field_input("customer_context", description="Any extra context."),
        ),
        shared_context_reads=("business_profile", "widget_history", "kb"),
        title_format='Reply to {customer_name or "lead"} — {topic}',
        body_format="1–3 short paragraphs, channel-appropriate.",
        reasoning_trace_steps=(
            "Business profile",
            "Knowledge base",
            "Widget history",
            "Drafted reply",
        ),
        routing_keywords=(
            "question",
            "asked",
            "reply",
            "respond",
            "customer wants to know",
            "do you",
            "hours",
            "pricing",
        ),
        example_interactions=(
            Example(
                owner_ask=(
                    "A new lead asked through the widget: 'Do you guys handle "
                    "hybrids? I have a 2018 Prius and the battery feels weak.' "
                    "Draft a response."
                ),
                expected_route="customer_question",
                expected_output_excerpt="let me check and get back to you",
            ),
        ),
    )

    def build(
        self, ask: OwnerAsk, context: SharedContext, trace: ReasoningTrace
    ) -> AgentResult:
        profile = context.business_profile
        channel = self.channel_for(ask)
        messages: list[str] = []

        question = ask.param("customer_question", ask.text)
        customer_name = ask.param("customer_name")
        topic = topic_from(question)

        # Knowledge base: honest load. Search both curated KB and prior chats.
        kb_hits = [
            e
            for e in profile.knowledge_base
            if any(t in question.lower() for t in (e.question.lower(), *e.topics))
        ]
        trace.record_load(
            "Knowledge base",
            kb_hits,
            describe=lambda hits: f"{len(hits)} relevant FAQ entr(ies)",
            fallback_note="no matching KB entry — drafting a safe holding reply",
        )

        widget_hits = context.widget_search(topic) if topic else []
        trace.record_load(
            "Widget history",
            widget_hits,
            describe=lambda h: f"{len(h)} related prior conversation(s)",
            skip_if_empty=True,
        )

        biz = profile.value("business_name")
        greeting_name = customer_name or "there"
        hello = f"Hi {greeting_name}!" if customer_name else "Hi!"
        thanks = (
            f"Thanks for reaching out to {biz}." if biz else "Thanks for reaching out."
        )

        if kb_hits:
            # We have a real answer. Lead with it.
            answer = kb_hits[0].answer
            fallback = f"{hello} {thanks} {answer}".strip()
        else:
            # Safe holding reply: acknowledge, one clarifying question, promise
            # follow-up. Never invent facts, never expose internal status.
            fallback = (
                f"{hello} {thanks} That's a great question — I want to give you an "
                f"accurate answer, so let me confirm the details and get back to you "
                f"shortly. In the meantime, could you share a little more about what "
                f"you're looking for?"
            ).strip()
            # Surface the gap to the owner — never to the customer.
            gap_topic = topic if topic != "your question" else "this topic"
            messages.append(
                f"Heads up — I don't have anything on {gap_topic} in your knowledge "
                f"base, so this is a safe holding reply. Want to add it now so I can "
                f"sharpen future answers?"
            )

        signoff = profile.value("owner_name")
        if signoff:
            fallback = f"{fallback} — {signoff}"

        system = (
            "You draft a warm, accurate customer reply for a small business. "
            "Use only facts from the business profile and knowledge base provided. "
            "Never invent prices, policies, or capabilities. Never mention internal "
            "tooling or missing data to the customer. Plain, friendly, concise."
        )
        prompt = (
            f"Business: {profile.loaded_summary() or 'unknown'}\n"
            f"Known answer: {kb_hits[0].answer if kb_hits else '(none — write a holding reply)'}\n"
            f"Customer question: {question}\n"
            f"Customer name: {customer_name or '(unknown)'}\n"
            "Draft the reply."
        )
        body, _live = self.draft(
            trace=trace, system=system, prompt=prompt, fallback=fallback
        )

        title = f"Reply to {customer_name or 'lead'} — {topic}"
        result = AgentResult(
            agent_id=self.spec.agent_id,
            channel=channel,
            title=title,
            body=body,
            trace=trace,
            metadata={"topic": topic, "had_kb_answer": bool(kb_hits)},
        )
        for m in messages:
            result.add_orchestrator_message(m)
        return result


class ComplaintHandlerAgent(BaseAgent):
    spec = build_spec(
        agent_id="complaint_handler",
        display_name="Complaint Handler",
        bucket=Bucket.customer_service,
        status=Status.new,
        build_priority=Priority.P3,
        purpose=(
            "Drafts a sensitive, empathetic response to a customer complaint and "
            "flags it in the orchestrator chat so the owner sees it personally."
        ),
        routes_here_when=(
            "Owner asks for help responding to a complaint",
            "Lead Triage classifies a widget message as complaint intent (Phase 4)",
        ),
        channel=Channel.widget_reply,
        secondary_channels=(Channel.email,),
        inputs=(
            field_input("customer_name", description="Customer's name."),
            field_input(
                "complaint_text",
                required=True,
                description="The complaint, verbatim.",
            ),
            field_input("incident_date", "date", description="When it happened."),
            field_input("prior_history", description="Prior history if any."),
        ),
        shared_context_reads=("business_profile", "pipeline_state"),
        # Hardcoded approval: complaints can never auto-send, even in Phase 4.
        permission_scope=PermissionScope(
            hardcoded_approval=True,
            require_owner_approval=True,
            notes="Never auto-send — complaints are too high-stakes.",
        ),
        title_format="Complaint reply — {customer_name}, {topic}",
        body_format="Empathy, ownership, one concrete next step. Never minimises.",
        reasoning_trace_steps=(
            "Business profile",
            "Sensitivity check",
            "Drafted reply",
        ),
        routing_keywords=(
            "complaint",
            "unhappy",
            "angry",
            "upset",
            "terrible",
            "refund",
            "disappointed",
            "frustrated",
            "worst",
            "never again",
        ),
        example_interactions=(
            Example(
                owner_ask=(
                    "Customer left a message: 'I'm furious, your tech showed up "
                    "two hours late and scratched my bumper.' Help me respond."
                ),
                expected_route="complaint_handler",
                expected_output_excerpt="I'm sorry",
            ),
        ),
    )

    def build(
        self, ask: OwnerAsk, context: SharedContext, trace: ReasoningTrace
    ) -> AgentResult:
        profile = context.business_profile
        channel = self.channel_for(ask)

        complaint = ask.param("complaint_text", ask.text)
        customer_name = ask.param("customer_name")
        topic = topic_from(complaint, default="your experience")

        trace.note(
            "Sensitivity check",
            "complaint language detected — drafting with empathy, flagging for owner",
        )

        greeting = f"Hi {customer_name}," if customer_name else "Hello,"
        biz = profile.value("business_name")
        owner = profile.value("owner_name")
        phone = profile.value("phone")

        contact = ""
        if phone:
            contact = f" You can reach me directly at {phone}."
        ownership_biz = f" at {biz}" if biz else ""

        fallback = (
            f"{greeting} I'm really sorry about your experience{ownership_biz}. "
            f"This isn't the standard we hold ourselves to, and I take full "
            f"responsibility for making it right. Here's what I'll do next: I'll "
            f"look into exactly what happened and follow up with you personally to "
            f"resolve it.{contact} Thank you for telling me directly — it genuinely "
            f"helps us do better."
        )
        if owner:
            fallback = f"{fallback} — {owner}"

        system = (
            "You draft an empathetic reply to a customer complaint for a small "
            "business owner. Acknowledge the problem sincerely, take ownership, "
            "offer one concrete next step. Never minimise, never get defensive, "
            "never promise what the business can't deliver, never admit legal "
            "liability. Warm and human."
        )
        prompt = (
            f"Business: {profile.loaded_summary() or 'unknown'}\n"
            f"Customer: {customer_name or '(unknown)'}\n"
            f"Complaint: {complaint}\n"
            "Draft the reply."
        )
        body, _live = self.draft(
            trace=trace, system=system, prompt=prompt, fallback=fallback
        )

        title = f"Complaint reply — {customer_name or 'customer'}, {topic}"
        result = AgentResult(
            agent_id=self.spec.agent_id,
            channel=channel,
            title=title,
            body=body,
            trace=trace,
            flagged=True,  # surfaces red in the task list
            metadata={"topic": topic, "sensitive": True},
        )
        result.add_orchestrator_message(
            f"⚠ Flagged: this is a complaint from {customer_name or 'a customer'}. "
            f"I drafted an empathetic reply but it will always need your approval — "
            f"complaints never auto-send. Review it personally before it goes out."
        )
        return result
