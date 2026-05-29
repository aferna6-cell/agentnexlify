"""Marketing bucket (library §5).

* ``campaign`` — email/SMS promo blasts. QA fixes: front-load $ in subject,
  respect "keep it short", emoji density is a parameter, real-name signoff.
* ``content_writer`` — long-form blog / FAQ / About / service copy (report).
* ``social_post`` — single platform-aware social post (FB/IG/LinkedIn/X).
* ``seo_recommendations`` — on-page checks + best practices, honest about what
  it does NOT check. Sold as "recommendations," never "audit."
"""

from __future__ import annotations

from agent_os.base import BaseAgent
from agent_os.context import SharedContext
from agent_os.result import AgentResult, OwnerAsk
from agent_os.schema import Bucket, Channel, Example, Priority, Status
from agent_os.tools.seo_check import seo_check
from agent_os.trace import ReasoningTrace

from ._helpers import build_spec, field_input, sms_optout, topic_from

_SHORT_HINTS = ("keep it short", "short", "brief", "one line", "quick")


class CampaignAgent(BaseAgent):
    spec = build_spec(
        agent_id="campaign",
        display_name="Campaign",
        bucket=Bucket.marketing,
        status=Status.existing,
        build_priority=Priority.P1,
        purpose=(
            "Drafts a marketing campaign — email blast or short-form SMS promo "
            "— with a mobile-optimized subject and a clear offer."
        ),
        routes_here_when=(
            "Owner asks for a campaign, email blast, or promo announcement",
            "Owner asks for a subject line + body for a marketing send",
        ),
        channel=Channel.email,
        secondary_channels=(Channel.sms,),
        inputs=(
            field_input("campaign_name", description="Internal name for the send."),
            field_input("audience", description="existing / new / all."),
            field_input("offer_details", description="Price, dates, eligibility."),
            field_input("tone_hint", description="Voice. Default: warm, direct."),
            field_input("length_hint", description="'keep it short' respected."),
            field_input("emoji_density", description="none | low | medium. Default low."),
        ),
        shared_context_reads=("business_profile", "pipeline_state"),
        title_format="Email blast — {campaign_name} ({offer_summary})",
        body_format="Subject (≤30 char, $ front-loaded), preheader, body.",
        reasoning_trace_steps=(
            "Business profile",
            "Audience sizing",
            "Drafted campaign",
        ),
        routing_keywords=(
            "campaign",
            "email blast",
            "blast",
            "promo",
            "promotion",
            "announcement",
            "subject line",
            "marketing email",
            "newsletter",
            "special offer",
        ),
        example_interactions=(
            Example(
                owner_ask=(
                    "Write a campaign email for $50 off first details this month, "
                    "keep it short."
                ),
                expected_route="campaign",
                expected_output_excerpt="Subject:",
            ),
        ),
    )

    def build(
        self, ask: OwnerAsk, context: SharedContext, trace: ReasoningTrace
    ) -> AgentResult:
        profile = context.business_profile
        channel = self.channel_for(ask)

        offer = ask.param("offer_details") or topic_from(ask.text, default="our latest offer")
        audience = ask.param("audience") or "existing"
        keep_short = bool(
            ask.param("length_hint")
            and any(h in str(ask.param("length_hint")).lower() for h in _SHORT_HINTS)
        ) or any(h in ask.text.lower() for h in _SHORT_HINTS)
        emoji_density = (ask.param("emoji_density") or "low").lower()

        # Audience sizing: honest — only counts if pipeline data is present.
        size = len(context.pipeline)
        trace.record_load(
            "Audience sizing",
            context.pipeline,
            describe=lambda p: f"{len(p)} contact(s) in pipeline ({audience})",
            skip_if_empty=True,
        )

        biz = profile.value("business_name") or "us"
        signoff = profile.signoff()

        # QA fix: front-load the price/$ in the subject so it survives ~30-char
        # mobile clipping. Subject stays plain text on both channels.
        subject_offer = _front_load_money(offer)
        subject = subject_offer[:30].rstrip(" -—:")
        emoji = "" if emoji_density == "none" else ("🎉 " if emoji_density == "medium" else "")

        if channel == Channel.sms:
            # SMS: plain text, tight, opt-out. No subject line framing.
            body = (
                f"{emoji}{biz}: {offer}. Reply or call to claim it. {sms_optout()}"
            ).strip()
        else:
            preheader = f"{offer} — from {biz}"
            lines = [
                f"Subject: {subject}",
                f"Preheader: {preheader}",
                "",
                f"Hi there,",
                f"{offer}.",
            ]
            if not keep_short:
                lines.append(
                    "It's our way of saying thanks for being a customer — "
                    "book whenever works for you and we'll take care of the rest."
                )
            lines.append("")
            lines.append(f"— {signoff}" if signoff else f"— {biz}")
            body = "\n".join(lines).strip()

        system = (
            "You draft a small-business marketing campaign. Front-load the price "
            "or discount in the subject line (≤30 chars, mobile inboxes clip). "
            "Respect a 'keep it short' request: do not add deliverables the owner "
            "didn't ask for. Use the real business name in the signoff. Low emoji "
            "density. Never use bracketed placeholders."
        )
        prompt = (
            f"Business: {profile.loaded_summary() or 'unknown'}\n"
            f"Offer: {offer}\nAudience: {audience} ({size} contacts)\n"
            f"Channel: {channel.value}\nKeep short: {keep_short}\n"
            f"Emoji density: {emoji_density}\nDraft the campaign."
        )
        body, _ = self.draft(
            trace=trace, system=system, prompt=prompt, fallback=body,
            step_name="Drafted campaign",
        )

        name = ask.param("campaign_name") or topic_from(offer, default="promo")
        title = f"Email blast — {name} ({offer[:32]})"
        return AgentResult(
            agent_id=self.spec.agent_id,
            channel=channel,
            title=title,
            body=body,
            trace=trace,
            metadata={"audience": audience, "keep_short": keep_short},
        )


