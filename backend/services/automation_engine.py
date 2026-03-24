"""Automation engine — triggers, processes, and executes email sequences."""


import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import anthropic

from backend.config import settings
from backend.models.database import get_supabase
from backend.services.email_sender import send_email, build_unsubscribe_url, render_template, render_sms_template

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL = "claude-sonnet-4-6"
HAIKU_MODEL = "claude-haiku-4-5-20251001"

VALID_LEAD_STAGES = {"new", "contacted", "appointment_booked", "closed", "lost"}

# Batch limits for background jobs (prevent runaway queries)
BATCH_LIMIT = 50