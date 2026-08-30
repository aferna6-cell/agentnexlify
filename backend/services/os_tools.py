"""Claim-gated data-plane tool entry.

``run_tool`` is the execute entry for L2 / ``requires_approval`` tools. It is
unreachable without a prior ``claim_for_execution``: a still-pending row never
reaches an injected provider. The approve HTTP path stays claim-then-run.

``send_email`` is capability-gated and controlled by ``SEND_EMAIL_ENABLED``
(default off). When the flag is off, or the proposing department lacks the
explicit capability, this module refuses before any mailbox port is used.
Injected test ports still go through that refuse check.

Distinct from ``backend/services/os_actions/`` (deliverable channel
handlers) — the two stay dual, not merged.
"""

import html
import logging
import os
from dataclasses import dataclass
from typing import Any, Protocol

from backend.services import os_tool_executions as svc

logger = logging.getLogger(__name__)

SEND_EMAIL_FLAG = "SEND_EMAIL_ENABLED"
SEND_EMAIL_TOOL_ID = "send_email"
SEND_EMAIL_CAPABLE_DEPARTMENTS = frozenset(
    {"sales", "marketing", "customer_service", "operations", "invoicing"}
)

_TRUTHY = frozenset({"1", "true", "yes", "on"})


class MailboxPort(Protocol):
    def find_by_rfc822_msgid(self, msgid: str) -> str | None: ...

    def send(self, **kwargs) -> dict | None: ...

    def verify(
        self, message_id: str, *, to: str, subject: str, rfc822_msgid: str
    ) -> dict: ...


@dataclass
class ToolContext:
    db: Any
    client_id: str
    execution_id: str
    tool_id: str
    input: dict
    agent_id: str | None = None
    approved_by: str | None = None
    port: Any = None


def send_email_enabled() -> bool:
    """Live send gate. Unset / empty / anything but 1/true/yes/on is off."""
    return os.environ.get(SEND_EMAIL_FLAG, "0").strip().lower() in _TRUTHY


def refuse_send_email(*, agent_id: str | None, tool_id: str | None = None) -> str | None:
    """Fail-closed reason to block a send, or None when it may proceed.

    Callers still have to have claimed the row. This never sends.
    """
    if tool_id not in (None, SEND_EMAIL_TOOL_ID):
        return None
    if not send_email_enabled():
        return "send_email is disabled (SEND_EMAIL_ENABLED defaults off)"
    if (agent_id or "") not in SEND_EMAIL_CAPABLE_DEPARTMENTS:
        return "this department is not permitted to propose send_email"
    return None


class GmailMailboxPort:
    """Production mailbox: Gmail connector send + rfc822msgid adopt."""

    def __init__(self, tenant_id: str, db: Any = None):
        self.tenant_id = tenant_id
        self.db = db

    def find_by_rfc822_msgid(self, msgid: str) -> str | None:
        from backend.services import gmail_connector

        return gmail_connector.find_message_id_by_rfc822_msgid(
            self.tenant_id, msgid, strict=True
        )

    def send(self, **kwargs) -> dict | None:
        from backend.services import gmail_connector

        body = kwargs.get("body") or ""
        body_html = body if "<" in body else f"<p>{html.escape(body)}</p>"
        result = gmail_connector.send_message(
            self.db,
            self.tenant_id,
            to=kwargs.get("to") or "",
            subject=kwargs.get("subject") or "",
            body_html=body_html,
            rfc822_msgid=kwargs.get("rfc822_msgid"),
            thread_id=kwargs.get("thread_id"),
            in_reply_to=kwargs.get("in_reply_to"),
        )
        if result.get("success"):
            return {"success": True, "message_id": result.get("message_id", "")}
        return None

    def verify(
        self, message_id: str, *, to: str, subject: str, rfc822_msgid: str
    ) -> dict:
        from backend.services import gmail_connector

        message = gmail_connector.get_message(self.tenant_id, message_id)
        if message is None:
            return {"verified": False, "detail": "sent message was not found in Gmail"}
        expected_to = svc._normalize_email(to)
        actual_to = svc._normalize_email(message.get("recipient"))
        expected_msgid = rfc822_msgid.strip().strip("<>")
        actual_msgid = (
            (message.get("headers") or {}).get("message-id") or ""
        ).strip().strip("<>")
        verified = (
            expected_to is not None
            and actual_to == expected_to
            and (message.get("subject") or "").strip() == subject.strip()
            and actual_msgid == expected_msgid
        )
        return {
            "verified": verified,
            "detail": (
                "recipient, subject, and Message-ID match"
                if verified
                else "recipient, subject, or Message-ID mismatch"
            ),
        }


def _run_data_plane_tool(
    db: Any, client_id: str, execution_id: str, port: Any
) -> dict:
    """Delegate to the data-plane runner. Unknown send stays non-terminal."""
    return svc._run_data_plane_tool(db, client_id, execution_id, port)


def production_send_email_port(client_id: str, db: Any) -> GmailMailboxPort:
    return GmailMailboxPort(client_id, db)


async def run_tool(ctx: ToolContext) -> dict:
    """Execute a claimed row only. Unclaimed L2 tools never reach the provider.

    ``send_email`` is refused when the flag is off or the agent is not Sales.
    A production Gmail port is attached only after that check, and only when
    the caller did not inject a mailbox.
    """
    if ctx.tool_id == SEND_EMAIL_TOOL_ID:
        reason = refuse_send_email(agent_id=ctx.agent_id, tool_id=ctx.tool_id)
        if reason:
            logger.info(
                "os_tools: send_email refused client_id=%s execution_id=%s reason=%s",
                ctx.client_id,
                ctx.execution_id,
                reason,
            )
            return {
                "executed": False,
                "adopted": False,
                "unknown": False,
                "refused": True,
                "reason": reason,
            }
        if ctx.port is None:
            ctx.port = production_send_email_port(ctx.client_id, ctx.db)
    return _run_data_plane_tool(ctx.db, ctx.client_id, ctx.execution_id, ctx.port)
