"""Booking aggregator — re-exports from sibling modules to preserve public API.

This file used to be a god class (~620 lines). It was split per Rule 9 into:
- booking_hours.py — business hours config (get/upsert/exception lookup)
- booking_slots.py — available slot generation
- booking_lifecycle.py — appointment CRUD + lead linking
- booking_recurring.py — recurring series generation
- booking_confirmation.py — email/SMS confirmation messaging
- booking_reschedule.py — signed reschedule URL helpers

Test patches target `backend.services.booking.X` — siblings use a deferred
import (`from backend.services import booking as _b`) so this aggregator is
the single source of truth for all symbols. Do not rename functions here
without updating both the sibling and the test patch sites.
"""


import logging

from backend.config import settings
from backend.models.database import get_service_supabase
from backend.services.tenant_scope import tenant_table

from backend.services.booking_confirmation import (
    _reschedule_link_html,
    _send_appointment_confirmation,
)
from backend.services.booking_hours import (
    DAY_NAMES,
    DEFAULT_HOURS,
    _get_exception_for_date,
    get_business_hours,
    upsert_business_hours,
)
from backend.services.booking_lifecycle import (
    cancel_appointment,
    create_appointment,
    link_appointment_to_lead,
    list_appointments,
    update_appointment,
)
from backend.services.booking_recurring import create_recurring_series
from backend.services.booking_reschedule import (
    _RESCHEDULE_TOKEN_TTL_SECONDS,
    _generate_reschedule_token,
    build_reschedule_url,
)
from backend.services.booking_slots import generate_available_slots

logger = logging.getLogger(__name__)

__all__ = [
    "DAY_NAMES",
    "DEFAULT_HOURS",
    "_RESCHEDULE_TOKEN_TTL_SECONDS",
    "_generate_reschedule_token",
    "_get_exception_for_date",
    "_reschedule_link_html",
    "_send_appointment_confirmation",
    "build_reschedule_url",
    "cancel_appointment",
    "create_appointment",
    "create_recurring_series",
    "generate_available_slots",
    "get_business_hours",
    "get_service_supabase",
    "link_appointment_to_lead",
    "list_appointments",
    "logger",
    "settings",
    "tenant_table",
    "update_appointment",
    "upsert_business_hours",
]
