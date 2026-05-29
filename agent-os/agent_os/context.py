"""Shared context / data layer (architecture §3.1 piece 4).

Single source of truth for everything an agent might reference: the business
profile (substrate), widget conversation history, pipeline/lead state, and agent
run history. Anything not present is simply empty — agents must behave honestly
when that's the case.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from agent_os.profile import BusinessProfile


@dataclass
class WidgetConversation:
    contact_name: str | None
    summary: str
    intent: str  # question | booking | complaint | sales_pitch | spam | qualified_lead
    occurred_on: date
    transcript: str = ""
    topics: tuple[str, ...] = ()


@dataclass
class Lead:
    name: str
    status: str  # new | contacted | quoted | booked | won | lost | stale
    subject: str = ""
    last_contact: date | None = None
    quote_amount: float | None = None


@dataclass
class Appointment:
    customer_name: str
    service: str
    when: datetime
    status: str = "scheduled"  # scheduled | completed | no_show | cancelled


@dataclass
class AgentRun:
    agent_id: str
    title: str
    when: datetime
    approved: bool
    sent: bool = False


@dataclass
class SharedContext:
    """Bundles every data source an agent can read from."""

    business_profile: BusinessProfile = field(default_factory=BusinessProfile)
    widget_history: list[WidgetConversation] = field(default_factory=list)
    pipeline: list[Lead] = field(default_factory=list)
    appointments: list[Appointment] = field(default_factory=list)
    agent_run_history: list[AgentRun] = field(default_factory=list)
    # "Today" is injectable so reports and relative dates are deterministic in
    # tests and demos.
    today: date = field(default_factory=date.today)

    # ----- query helpers -----
    def widget_search(self, term: str) -> list[WidgetConversation]:
        term = term.lower()
        return [
            c
            for c in self.widget_history
            if term in c.summary.lower()
            or term in c.transcript.lower()
            or any(term in t.lower() for t in c.topics)
        ]

    def lead_for(self, name: str) -> Lead | None:
        name = name.lower()
        for lead in self.pipeline:
            if lead.name.lower() == name:
                return lead
        return None

    def stale_leads(self) -> list[Lead]:
        return [lead for lead in self.pipeline if lead.status == "stale"]

    def appointments_on(self, day: date) -> list[Appointment]:
        return [
            a
            for a in self.appointments
            if a.when.date() == day and a.status == "scheduled"
        ]