class ContentWriterAgent(BaseAgent):
    spec = build_spec(
        agent_id="content_writer",
        display_name="Content Writer",
        bucket=Bucket.marketing,
        status=Status.new,
        build_priority=Priority.P2,
        purpose=(
            "Drafts longer-form content — blog posts, web copy, FAQs, About Us, "
            "service descriptions — for the owner to publish."
        ),
        routes_here_when=(
            "Owner asks for a blog post, article, or web copy",
            "Owner asks to draft FAQ entries, About Us copy, or service descriptions",
        ),
        channel=Channel.report,
        inputs=(
            field_input("topic", required=True, description="What to write about."),
            field_input("format", description="blog | faq | about | service."),
            field_input("target_length", "number", description="Approx words."),
            field_input("tone_hint", description="Voice."),
            field_input("seo_keywords", "array", description="Optional keywords."),
            field_input("audience", description="Who it's for."),
        ),
        title_format="{format} — {topic}",
        body_format="Structured long-form per format (markdown allowed).",
        reasoning_trace_steps=("Business profile", "Drafted content"),
        routing_keywords=(
            "blog",
            "blog post",
            "article",
            "web copy",
            "website copy",
            "about us",
            "faq",
            "service description",
            "long form",
            "write a post about",
        ),
        example_interactions=(
            Example(
                owner_ask="Write a blog post about why ceramic coating is worth it.",
                expected_route="content_writer",
                expected_output_excerpt="ceramic",
            ),
        ),
    )

    def build(
        self, ask: OwnerAsk, context: SharedContext, trace: ReasoningTrace
    ) -> AgentResult:
        profile = context.business_profile
        channel = self.channel_for(ask)

        topic = ask.param("topic") or topic_from(ask.text, default="your business")
        fmt = (ask.param("format") or "blog").lower()
        biz = profile.value("business_name")
        city = profile.value("city")
        locale = f" in {city}" if city else ""
        byline = f" — {biz}" if biz else ""

        if fmt == "faq":
            fallback = (
                f"## Frequently Asked Questions: {topic}\n\n"
                f"**Q: What should I know about {topic}?**\n"
                f"A: Here's the short version, with the details that actually matter "
                f"for {biz or 'our customers'}{locale}.\n\n"
                f"**Q: How do I get started?**\n"
                f"A: Reach out and we'll walk you through it."
            )
        elif fmt == "about":
            fallback = (
                f"## About {biz or 'Us'}\n\n"
                f"{biz or 'We'} help customers{locale} with {topic}. "
                f"We focus on doing the work right and keeping you informed at "
                f"every step."
            )
        elif fmt == "service":
            fallback = (
                f"## {topic}\n\n"
                f"What it is, who it's for, and what to expect when you book "
                f"{topic} with {biz or 'us'}{locale}."
            )
        else:  # blog
            fallback = (
                f"# {topic}\n\n"
                f"If you've wondered about {topic}, here's a clear rundown.\n\n"
                f"## Why it matters\n\n"
                f"The practical reasons {topic} is worth your attention"
                f"{locale}.\n\n"
                f"## What to do next\n\n"
                f"How {biz or 'we'} can help, and how to get started.{byline}"
            )

        system = (
            "You draft long-form content for a small business owner to publish. "
            "Ground every claim in the business profile; never invent services or "
            "prices. Use the real business name. Markdown headings are fine. Never "
            "use bracketed placeholders."
        )
        prompt = (
            f"Business: {profile.loaded_summary() or 'unknown'}\n"
            f"Format: {fmt}\nTopic: {topic}\n"
            f"Keywords: {ask.param('seo_keywords') or '(none)'}\n"
            "Draft the content."
        )
        body, _ = self.draft(
            trace=trace, system=system, prompt=prompt, fallback=fallback,
            step_name="Drafted content", max_tokens=2048,
        )

        title = f"{fmt.capitalize()} — {topic}"
        return AgentResult(
            agent_id=self.spec.agent_id,
            channel=channel,
            title=title,
            body=body,
            trace=trace,
            metadata={"format": fmt, "topic": topic},
        )


