"""Agent OS tool: ``send_email`` — the first real external action.

Level 2 (external communication): an agent may PREPARE this, and only an
explicit owner approval can send it. By the time ``_execute`` runs, the
approval endpoint has already claimed the durable ``os_tool_executions`` row
with a conditional update, so exactly one approval reached here.

Provider: the tenant's own connected Gmail, through the existing
``backend.services.gmail_connector`` (same OAuth rows, same encrypted token
vault, same transport as the inbox-triage reply path). Gmail specifically,
rather than the ``email.send`` deliverable action's m365/Resend dispatch,
because Gmail is the provider that can answer the two questions this milestone
is about:

  "did this already send?"  -> rfc822msgid: search on a Message-ID we set
  "did it really land?"     -> fetch the sent message back and compare it

Neither Resend nor the M365 Graph path exposes those, so this tool refuses to
run without Gmail rather than silently degrading to a provider whose outcome
it cannot check. The existing ``email.send`` action still covers those
providers for approved deliverables.

Idempotency, exactly as implemented (no stronger claim):
  1. The approval claim is a conditional UPDATE out of ``pending_approval``.
     Double-clicks and retried requests lose the race and never reach here.
  2. Every message carries ``Message-ID: <aos-<execution_id>@...>``, derived
     from the execution row's id — stable across retries of the same action,
     unique across different ones.
  3. Before sending, we ask Gmail whether a message with that Message-ID
     already exists. If it does, we do not send again; we adopt it.
  4. If the send's outcome is unknown (transport failure, timeout), the row is
     left non-terminal and is NOT retried automatically. A later re-drive hits
     check 3 first.

The residual window is real and small: Gmail can accept a message and the
response can be lost before we record it. Check 3 closes that on the next
attempt, but between the two, our record says "unknown", not "sent". This is
at-most-once with a resolvable unknown, not exactly-once.
"""

import logging
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

from backend.services import gmail_connector
from backend.services.os_actions.email import _body_to_html
from backend.services.os_actions.recipients import normalize_email
from backend.services.os_tools.base import (
    ToolContext,
    ToolOutcome,
    ToolSpec,
    VerificationOutcome,
)

logger = logging.getLogger(__name__)

TOOL_ID = "send_email"

#: Domain for the Message-ID we stamp on outgoing mail. Not a real host — it
#: only has to be stable and unique, which is what RFC 5322 asks of the
#: right-hand side.
_MSGID_DOMAIN = "actions.agentnexlify"

_SUBJECT_MAX = 200
_BODY_MAX = 20000


class SendEmailInput(BaseModel):
    """Mirrors the engine's Zod schema for ``send_email``.

    Single recipient by design for the first release: one address is what the
    owner can meaningfully eyeball in an approval prompt, and it keeps the
    blast radius of a mistaken approval to one person.
    """

    to: str = Field(..., max_length=254)
    subject: str = Field(..., min_length=1, max_length=_SUBJECT_MAX)
    body: str = Field(..., min_length=1, max_length=_BODY_MAX)
    # Optional threading, when the agent is continuing an existing Gmail
    # conversation the tenant already has.
    thread_id: str | None = Field(default=None, max_length=200)
    in_reply_to: str | None = Field(default=None, max_length=500)

    @field_validator("to")
    @classmethod
    def _valid_recipient(cls, value: str) -> str:
        normalized = normalize_email(value)
        if not normalized:
            raise ValueError("recipient is not a valid email address")
        return normalized

    @field_validator("subject", "body")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()


def rfc822_msgid_for(execution_id: str) -> str:
    """The Message-ID this execution's mail carries.

    Derived purely from the execution id so it is identical across every
    attempt at the same action and different for every other one — that is
    what makes the pre-send duplicate check meaningful.
    """
    safe = re.sub(r"[^A-Za-z0-9_.-]", "", str(execution_id))
    return f"aos-{safe}@{_MSGID_DOMAIN}"


def _connector_error(message: str) -> ToolOutcome:
    return ToolOutcome(
        status="failed",
        error={"code": "connector_unavailable", "message": message},
    )


