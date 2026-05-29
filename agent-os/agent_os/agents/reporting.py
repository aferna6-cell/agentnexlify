"""Reporting bucket (library §9).

* ``weekly_briefing`` — an owner-facing weekly summary. QA rule: OMIT empty
  sections entirely. Never pad with "none this week" filler — a section only
  appears when it has real content behind it.
"""

from __future__ import annotations

from datetime import timedelta

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
    TriggerType,
)
from agent_os.trace import ReasoningTrace

from ._helpers import build_spec, field_input, money


class WeeklyBriefingAgent(BaseAgent):
    spec = build_spec(
        agent_id="weekly_briefing",
        display_name="Weekly Briefing",
        bucket=Bucket.reporting,
        status=Status.new,
        build_priority=Priority.P3,
        purpose=(
            "Compiles an owner-facing weekly briefing from real activity: new "
            "leads, appointments, quotes, and drafts produced. Empty sections are "
            "omitted entirely — no filler."
        ),
        routes_here_when=(
            "Owner asks for a weekly summary or recap",
            "Scheduled Monday-morning briefing (Phase 4 trigger)",
        ),
        channel=Channel.report,
        inputs=(
            field_input("window_days", "number", description="Look-back window (default 7)."),
        ),
        shared_context_reads=(
            "business_profile",
            "pipeline_state",
            "appointments",
            "agent_run_history",
        ),
        triggers_supported=(TriggerType.manual, TriggerType.scheduled),
        permission_scope=PermissionScope(
            require_owner_approval=False,
            notes="Internal owner report — nothing customer-facing to send.",
        ),
        title_format="Weekly briefing — {date}",
        body_format="Markdown report. Only sections with real content appear.",
        reasoning_trace_steps=(
            "Business profile",
            "Pipeline",
            "Appointments",
            "Agent activity",
            "Drafted briefing",
        ),
        routing_keywords=(
            "weekly summary",
            "weekly briefing",
            "recap",
            "how did we do",
            "this week's numbers",
            "what happened this week",
            "report",
        ),
        example_interactions=(
            Example(
                owner_ask="Give me the weekly briefing.",
                expected_route="weekly_briefing",
                expected_output_excerpt="briefing",
            ),
        ),
    )

    def build(
        self, ask: OwnerAsk, context: SharedContext, trace: ReasoningTrace
    ) -> AgentResult:
        profile = context.business_profile
        channel = self.channel_for(ask)
        biz = profile.value("business_name") or "your business"

        window_days = int(ask.param("window_days", 7) or 7)
        since = context.today - timedelta(days=window_days)

        # Gather real activity. Each load is recorded honestly; empty buckets
        # skip their trace step rather than faking a green check.
        leads = context.pipeline
        recent_leads = [l for l in leads if l.last_contact and l.last_contact >= since]
        trace.record_load(
            "Pipeline",
            recent_leads,
            describe=lambda d: f"{len(d)} lead(s) touched since {since.isoformat()}",
            skip_if_empty=True,
        )

        upcoming = [
            a for a in context.appointments
            if a.when.date() >= context.today and a.status == "scheduled"
        ]
        trace.record_load(
            "Appointments",
            upcoming,
            describe=lambda d: f"{len(d)} upcoming appointment(s)",
            skip_if_empty=True,
        )

        recent_runs = [
            r for r in context.agent_run_history if r.when.date() >= since
        ]
        trace.record_load(
            "Agent activity",
            recent_runs,
            describe=lambda d: f"{len(d)} draft(s) produced this week",
            skip_if_empty=True,
        )

        # Build the report — a section is only emitted when it has content.
        sections: list[str] = [f"Weekly briefing — {biz}", f"Week ending {context.today.isoformat()}", ""]

        won = [l for l in recent_leads if l.status == "won"]
        new_leads = [l for l in recent_leads if l.status in ("new", "contacted")]
        quoted = [l for l in recent_leads if l.status == "quoted"]
        stale = [l for l in leads if l.status == "stale"]

        if new_leads:
            sections.append(f"## New & active leads ({len(new_leads)})")
            sections += [f"- {l.name} — {l.subject or 'inquiry'} ({l.status})" for l in new_leads]
            sections.append("")
        if quoted:
            total = sum(l.quote_amount or 0 for l in quoted)
            sections.append(f"## Outstanding quotes ({len(quoted)}, {money(total)})")
            sections += [
                f"- {l.name} — {money(l.quote_amount)} for {l.subject or 'work'}"
                for l in quoted
            ]
            sections.append("")
        if won:
            total = sum(l.quote_amount or 0 for l in won)
            sections.append(f"## Closed won ({len(won)}, {money(total)})")
            sections += [f"- {l.name} — {money(l.quote_amount)}" for l in won]
            sections.append("")
        if upcoming:
            sections.append(f"## Upcoming appointments ({len(upcoming)})")
            sections += [
                f"- {a.customer_name} — {a.service}, {a.when.strftime('%a %-I:%M %p')}"
                for a in upcoming[:10]
            ]
            sections.append("")
        if stale:
            sections.append(f"## Needs follow-up ({len(stale)})")
            sections += [f"- {l.name} — {l.subject or 'inquiry'}" for l in stale]
            sections.append("")
        if recent_runs:
            sections.append(f"## Drafts prepared ({len(recent_runs)})")
            sections += [f"- {r.title}" for r in recent_runs[:10]]
            sections.append("")

        # If nothing happened, say so once — honestly — instead of empty headers.
        had_content = any(s.startswith("## ") for s in sections)
        if not had_content:
            sections.append(
                "Quiet week — no new leads, quotes, appointments, or drafts in the "
                f"last {window_days} days on record. Nothing to action."
            )
        fallback = "\n".join(sections).strip()

        system = (
            "You write a concise weekly briefing for a small-business owner from "
            "the structured activity provided. Include only sections that have "
            "real content — never add an empty section or 'none this week' filler. "
            "Use the real business name. Markdown headings are fine (report channel)."
        )
        prompt = (
            f"Business: {profile.loaded_summary() or 'unknown'}\n"
            f"New/active leads: {len(new_leads)}\nQuotes out: {len(quoted)}\n"
            f"Closed won: {len(won)}\nUpcoming appts: {len(upcoming)}\n"
            f"Stale: {len(stale)}\nDrafts: {len(recent_runs)}\n"
            "Write the briefing, omitting any empty section."
        )
        body, _ = self.draft(
            trace=trace, system=system, prompt=prompt, fallback=fallback,
            step_name="Drafted briefing", max_tokens=1536,
        )

        return AgentResult(
            agent_id=self.spec.agent_id,
            channel=channel,
            title=f"Weekly briefing — {context.today.isoformat()}",
            body=body,
            trace=trace,
            requires_approval=False,
            metadata={
                "new_leads": len(new_leads),
                "quotes": len(quoted),
                "won": len(won),
                "appointments": len(upcoming),
            },
        )
