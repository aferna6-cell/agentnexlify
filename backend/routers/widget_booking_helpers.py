"""Widget booking helpers: booking prep and callback logging.

Extracted from widget_helpers.py god class split (2026-04-18).
Booking extraction logic lives in widget_booking.py (_extract_order_from_response,
_strip_order_json_from_response, etc.). This module is the home for any
future booking-prep helpers that currently have no natural owner.

At split time, no functions from widget_helpers.py belonged here — all booking
logic was already in widget_booking.py. This file is the designated landing
zone for booking-prep concerns extracted from widget_chat.py or widget_booking.py
in the future (e.g. appointment slot pre-fetching, callback payload builders).

WARNING: PEP 563 deferred annotations are incompatible with FastAPI.
It breaks FastAPI's parameter introspection — Pydantic body models and
BackgroundTasks get treated as query params, causing 422 errors.
"""

import logging

logger = logging.getLogger(__name__)

# Future booking-prep helpers go here.
# See widget_booking.py for active booking extraction logic.