class SocialPostAgent(BaseAgent):
    spec = build_spec(
        agent_id="social_post",
        display_name="Social Post",
        bucket=Bucket.marketing,
        status=Status.new,
        build_priority=Priority.P2,
        purpose="Drafts a single platform-aware social media post or short caption.",
        routes_here_when=(
            "Owner asks for a social post or caption",
            "Campaign agent delegates the social variant of a campaign here",
        ),
        channel=Channel.post,
        inputs=(
            field_input("topic", required=True, description="What to post about."),
            field_input("platform", description="facebook | instagram | linkedin | x."),
            field_input("tone_hint", description="Voice."),
            field_input("length_hint", description="Length nudge."),
            field_input("hashtags_wanted", "boolean", description="Default false."),
            field_input("cta", description="Optional call to action."),
        ),
        title_format="Social post ({platform}) — {topic}",
        body_format="Platform-appropriate plain text (post channel).",
        reasoning_trace_steps=("Business profile", "Drafted post"),
        routing_keywords=(
            "social post",
            "social media",
            "caption",
            "facebook post",
            "instagram",
            "linkedin post",
            "tweet",
            "post about",
        ),
        example_interactions=(
            Example(
                owner_ask="Write an Instagram caption about our spring detailing special.",
                expected_route="social_post",
                expected_output_excerpt="spring",
            ),
        ),
    )

    def build(
        self, ask: OwnerAsk, context: SharedContext, trace: ReasoningTrace
    ) -> AgentResult:
        profile = context.business_profile
        channel = self.channel_for(ask)

        topic = ask.param("topic") or topic_from(ask.text, default="our latest")
        platform = (ask.param("platform") or "facebook").lower()
        cta = ask.param("cta")
        biz = profile.value("business_name") or "us"

        cta_line = cta or "Reach out to book."

        if platform in ("x", "twitter"):
            # ≤280 chars, plain text.
            fallback = f"{topic.capitalize()} at {biz}. {cta_line}"[:280]
        elif platform == "linkedin":
            fallback = (
                f"A quick note on {topic}.\n\n"
                f"At {biz}, we've found this matters more than people expect — "
                f"here's why, and what we do about it.\n\n"
                f"{cta_line}"
            )
        else:  # facebook / instagram ~200-500 chars
            fallback = (
                f"{topic.capitalize()} 🚗 At {biz}, we want to make this easy for you. "
                f"{cta_line}"
            )

        system = (
            f"You draft one {platform} post for a small business. Match the "
            "platform's natural length (Facebook/Instagram ~200-500 chars, "
            "LinkedIn 1-3 short paragraphs, X ≤280). Plain text — no markdown "
            "headers or asterisks. Use the real business name. Hashtags only if "
            "asked. Never use bracketed placeholders."
        )
        prompt = (
            f"Business: {profile.loaded_summary() or 'unknown'}\n"
            f"Platform: {platform}\nTopic: {topic}\nCTA: {cta or '(none)'}\n"
            f"Hashtags: {bool(ask.param('hashtags_wanted'))}\nDraft the post."
        )
        body, _ = self.draft(
            trace=trace, system=system, prompt=prompt, fallback=fallback,
            step_name="Drafted post",
        )

        title = f"Social post ({platform}) — {topic}"
        return AgentResult(
            agent_id=self.spec.agent_id,
            channel=channel,
            title=title,
            body=body,
            trace=trace,
            metadata={"platform": platform, "topic": topic},
        )


