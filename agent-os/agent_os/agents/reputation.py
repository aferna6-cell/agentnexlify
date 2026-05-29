"""Reputation bucket (library §8).

* ``review_request`` — post-service review-link asks (SMS or email).
* ``ai_visibility_stub`` — honest v2-beta placeholder that captures interest
  instead of faking an "AI visibility audit" we can't run yet.
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
)
from agent_os.trace import ReasoningTrace

from ._helpers import build_spec, field_input, sms_optout, topic_from


# Review-link profile fields, in the order we prefer to surface them.
_REVIEW_FIELDS = (
    ("review_link_google", "Google"),
    ("review_link_yelp", "Yelp"),
    ("review_link_facebook", "Facebook"),
)


class ReviewRequestAgent(BaseAgent):
    spec = build_spec(
        agent_id="review_request",
        display_name="Review Request",
        bucket=Bucket.reputation,
        status=Status.new,
        build_priority=Priority.P2,
        purpose=(
            "Drafts a short post-service message asking a happy customer to leave "
            "a review, with the real review link when one is on file."
        ),
        routes_here_when=(
            "Owner asks to request a review from a customer",
            "A service is marked complete (Phase 4 trigger)",
        ),
        channel=Channel.sms,
        secondary_channels=(Channel.email,),
        inputs=(
            field_input("customer_name", required=True, description="Who to ask."),
            field_input("service", description="What was done."),
            field_input("platform", description="google | yelp | facebook (default: first on file)."),
        ),
        permission_scope=PermissionScope(
            require_owner_approval=True,
            recipient_filter="completed_service_only",
            send_caps=SendCaps(per_day=None),
            notes="1 request per customer per 90 days (hardcoded). Completed service only.",
        ),
        title_format="Review request — {customer_name}",
        body_format="Short, warm review ask with link. Plain text on SMS.",
        reasoning_trace_steps=("Business profile", "Review link", "Drafted request"),
        routing_keywords=(
            "review",
            "leave a review",
            "ask for a review",
            "google review",
            "feedback",
            "testimonial",
            "rate us",
        ),
        example_interactions=(
            Example(
                owner_ask="Ask Dana to leave us a Google review after her cleaning.",
                expected_route="review_request",
                expected_output_excerpt="review",
            ),
        ),
    )

    def build(
        self, ask: OwnerAsk, context: SharedContext, trace: ReasoningTrace
    ) -> AgentResult:
        profile = context.business_profile
        channel = self.channel_for(ask)

        customer_name = ask.param("customer_name") or topic_from(ask.text, default="there")
        service = ask.param("service") or "your recent visit"
        biz = profile.value("business_name") or "us"
        signoff = profile.signoff()

        # Pick the requested platform's link, else the first link on file.
        requested = (ask.param("platform") or "").lower()
        chosen_label = None
        chosen_link = None
        for field_name, label in _REVIEW_FIELDS:
            link = profile.value(field_name)
            if not link:
                continue
            if requested and requested in label.lower():
                chosen_label, chosen_link = label, link
                break
            if chosen_link is None:
                chosen_label, chosen_link = label, link

        review_msgs: list[str] = []
        trace.record_load(
            "Review link",
            chosen_link,
            describe=lambda _: f"{chosen_label} review link on file",
            fallback_note="no review link on file — asking owner to add one",
        )
        if not chosen_link:
            review_msgs.append(
                "Heads up — no review link (Google/Yelp/Facebook) is in your "
                "business profile yet, so this draft asks for a review without a "
                "direct link. Add one to make it one tap for the customer."
            )

        link_clause = f" Here's the link: {chosen_link}" if chosen_link else ""
        fallback = (
            f"Hi {customer_name}, thanks so much for choosing {biz} for {service}! "
            f"If you have a minute, a quick {chosen_label or 'online'} review really "
            f"helps us out.{link_clause} Thank you!"
        )
        if channel == Channel.email and signoff:
            fallback += f"\n\n— {signoff}, {biz}"
        if channel == Channel.sms:
            fallback = f"{fallback} {sms_optout()}"
            cap = CHANNEL_SOFT_MAX_CHARS[Channel.sms]
            if len(fallback) > cap:
                fallback = fallback[: cap - 1].rstrip() + "…"

        system = (
            "You write a short, warm review request for a happy small-business "
            "customer. Thank them, ask for a review, include the real review link "
            "if one is provided. Use the real business name — never a bracketed "
            "placeholder. Plain text on SMS, light markdown OK on email."
        )
        prompt = (
            f"Business: {profile.loaded_summary() or 'unknown'}\n"
            f"Customer: {customer_name}\nService: {service}\n"
            f"Platform: {chosen_label or '(none on file)'}\n"
            f"Link: {chosen_link or '(none)'}\nChannel: {channel.value}\nDraft the request."
        )
        body, _ = self.draft(
            trace=trace, system=system, prompt=prompt, fallback=fallback,
            step_name="Drafted request",
        )

        result = AgentResult(
            agent_id=self.spec.agent_id,
            channel=channel,
            title=f"Review request — {customer_name}",
            body=body,
            trace=trace,
            metadata={"platform": chosen_label},
        )
        for msg in review_msgs:
            result.add_orchestrator_message(msg)
        return result


class AiVisibilityStubAgent(BaseAgent):
    spec = build_spec(
        agent_id="ai_visibility_stub",
        display_name="AI Visibility (beta)",
        bucket=Bucket.reputation,
        status=Status.stub,
        build_priority=Priority.P4,
        purpose=(
            "Honest placeholder for the v2 'how does your business show up in AI "
            "answers' feature. Explains what's coming and captures interest — "
            "never fakes an audit it can't run yet."
        ),
        routes_here_when=(
            "Owner asks how their business appears in ChatGPT/AI search results",
            "Owner asks about AI visibility or LLM SEO",
        ),
        channel=Channel.report,
        inputs=(
            field_input("query", description="What the owner wanted to check."),
        ),
        permission_scope=PermissionScope(
            require_owner_approval=False,
            notes="Informational only — no customer-facing output, nothing to send.",
        ),
        title_format="AI visibility — coming in v2",
        body_format="Honest status note + what's planned. Markdown OK (report).",
        reasoning_trace_steps=("Business profile", "Feature status", "Drafted note"),
        routing_keywords=(
            "ai visibility",
            "show up in chatgpt",
            "ai search",
            "llm seo",
            "appear in ai",
            "ai answers",
            "generative search",
        ),
        example_interactions=(
            Example(
                owner_ask="How does my business show up when someone asks ChatGPT about plumbers near me?",
                expected_route="ai_visibility_stub",
                expected_output_excerpt="v2",
            ),
        ),
    )

    def build(
        self, ask: OwnerAsk, context: SharedContext, trace: ReasoningTrace
    ) -> AgentResult:
        profile = context.business_profile
        channel = self.channel_for(ask)
        biz = profile.value("business_name") or "your business"

        # No data load here is honest: nothing has been measured. Record the
        # feature status as a decision note, not a green-check data load.
        trace.note(
            "Feature status",
            "AI visibility checks aren't live yet — this is a v2 beta placeholder, "
            "so no audit was run.",
        )

        body = (
            f"AI visibility for {biz} — coming in v2\n\n"
            "Checking how your business shows up inside AI assistants (ChatGPT, "
            "Gemini, AI-powered search) is on the roadmap, not live yet. I'm not "
            "going to run a fake audit and hand you made-up numbers.\n\n"
            "When it ships, it will cover:\n"
            "- Whether AI assistants mention your business for local queries\n"
            "- How your name, services, and hours come through\n"
            "- Gaps to fix so AI answers describe you accurately\n\n"
            "I've logged your interest so you're in the first beta group."
        )

        result = AgentResult(
            agent_id=self.spec.agent_id,
            channel=channel,
            title="AI visibility — coming in v2",
            body=body,
            trace=trace,
            requires_approval=False,
            metadata={"beta_signal": True, "query": ask.param("query") or ask.text},
        )
        result.add_orchestrator_message(
            "Captured an AI-visibility beta interest signal for v2 prioritization."
        )
        return result
