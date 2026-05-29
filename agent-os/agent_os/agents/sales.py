"""Sales bucket (library §4).

* ``lead_nurture`` — warm multi-touch follow-up sequences for stale leads.
* ``quote_follow_up`` — quote-specific nurture variant (known $ amount + scope).
"""

from __future__ import annotations

from agent_os.base import BaseAgent
from agent_os.context import SharedContext
from agent_os.result import AgentResult, OwnerAsk
from agent_os.schema import Bucket, Channel, Example, Priority, Status
from agent_os.trace import ReasoningTrace

from ._helpers import build_spec, field_input, money, sms_optout, topic_from, touch_label


class LeadNurtureAgent(BaseAgent):
    spec = build_spec(
        agent_id="lead_nurture",
        display_name="Lead Nurture",
        bucket=Bucket.sales,
        status=Status.existing,
        build_priority=Priority.P1,
        purpose=(
            "Drafts warm follow-up messages or 2–3 touch sequences to re-engage "
            "prospects who haven't moved forward."
        ),
        routes_here_when=(
            "Owner asks for a follow-up sequence for a specific lead",
            "A lead goes stale N days (Phase 4 trigger)",
        ),
        channel=Channel.sequence,
        inputs=(
            field_input("customer_name", required=True, description="Lead's name."),
            field_input("subject", description="What they were interested in."),
            field_input("last_contact_date", "date", description="Last touch."),
            field_input("current_status", description="Pipeline status."),
            field_input("tone_hint", description="Default: warm, not pushy."),
            field_input("touch_count", "number", description="Touches (default 3)."),
        ),
        shared_context_reads=(
            "business_profile",
            "pipeline_state",
            "agent_run_history",
        ),
        title_format="{N}-touch follow-up sequence — {customer_name}, {subject}",
        body_format="Delimited sections per touch, relative dates, channel per touch.",
        reasoning_trace_steps=(
            "Business profile",
            "Pipeline state",
            "Prior outreach",
            "Drafted reply",
        ),
        routing_keywords=(
            "follow up",
            "follow-up",
            "nurture",
            "re-engage",
            "reach back out",
            "stale lead",
            "hasn't responded",
            "sequence",
        ),
        example_interactions=(
            Example(
                owner_ask=(
                    "Write a 3-touch follow-up for Dana who asked about a "
                    "consultation two weeks ago and went quiet."
                ),
                expected_route="lead_nurture",
                expected_output_excerpt="Touch 1 — Today",
            ),
        ),
    )

    def build(
        self, ask: OwnerAsk, context: SharedContext, trace: ReasoningTrace
    ) -> AgentResult:
        profile = context.business_profile
        channel = self.channel_for(ask)

        customer_name = ask.param("customer_name") or topic_from(ask.text, default="there")
        subject = ask.param("subject") or topic_from(ask.text, default="your inquiry")
        touch_count = int(ask.param("touch_count", 3) or 3)
        touch_count = max(2, min(3, touch_count))

        lead = context.lead_for(customer_name)
        trace.record_load(
            "Pipeline state",
            lead,
            describe=lambda l: f"{l.name} — status {l.status}",
            skip_if_empty=True,
        )
        prior = [r for r in context.agent_run_history if r.agent_id == self.spec.agent_id]
        trace.record_load(
            "Prior outreach",
            prior,
            describe=lambda p: f"{len(p)} earlier nurture run(s) — avoiding repeats",
            skip_if_empty=True,
        )

        signoff = profile.signoff()
        biz = profile.value("business_name") or "us"

        # Relative-date, channel-labelled touches (QA: never "Day 1 / Day 5").
        plan = [(0, "Text"), (5, "Email"), (12, "Text")][:touch_count]
        lines: list[str] = []
        bodies = [
            (
                f"Hi {customer_name}, it's {signoff or biz}. Just circling back on "
                f"{subject} — happy to answer any questions whenever you're ready."
            ),
            (
                f"Hi {customer_name}, following up on {subject}. No rush at all — "
                f"if it's helpful I can walk you through the options. Want me to send "
                f"a few details over?"
            ),
            (
                f"Hi {customer_name}, last note from me on {subject} for now. The door's "
                f"open whenever the timing's right — just reply here and we'll pick it up."
            ),
        ]
        for i, (offset, ch) in enumerate(plan):
            lines.append(touch_label(i + 1, offset, ch))
            msg = bodies[i]
            if ch == "Text":
                msg = f"{msg} {sms_optout()}"
            lines.append(msg)
            lines.append("")
        fallback = "\n".join(lines).strip()

        system = (
            "You draft a warm, low-pressure follow-up sequence for a small business "
            "lead. Use relative date labels (Today, +5 days), show each touch's "
            "channel, vary the message, and keep the real business name in signoffs. "
            "Never use bracketed placeholders. Plain text per touch."
        )
        prompt = (
            f"Business: {profile.loaded_summary() or 'unknown'}\n"
            f"Lead: {customer_name}, interested in {subject}\n"
            f"Touches: {touch_count}\n"
            "Draft the sequence."
        )
        body, _ = self.draft(trace=trace, system=system, prompt=prompt, fallback=fallback)

        title = f"{touch_count}-touch follow-up sequence — {customer_name}, {subject}"
        return AgentResult(
            agent_id=self.spec.agent_id,
            channel=channel,
            title=title,
            body=body,
            trace=trace,
            metadata={"touch_count": touch_count, "subject": subject},
        )