class SeoRecommendationsAgent(BaseAgent):
    spec = build_spec(
        agent_id="seo_recommendations",
        display_name="SEO Recommendations",
        bucket=Bucket.marketing,
        status=Status.workaround,
        build_priority=Priority.P3,
        purpose=(
            "Returns on-page SEO checks for the owner's URL plus best-practice "
            "recommendations. Honest about what it does NOT check yet."
        ),
        routes_here_when=(
            "Owner asks for an SEO check / SEO recommendations / SEO audit",
        ),
        channel=Channel.report,
        inputs=(
            field_input("url", description="Defaults to business_profile.website."),
        ),
        tool_dependencies=("seo_check",),
        title_format="SEO recommendations — {domain}",
        body_format="On-page findings + recommendations + explicit not-checked list.",
        reasoning_trace_steps=("Business profile", "On-page check", "Drafted report"),
        routing_keywords=(
            "seo",
            "seo audit",
            "seo check",
            "seo recommendations",
            "search ranking",
            "google ranking",
            "meta description",
            "title tag",
        ),
        example_interactions=(
            Example(
                owner_ask="Can you run an SEO check on my website?",
                expected_route="seo_recommendations",
                expected_output_excerpt="Not checked yet",
            ),
        ),
    )

    def build(
        self, ask: OwnerAsk, context: SharedContext, trace: ReasoningTrace
    ) -> AgentResult:
        profile = context.business_profile
        channel = self.channel_for(ask)
        messages: list[str] = []

        url = ask.param("url") or profile.value("website")
        if not url:
            trace.note("On-page check", "no URL — owner has no website on file")
            result = AgentResult(
                agent_id=self.spec.agent_id,
                channel=channel,
                title="SEO recommendations — (no website on file)",
                body=(
                    "## SEO recommendations\n\n"
                    "I don't have a website URL for your business yet, so I can't "
                    "run on-page checks. Add your website and I'll check the basics "
                    "(title tag, meta description, headings, mobile viewport, image "
                    "alt text) and give you recommendations.\n\n"
                    "### Not checked yet (any version)\n"
                    "- Backlinks\n- Keyword rankings\n- Competitor analysis"
                ),
                trace=trace,
                metadata={"had_url": False},
            )
            result.add_orchestrator_message(
                "No website on file — add it to your business profile and I can run "
                "on-page SEO checks."
            )
            return result

        report = seo_check(url)
        # Honest load: the check only "loaded" if the fetch succeeded.
        trace.record_load(
            "On-page check",
            report.findings if report.fetched else None,
            describe=lambda f: f"{len(f)} on-page signal(s) for {report.domain}",
            fallback_note=f"could not fetch {report.domain} — giving best-practice guidance only",
        )
        if not report.fetched:
            messages.append(
                f"I couldn't fetch {report.domain} (it may be down or blocking "
                f"automated requests), so this is best-practice guidance rather than "
                f"a live check of your page."
            )

        finding_lines = "\n".join(f"- {f}" for f in report.findings) or "- (no live findings)"
        body = (
            f"## SEO recommendations — {report.domain}\n\n"
            f"### On-page checks\n{finding_lines}\n\n"
            f"### Recommendations\n"
            f"- Keep your title tag under ~60 characters and lead with what you do.\n"
            f"- Write a meta description (~150 chars) that includes your city.\n"
            f"- Use one H1 and structure the rest with H2s.\n"
            f"- Add descriptive alt text to images.\n\n"
            f"### Not checked yet\n"
            f"These need infrastructure we haven't built — they're honestly out of "
            f"scope for now:\n"
            f"- Backlinks / off-page authority\n"
            f"- Keyword rankings in search results\n"
            f"- Competitor analysis"
        )

        title = f"SEO recommendations — {report.domain}"
        result = AgentResult(
            agent_id=self.spec.agent_id,
            channel=channel,
            title=title,
            body=body,
            trace=trace,
            metadata={"had_url": True, "fetched": report.fetched},
        )
        for m in messages:
            result.add_orchestrator_message(m)
        return result


def _front_load_money(text: str) -> str:
    """Move a $/percent token to the front of *text* for subject lines."""

    import re

    m = re.search(r"(\$\s?\d[\d,]*|\d+%)", text)
    if not m:
        return text
    token = m.group(1).replace(" ", "")
    rest = (text[: m.start()] + text[m.end():]).strip(" ,.-—")
    return f"{token} {rest}".strip()