async def _execute(ctx: ToolContext) -> ToolOutcome:
    payload = ctx.input
    to = payload["to"]
    subject = payload["subject"]
    body = payload["body"]

    # No connected mailbox: fail closed, and say so in words the owner can act
    # on. Never fall back to another provider — the owner approved sending
    # from their own mailbox.
    try:
        connected = gmail_connector.is_connected(ctx.client_id)
    except Exception as e:
        logger.warning(
            "send_email: connector lookup failed client_id=%s", ctx.client_id, exc_info=True
        )
        return _connector_error(f"could not check the Gmail connection: {str(e)[:200]}")
    if not connected:
        return _connector_error(
            "Gmail is not connected for this business, so nothing was sent. "
            "Connect Gmail under Integrations and approve this again."
        )

    msgid = rfc822_msgid_for(ctx.execution_id)

    # Pre-send duplicate check (idempotency step 3). A hit means this exact
    # action already sent — adopt that message instead of sending a second.
    try:
        existing = gmail_connector.find_message_id_by_rfc822_msgid(ctx.client_id, msgid)
    except Exception:
        logger.warning(
            "send_email: duplicate check failed client_id=%s", ctx.client_id, exc_info=True
        )
        existing = None
    if existing:
        logger.info(
            "send_email: duplicate suppressed client_id=%s execution_id=%s message_id=%s",
            ctx.client_id,
            ctx.execution_id,
            existing,
        )
        return ToolOutcome(
            status="succeeded",
            result={
                "provider": "gmail",
                "messageId": existing,
                "to": to,
                "subject": subject,
                "rfc822MsgId": msgid,
                "deduplicated": True,
                "detail": "this message was already in the mailbox; it was not sent again",
            },
            effect={"port": "gmail", "durable": True},
        )

    try:
        sent = gmail_connector.send_message(
            ctx.db,
            ctx.client_id,
            to=to,
            subject=subject,
            body_html=_body_to_html(body),
            rfc822_msgid=msgid,
            thread_id=payload.get("thread_id") or None,
            in_reply_to=payload.get("in_reply_to") or None,
        )
    except Exception as e:
        logger.exception("send_email: gmail send raised client_id=%s", ctx.client_id)
        # The outcome is unknown, not "not sent". Say exactly that.
        return ToolOutcome(
            status="failed",
            error={
                "code": "send_outcome_unknown",
                "message": (
                    f"the Gmail send raised before a response was seen ({str(e)[:200]}); "
                    "whether the message left the mailbox is unknown"
                ),
                "rfc822MsgId": msgid,
            },
            effect={"port": "gmail", "durable": True},
        )

    if not sent.get("success"):
        detail = str(sent.get("detail") or "the send reported failure")
        status_code = sent.get("status_code")
        # A 4xx from Gmail is a definite non-send (auth expired, bad address).
        # Anything else could have been accepted before the response was lost.
        definite = isinstance(status_code, int) and 400 <= status_code < 500
        return ToolOutcome(
            status="failed",
            error={
                "code": "send_rejected" if definite else "send_outcome_unknown",
                "message": detail
                if definite
                else f"{detail}; whether the message left the mailbox is unknown",
                "rfc822MsgId": msgid,
                **({"statusCode": status_code} if status_code is not None else {}),
            },
            effect={"port": "gmail", "durable": True},
        )

    return ToolOutcome(
        status="succeeded",
        result={
            "provider": "gmail",
            "messageId": sent.get("message_id", ""),
            "threadId": sent.get("thread_id", ""),
            "to": to,
            "subject": subject,
            "rfc822MsgId": msgid,
            "deduplicated": False,
            "detail": "accepted by Gmail",
        },
        effect={"port": "gmail", "durable": True},
    )


async def _verify(ctx: ToolContext, outcome: ToolOutcome) -> VerificationOutcome:
    """Independently confirm the message exists in the mailbox.

    Not "the API returned 200" — we fetch the message back by the id Gmail gave
    us and compare the recipient and subject we intended against what the
    mailbox actually holds. A mismatch or a missing message is a verification
    failure even though the send reported success, which is exactly the case
    the two-axis model exists to represent.
    """
    result = outcome.result or {}
    message_id = result.get("messageId")
    if not message_id:
        return VerificationOutcome(
            state="failed", detail="the send returned no message id to check"
        )

    try:
        message: Any = gmail_connector.get_message(ctx.client_id, message_id)
    except Exception as e:
        return VerificationOutcome(
            state="failed",
            detail=f"the sent message could not be read back: {str(e)[:200]}",
        )

    if not message:
        return VerificationOutcome(
            state="failed",
            detail=(
                f"Gmail accepted the send but message {message_id} could not be read "
                "back, so delivery is unconfirmed"
            ),
        )

    intended_to = (result.get("to") or "").strip().lower()
    actual_to = (message.get("recipient") or "").strip().lower()
    if intended_to and intended_to not in actual_to:
        return VerificationOutcome(
            state="failed",
            detail=(
                "the message in the mailbox is addressed to someone other than the "
                "approved recipient"
            ),
        )

    intended_subject = (result.get("subject") or "").strip()
    actual_subject = (message.get("subject") or "").strip()
    if intended_subject and intended_subject != actual_subject:
        return VerificationOutcome(
            state="failed",
            detail="the message in the mailbox does not carry the approved subject",
        )

    return VerificationOutcome(
        state="passed",
        detail=(
            f"message {message_id} confirmed in the mailbox, addressed to the approved "
            "recipient with the approved subject"
        ),
    )


SPEC = ToolSpec(
    tool_id=TOOL_ID,
    risk_level=2,
    mutating=True,
    requires_approval=True,
    input_model=SendEmailInput,
    execute=_execute,
    verify=_verify,
    required_connectors=["gmail"],
    description=(
        "Send an email from the business's own connected Gmail mailbox. "
        "External communication: always requires explicit owner approval."
    ),
)
