"""Factory functions for reusable smart list templates.

Smart lists are saved filters over `leads`, `appointments`, or `invoices`.
The filter dict is JSON-serialized into the smart_lists.filter column; the
automation_engine evaluates it on demand.
"""

from backend.services.industry_packs.base import SmartListTemplate


def make_lapsed_clients_list(
    *, months_since_last_visit: int = 6,
) -> SmartListTemplate:
    """Leads whose last appointment was more than N months ago."""
    return SmartListTemplate(
        key="lapsed_clients",
        name=f"Lapsed Clients ({months_since_last_visit}mo+)",
        description=(
            f"Active clients whose last appointment was more than "
            f"{months_since_last_visit} months ago. Used by the reactivation "
            "weekly cron."
        ),
        entity="leads",
        filter={
            "last_appointment_date": {"lt": f"now-{months_since_last_visit * 30}d"},
            "status": {"in": ["active", "customer"]},
        },
    )


def make_overdue_invoices_list(*, min_days_overdue: int = 3) -> SmartListTemplate:
    """Invoices past due by more than N days."""
    return SmartListTemplate(
        key="overdue_invoices",
        name=f"Overdue Invoices ({min_days_overdue}d+)",
        description=(
            f"Invoices that are more than {min_days_overdue} days past their "
            "due date and still unpaid. Used by the dunning ladder trigger."
        ),
        entity="invoices",
        filter={
            "status": "overdue",
            "days_overdue": {"gte": min_days_overdue},
        },
    )


def make_unresponded_leads_list(*, hours_since_inquiry: int = 24) -> SmartListTemplate:
    """Leads that came in more than N hours ago with no reply from staff."""
    return SmartListTemplate(
        key="unresponded_leads",
        name=f"Unresponded Leads ({hours_since_inquiry}h+)",
        description=(
            f"Leads who haven't received a staff reply within "
            f"{hours_since_inquiry} hours of inquiry. A revenue leak if this "
            "list grows."
        ),
        entity="leads",
        filter={
            "first_reply_sent_at": None,
            "created_at": {"lt": f"now-{hours_since_inquiry}h"},
            "status": {"ne": "disqualified"},
        },
    )
