"""Claim-gated data-plane tool entry.

``run_tool`` is the execute entry for L2 / ``requires_approval`` tools. It is
unreachable without a prior ``claim_for_execution``: a still-pending row never
reaches an injected provider. The approve HTTP path stays claim-then-run.

``send_email`` is Sales-only and gated by ``SEND_EMAIL_ENABLED`` (default
off). When the flag is off, or the agent is not Sales, this module refuses
before any mailbox port is used — including the production Gmail port.
Injected test ports still go through that refuse check.

Distinct from ``backend/services/os_actions/`` (deliverable channel
handlers) — the two stay dual, not merged.
"""

import html
import logging
import os
from dataclasses import dataclass
from email.header import decode_header, make_header
from email.utils import parseaddr
from typing import Any, Protocol

from backend.services import os_tool_executions as svc

logger = logging.getLogger(__name__)

SEND_EMAIL_FLAG = "SEND_EMAIL_ENABLED"
SEND_EMAIL_TOOL_ID = "send_email"
SALES_DEPARTMENT = "sales"

_TRUTHY = frozenset({"1", "true", "yes", "on"})


class MailboxPort(Protocol):
    def find_by_rfc822_msgid(self, msgid: str) -> str | None: ...

    def send(self, **kwargs) -> dict | None: ...

    def verify(
        self, message_id: str, *, to: str, subject: str, rfc822_msgid: str
    ) -> dict: ...


def _decoded_header(raw: str) -> str:
    try:
        return str(make_header(decode_header(raw or "")))
    except (LookupError, UnicodeError):
        return raw or ""


def _comparable_address(raw: str) -> str | None:
    address = parseaddr(raw or "")[1].strip()
    if "@" not in address:
        return None
    local, domain = address.rsplit("@", 1)
    if not local or not domain:
        return None
    return f"{local}@{domain.lower()}"


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
    if (agent_id or "") != SALES_DEPARTMENT:
        return "send_email is only available to the Sales department"
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
        body_html = f"<p>{html.escape(body)}</p>"
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
        if result.get("unknown"):
            return None
        return {
            "success": False,
            "refused": True,
            "detail": result.get("detail") or "Gmail refused the message",
        }

    def verify(
        self, message_id: str, *, to: str, subject: str, rfc822_msgid: str
    ) -> dict:
        from backend.services import gmail_connector

        message = gmail_connector.get_message(self.tenant_id, message_id)
        if message is None:
            return {
                "verified": False,
                "conclusive": False,
                "detail": "sent message could not be read back from Gmail",
            }
        expected_msgid = rfc822_msgid.strip().strip("<>")
        actual_msgid = (
            (message.get("headers") or {}).get("message-id") or ""
        ).strip().strip("<>")
        verified = (
            _comparable_address(message.get("recipient") or "")
            == _comparable_address(to)
            and _decoded_header(message.get("subject") or "").strip()
            == subject.strip()
            and actual_msgid == expected_msgid
        )
        return {
            "verified": verified,
            "conclusive": True,
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
