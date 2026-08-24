"""Appointment booking via Claude Managed Agents.

Books or escalates an appointment request for a lead, using the
`appointment_booker` Managed Agent.  If the preferred window is empty the
agent cannot schedule and the result is `needs_human`.

No Twilio / SMS.  The confirmation_message is a plain stub string.

Mirrors the lead_qualification pattern line-for-line (same session
lifecycle, same stream loop, same error semantics).
"""

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel

from backend.models.database import get_service_supabase
from backend.services.managed_agents import (
    ManagedAgentsClient,
    ManagedAgentsError,
    SessionTerminalState,
    default_session_budget_cents,
)
from backend.services.managed_agents_registry import (
    ManagedAgentNotConfigured,
    ManagedAgentHandle,
    get_environment_id,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)


def _extract_appointment_id(reply: str) -> str | None:
    """Pull the appointment UUID out of the agent's reply, or None.

    Deliberately a regex over the whole reply rather than "take line 1": the
    agent is prompted to return a bare UUID, but a chatty reply ("Done! The
    id is <uuid>.") should still be usable, while a reply with no UUID at all
    must fail closed rather than becoming a fake reference.
    """
    match = _UUID_RE.search(reply or "")
    return match.group(0).lower() if match else None


def _appointment_row_exists(db: Any, appointment_id: str, tenant_id: str) -> bool:
    """True only when the appointment really exists AND belongs to this tenant.

    Fails CLOSED: any lookup error returns False, so an unverifiable booking is
    reported as `needs_human` rather than confirmed to a customer. That is the
    opposite of the fail-open posture used for non-critical guards
    (`widget_guard.py`) — here a false positive means a customer is told to
    expect a business that is not coming.

    `appointments` is keyed by `tenant_id`, while `leads`/`conversations` use
    `client_id` (`.claude/rules/schema-discipline.md`). The tenant-scope filter
    is what stops one tenant's agent confirming another tenant's appointment.
    """
    try:
        result = (
            db.table("appointments")
            .select("id")
            .eq("id", appointment_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.warning(
            "appointment_booker: lookup failed for appointment %s — treating as "
            "unverified",
            appointment_id,
            exc_info=True,
        )
        return False
    return bool(getattr(result, "data", None))


class AppointmentBookerInput(BaseModel):
    client_id: str
    lead_id: str
    service: str
    preferred_window: str
    notes: str = ""


class AppointmentBookerOutput(BaseModel):
    appointment_id: str | None
    confirmation_message: str
    status: Literal["booked", "needs_human", "error"]


# ---------------------------------------------------------------------------
# Registry handle
# ---------------------------------------------------------------------------


def _appointment_booker_handle() -> ManagedAgentHandle:
    """Resolve the agent handle from env, raising ManagedAgentNotConfigured
    when the env var is absent.  Reads directly from os.environ because
    the field is not in Settings (config.py is out of scope for this task).
    """
    agent_id = os.environ.get("APPOINTMENT_BOOKER_AGENT_ID", "")
    if not agent_id:
        raise ManagedAgentNotConfigured("APPOINTMENT_BOOKER_AGENT_ID")
    return ManagedAgentHandle(
        agent_id=agent_id,
        environment_id=get_environment_id(),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_booking_prompt(inp: AppointmentBookerInput, lead: dict[str, Any]) -> str:
    lines = ["Book an appointment for this lead:", ""]
    lines.append(f"- Lead name: {lead.get('name') or '(unknown)'}")
    lines.append(f"- Service requested: {inp.service}")
    lines.append(f"- Preferred window: {inp.preferred_window}")
    if inp.notes:
        lines.append(f"- Notes: {inp.notes}")
    if lead.get("phone"):
        lines.append(f"- Phone: {lead['phone']}")
    if lead.get("email"):
        lines.append(f"- Email: {lead['email']}")
    lines.append("")
    lines.append(
        "Confirm the appointment by returning ONLY the appointment_id UUID "
        "on a single line. If you cannot confirm, return exactly: NEEDS_HUMAN"
    )
    return "\n".join(lines)


def _extract_text_blocks(content: list[Any] | None) -> str:
    if not content:
        return ""
    parts: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)


def _run_booker_session(
    client: ManagedAgentsClient,
    *,
    agent_id: str,
    environment_id: str,
    prompt: str,
    tenant_id: str,
    lead_id: str,
) -> tuple[SessionTerminalState, str]:
    session = client.create_session(
        agent_id=agent_id,
        environment_id=environment_id,
        title=f"appointment-book {tenant_id}",
        metadata={
            "tenant_id": tenant_id,
            "lead_id": lead_id,
            "flow": "appointment_booking",
        },
        # Non-interactive path — cap the spend (no customer is waiting).
        budget_cents=default_session_budget_cents(),
    )
    session_id = session["id"]
    logger.info(
        "appointment_booker: session %s created for lead %s (tenant %s)",
        session_id,
        lead_id,
        tenant_id,
    )

    stream = client.stream_events(session_id)
    client.send_user_message(session_id, prompt)

    assistant_chunks: list[str] = []
    terminal = SessionTerminalState(
        terminated=False,
        stop_reason_type=None,
        last_event_id=None,
        session_id=session_id,
    )

    for event in stream:
        event_type = event.get("type", "")
        if event_type == "agent.message":
            assistant_chunks.append(_extract_text_blocks(event.get("content")))
        elif event_type == "session.status_terminated":
            terminal = SessionTerminalState(
                terminated=True,
                stop_reason_type=None,
                last_event_id=event.get("id"),
                session_id=session_id,
            )
            break
        elif event_type == "session.status_idle":
            stop_reason = event.get("stop_reason") or {}
            stop_type = (
                stop_reason.get("type") if isinstance(stop_reason, dict) else None
            )
            if stop_type != "requires_action":
                terminal = SessionTerminalState(
                    terminated=False,
                    stop_reason_type=stop_type,
                    last_event_id=event.get("id"),
                    session_id=session_id,
                )
                break

    return terminal, "\n".join(c for c in assistant_chunks if c)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class AppointmentBooker:
    """Book appointments via the Managed Agent.

    Usage:
        booker = AppointmentBooker()
        output = booker.run(inp)
    """

    def run(self, inp: AppointmentBookerInput) -> AppointmentBookerOutput:
        """Run the booking agent and return a structured result.

        Returns AppointmentBookerOutput with status:
            booked       — agent confirmed and an appointment row exists
            needs_human  — preferred_window empty or agent said NEEDS_HUMAN
            error        — unexpected failure (logged, not re-raised)
        """
        # Fast path: no window → escalate immediately, no API spend.
        if not inp.preferred_window or not inp.preferred_window.strip():
            logger.info(
                "appointment_booker: lead %s has empty preferred_window, needs_human",
                inp.lead_id,
            )
            return AppointmentBookerOutput(
                appointment_id=None,
                confirmation_message="No preferred window provided — human follow-up required.",
                status="needs_human",
            )

        db = get_service_supabase()

        # Load lead (uses client_id per schema-discipline).
        lead_res = (
            db.table("leads")
            .select("id, client_id, name, email, phone")
            .eq("id", inp.lead_id)
            .eq("client_id", inp.client_id)
            .limit(1)
            .execute()
        )
        if not lead_res.data:
            logger.warning(
                "appointment_booker: lead %s not found for client %s",
                inp.lead_id,
                inp.client_id,
            )
            return AppointmentBookerOutput(
                appointment_id=None,
                confirmation_message="Lead not found.",
                status="error",
            )
        lead = lead_res.data[0]
        client_id = lead.get("client_id") or inp.client_id

        # Resolve agent handle.
        try:
            handle = _appointment_booker_handle()
        except ManagedAgentNotConfigured as exc:
            logger.warning("appointment_booker: not configured (%s)", exc)
            raise RuntimeError(
                "APPOINTMENT_BOOKER_AGENT_ID env var not set. "
                "Run scripts/managed_agents/provision.py to provision the agent."
            ) from exc

        prompt = _build_booking_prompt(inp, lead)
        client = ManagedAgentsClient()

        try:
            _terminal, reply_text = _run_booker_session(
                client,
                agent_id=handle.agent_id,
                environment_id=handle.environment_id,
                prompt=prompt,
                tenant_id=client_id,  # client_id passed as session metadata tenant_id
                lead_id=inp.lead_id,
            )
        except ManagedAgentsError as exc:
            logger.warning(
                "appointment_booker: session failed for lead %s: %s (request_id=%s)",
                inp.lead_id,
                exc,
                exc.request_id,
            )
            return AppointmentBookerOutput(
                appointment_id=None,
                confirmation_message="Booking agent error — human follow-up required.",
                status="error",
            )

        reply_stripped = (reply_text or "").strip()

        if not reply_stripped or "NEEDS_HUMAN" in reply_stripped.upper():
            return AppointmentBookerOutput(
                appointment_id=None,
                confirmation_message="Agent could not confirm — human follow-up required.",
                status="needs_human",
            )

        # The agent should return a UUID appointment_id. Trusting it is not
        # enough: an agent that replies "I've booked you for Tuesday at 3pm"
        # used to have that sentence become the customer's confirmation
        # reference, flip the lead to `appointment_booked`, and be reported as
        # status="booked" — with no appointment row anywhere. The business
        # then does not show up. Verify against the table before telling a
        # customer anything is confirmed.
        appointment_id = _extract_appointment_id(reply_stripped)
        if appointment_id is None:
            logger.warning(
                "appointment_booker: lead %s — agent reply contained no appointment "
                "UUID, refusing to report a booking. reply_prefix=%r",
                inp.lead_id,
                reply_stripped[:120],
            )
            return AppointmentBookerOutput(
                appointment_id=None,
                confirmation_message="Agent could not confirm — human follow-up required.",
                status="needs_human",
            )

        # inp.client_id holds the tenant UUID — appointments.tenant_id stores the same value
        if not _appointment_row_exists(db, appointment_id, inp.client_id):
            logger.warning(
                "appointment_booker: lead %s — agent claimed appointment %s but no "
                "matching row exists for tenant %s, refusing to confirm.",
                inp.lead_id,
                appointment_id,
                inp.client_id,
            )
            return AppointmentBookerOutput(
                appointment_id=None,
                confirmation_message="Agent could not confirm — human follow-up required.",
                status="needs_human",
            )

        # Persist the booking reference against the lead (best-effort).
        try:
            db.table("leads").update(
                {
                    "status": "appointment_booked",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", inp.lead_id).execute()
        except Exception:
            logger.warning(
                "appointment_booker: failed to update lead %s status",
                inp.lead_id,
                exc_info=True,
            )

        # Surface the booking on the activity feed (best-effort, fail-open) so the
        # managed-agent booking shows up alongside widget/manual bookings (#119).
        from backend.services.activity import log_activity

        log_activity(
            tenant_id=inp.client_id,
            activity_type="appointment_booked",
            description="Appointment booked by the scheduling agent.",
            lead_id=inp.lead_id,
            metadata={"appointment_id": appointment_id, "source": "appointment_booker"},
        )

        logger.info(
            "appointment_booker: lead %s booked appointment %s",
            inp.lead_id,
            appointment_id,
        )
        return AppointmentBookerOutput(
            appointment_id=appointment_id,
            confirmation_message=f"Appointment confirmed. Reference: {appointment_id}",
            status="booked",
        )
