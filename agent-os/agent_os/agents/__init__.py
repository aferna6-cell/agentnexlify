"""Worker agent library — all 18 agents across 8 buckets.

Importing this package registers every agent into the global
:data:`agent_os.registry.REGISTRY`. Each ``register`` call runs static schema
validation, so an import error here means an agent violates the schema or one of
the three rules — exactly the CI gate we want.
"""

from __future__ import annotations

from agent_os.registry import REGISTRY

from .customer_service import ComplaintHandlerAgent, CustomerQuestionAgent
from .finance import (
    InvoiceReminderAgent,
    PaymentFollowUpAgent,
    QuoteGeneratorAgent,
)
from .marketing import (
    CampaignAgent,
    ContentWriterAgent,
    SeoRecommendationsAgent,
    SocialPostAgent,
)
from .reporting import WeeklyBriefingAgent
from .reputation import AiVisibilityStubAgent, ReviewRequestAgent
from .sales import LeadNurtureAgent, QuoteFollowUpAgent
from .scheduling_ops import AppointmentReminderAgent, BookingAgent
from .system import GeneralistAgent, LeadTriageAgent

# Order is bucket-by-bucket for readability; registry stores insertion order.
_AGENT_CLASSES = (
    # customer_service
    CustomerQuestionAgent,
    ComplaintHandlerAgent,
    # sales
    LeadNurtureAgent,
    QuoteFollowUpAgent,
    # marketing
    CampaignAgent,
    ContentWriterAgent,
    SocialPostAgent,
    SeoRecommendationsAgent,
    # scheduling_ops
    BookingAgent,
    AppointmentReminderAgent,
    # finance
    QuoteGeneratorAgent,
    InvoiceReminderAgent,
    PaymentFollowUpAgent,
    # reputation
    ReviewRequestAgent,
    AiVisibilityStubAgent,
    # reporting
    WeeklyBriefingAgent,
    # system
    LeadTriageAgent,
    GeneralistAgent,
)


def register_all() -> None:
    """Instantiate and register every agent. Idempotent within a process."""

    for cls in _AGENT_CLASSES:
        if not REGISTRY.has(cls.spec.agent_id):
            REGISTRY.register(cls())


register_all()

__all__ = [cls.__name__ for cls in _AGENT_CLASSES] + ["register_all", "REGISTRY"]