class QuoteFollowUpAgent(BaseAgent):
    spec = build_spec(
        agent_id="quote_follow_up",
        display_name="Quote Follow-up",
        bucket=Bucket.sales,
        status=Status.new,
        build_priority=Priority.P2,
        purpose=(
            "Lead-nurture variant tuned for unresponded quotes. Carries the quote "
            "amount and scope, with quote-specific framing."
        ),
        routes_here_when=(
            "Owner asks to follow up on a specific quote that hasn't been booked",
            "Quote sent → +3/+7/+14 days with no booking (Phase 4 event)",
        ),
        channel=Channel.sequence,
        secondary_channels=(Channel.sms,),
        inputs=(
            field_input("customer_name", required=True, description="Customer's name."),
            field_input("quote_amount", "number", required=True, description="Quote $."),
            field_input("quote_scope", description="What the quote covers."),
            field_input("quote_date", "date", description="When sent."),
            field_input("touch_count", "number", description="Touches (default 3)."),
        ),
        shared_context_reads=("business_profile", "pipeline_state"),
        title_format="Quote follow-up — {customer_name}, ${quote_amount} {quote_scope}",
        body_format="Sequence with quote-specific framing per touch.",
        reasoning_trace_steps=(
            "Business profile",
            "Pipeline state",
            "Drafted reply",
        ),
        routing_keywords=(
            "follow up on the quote",
            "quote follow",
            "chase the quote",
            "quote i sent",
            "estimate i sent",
            "unresponded quote",
        ),
        example_interactions=(
            Example(
                owner_ask=(
                    "Follow up with Mike on the $1,100 brake job quote I sent last "
                    "week — he hasn't booked."
                ),
                expected_route="quote_follow_up",
                expected_output_excerpt="quote",
            ),
        ),
    )

    def build(
        self, ask: OwnerAsk, context: SharedContext, trace: ReasoningTrace
    ) -> AgentResult:
        profile = context.business_profile
        channel = self.channel_for(ask)

        customer_name = ask.param("customer_name") or topic_from(ask.text, default="there")
        amount = ask.param("quote_amount")
        scope = ask.param("quote_scope") or "the work we discussed"
        touch_count = int(ask.param("touch_count", 3) or 3)
        touch_count = max(2, min(3, touch_count))

        lead = context.lead_for(customer_name)
        trace.record_load(
            "Pipeline state",
            lead,
            describe=lambda l: f"{l.name} — status {l.status}, quote {money(l.quote_amount)}",
            skip_if_empty=True,
        )

        amount_str = money(amount) if amount is not None else ""
        signoff = profile.signoff()
        quote_ref = f"the {amount_str} quote for {scope}" if amount_str else f"the quote for {scope}"

        plan = [(0, "Text"), (4, "Email"), (10, "Text")][:touch_count]
        bodies = [
            (
                f"Hi {customer_name}, just checking in on {quote_ref}. Happy to walk "
                f"through anything or adjust the scope if that helps — let me know."
            ),
            (
                f"Hi {customer_name}, following up on {quote_ref}. The pricing holds for "
                f"now, and I can get you on the schedule quickly once you're ready. Any "
                f"questions I can answer?"
            ),
            (
                f"Hi {customer_name}, last check-in on {quote_ref}. If the timing or "
                f"budget isn't right, no problem — just let me know and I'll keep it on file."
            ),
        ]
        lines: list[str] = []
        for i, (offset, ch) in enumerate(plan):
            lines.append(touch_label(i + 1, offset, ch))
            msg = bodies[i]
            if ch == "Text":
                msg = f"{msg} {sms_optout()}"
            lines.append(msg)
            if signoff:
                lines.append(f"— {signoff}")
            lines.append("")
        fallback = "\n".join(lines).strip()

        system = (
            "You draft a quote follow-up sequence for a small business. Softer than "
            "chasing payment, sharper than generic nurture. Reference the quote amount "
            "and scope, keep relative dates and channel labels, real business name in "
            "signoffs, no bracketed placeholders. Plain text per touch."
        )
        prompt = (
            f"Business: {profile.loaded_summary() or 'unknown'}\n"
            f"Customer: {customer_name}\nQuote: {amount_str or '(amount unknown)'} for {scope}\n"
            f"Touches: {touch_count}\nDraft the sequence."
        )
        body, _ = self.draft(trace=trace, system=system, prompt=prompt, fallback=fallback)

        title = f"Quote follow-up — {customer_name}, {amount_str} {scope}".strip()
        return AgentResult(
            agent_id=self.spec.agent_id,
            channel=channel,
            title=title,
            body=body,
            trace=trace,
            metadata={"quote_amount": amount, "quote_scope": scope},
        )
