"""The demo fixture — a realistic small-business profile and pipeline.

Bright Auto is a fictional Austin auto-repair shop. The profile is fully
populated (all six core fields + hours, services, review link, payment link,
knowledge base) so drafts come out grounded and placeholder-free. The pipeline,
appointments, run history, and widget conversations are shaped so the demo
exercises every routing rule: a known quote (specialty rule), a complaint, a
channel request, a bucket query, and an out-of-scope ask (generalist + wishlist).
"""

from __future__ import annotations

from datetime import date, datetime

from agent_os.context import (
    AgentRun,
    Appointment,
    Lead,
    SharedContext,
    WidgetConversation,
)
from agent_os.profile import BusinessProfile, KBEntry
from agent_os.result import OwnerAsk

# A fixed "today" keeps relative dates and the weekly briefing deterministic.
TODAY = date(2026, 5, 28)


def sample_profile() -> BusinessProfile:
    return BusinessProfile(
        business_name="Bright Auto",
        owner_name="Sam Rivera",
        industry="auto repair",
        city="Austin",
        phone="512-555-0100",
        website="brightauto.com",
        email="hello@brightauto.com",
        services=[
            "oil changes",
            "brake service",
            "tire rotation",
            "engine diagnostics",
            "hybrid service",
        ],
        hours="Mon–Fri 7:30am–6pm, Sat 8am–2pm",
        timezone="America/Chicago",
        review_link_google="https://g.page/r/brightauto/review",
        payment_link="https://pay.brightauto.com",
        knowledge_base=[
            KBEntry(
                question="Do you work on hybrids?",
                answer=(
                    "Yes — we service hybrid drivetrains and high-voltage "
                    "batteries, including the Prius. Bring it in and we'll run a "
                    "diagnostic."
                ),
                topics=("hybrid", "prius", "battery", "diagnostics"),
            ),
            KBEntry(
                question="What are your hours?",
                answer="We're open Mon–Fri 7:30am–6pm and Sat 8am–2pm.",
                topics=("hours", "open", "schedule"),
            ),
            KBEntry(
                question="Do I need an appointment?",
                answer=(
                    "Walk-ins are welcome for oil changes and tire rotations. For "
                    "brakes, diagnostics, or hybrid work, an appointment gets you "
                    "in faster."
                ),
                topics=("appointment", "walk-in", "booking"),
            ),
        ],
    )


def sample_context() -> SharedContext:
    profile = sample_profile()
    return SharedContext(
        business_profile=profile,
        today=TODAY,
        pipeline=[
            Lead(
                name="Mike",
                status="quoted",
                subject="brake job",
                last_contact=date(2026, 5, 20),
                quote_amount=1100.0,
            ),
            Lead(
                name="Dana",
                status="stale",
                subject="hybrid battery diagnostic",
                last_contact=date(2026, 5, 12),
            ),
            Lead(
                name="Priya",
                status="new",
                subject="tire rotation",
                last_contact=date(2026, 5, 27),
            ),
        ],
        appointments=[
            Appointment(
                customer_name="Carlos",
                service="oil change",
                when=datetime(2026, 5, 28, 9, 0),
            ),
            Appointment(
                customer_name="Mike",
                service="brake inspection",
                when=datetime(2026, 5, 29, 14, 30),
            ),
        ],
        agent_run_history=[
            AgentRun(
                agent_id="lead_nurture",
                title="Re-engage Dana",
                when=datetime(2026, 5, 15, 10, 0),
                approved=True,
                sent=True,
            ),
            AgentRun(
                agent_id="review_request",
                title="Review ask — Carlos",
                when=datetime(2026, 5, 22, 16, 0),
                approved=True,
                sent=True,
            ),
        ],
        widget_history=[
            WidgetConversation(
                contact_name="Dana",
                summary="Asked whether we service hybrid batteries on a 2018 Prius.",
                intent="question",
                occurred_on=date(2026, 5, 12),
                transcript="Do you guys handle hybrids? My Prius battery feels weak.",
                topics=("hybrid", "prius", "battery"),
            ),
            WidgetConversation(
                contact_name="Greg",
                summary="Furious the tech showed up late and scratched the bumper.",
                intent="complaint",
                occurred_on=date(2026, 5, 24),
                transcript="I'm furious — your tech was two hours late and scratched my bumper.",
                topics=("complaint", "damage", "late"),
            ),
            WidgetConversation(
                contact_name="Priya",
                summary="Wants to book a tire rotation Saturday morning.",
                intent="booking",
                occurred_on=date(2026, 5, 27),
                transcript="Can I get a tire rotation this Saturday?",
                topics=("tire", "rotation", "booking"),
            ),
            WidgetConversation(
                contact_name=None,
                summary="SEO agency cold-pitching their services.",
                intent="sales_pitch",
                occurred_on=date(2026, 5, 26),
                transcript="We can get you to the top of Google, interested?",
                topics=("seo", "pitch"),
            ),
        ],
    )


def sample_asks() -> list[OwnerAsk]:
    """One ask per routing path, in the order the CLI walks them.

    Each ask carries the params the production classifier (Haiku) would extract
    from the owner's sentence — customer name, quote amount, scope, the verbatim
    customer message — so the deterministic demo produces clean, grounded drafts
    instead of routing-only stubs. Routing still keys off ``text``.
    """

    return [
        # Specialty rule: dollar amount + "quote" → quote_follow_up over lead_nurture.
        OwnerAsk(
            text="Follow up with Mike on the $1,100 brake job quote I sent — he hasn't booked.",
            params={
                "customer_name": "Mike",
                "quote_amount": 1100,
                "quote_scope": "the brake job",
            },
        ),
        # Complaint short-circuit → complaint_handler (flagged, always approval).
        OwnerAsk(
            text="A customer is furious our tech showed up late and scratched their bumper. Help me respond.",
            params={
                "customer_name": "Greg",
                "complaint_text": "Your tech showed up two hours late and scratched my bumper.",
            },
        ),
        # Channel inference → review_request on SMS.
        OwnerAsk(
            text="Text Carlos asking for a Google review after his oil change.",
            params={"customer_name": "Carlos"},
        ),
        # KB-grounded customer question.
        OwnerAsk(
            text="A lead asked through the widget if we service hybrid batteries on a Prius. Reply.",
            params={
                "customer_name": "Dana",
                "customer_question": "Do you service hybrid batteries on a 2018 Prius?",
            },
        ),
        # Scheduling.
        OwnerAsk(
            text="Book Priya for a tire rotation this Saturday morning.",
            params={"customer_name": "Priya", "subject": "a tire rotation"},
        ),
        # Reporting.
        OwnerAsk(text="Give me the weekly briefing."),
        # Bucket query (rule 7).
        OwnerAsk(text="What marketing agents do you have?"),
        # Out-of-scope → generalist + wishlist capture (rule 1).
        OwnerAsk(text="Help me think through whether to hire a second technician."),
    ]
