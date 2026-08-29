"""Claim-gated data-plane tool entry.

``run_tool`` is the execute entry for L2 / ``requires_approval`` tools. It is
unreachable without a prior ``claim_for_execution``: a still-pending row never
reaches an injected provider. The approve HTTP path stays claim-then-run.

This is not a production Gmail send path. There is no default that calls
``gmail_connector.send_message`` or ``email_sender.send_email``. A mailbox
port must be injected. Distinct from ``backend/services/os_actions/`` (deliverable
channel handlers) — the two stay dual, not merged.
"""

from dataclasses import dataclass
from typing import Any, Protocol

from backend.services import os_tool_executions as svc


class MailboxPort(Protocol):
    def find_by_rfc822_msgid(self, msgid: str) -> str | None: ...

    def send(self, **kwargs) -> dict | None: ...


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


def _run_data_plane_tool(
    db: Any, client_id: str, execution_id: str, port: Any
) -> dict:
    """Delegate to the data-plane runner. Unknown send stays non-terminal."""
    return svc._run_data_plane_tool(db, client_id, execution_id, port)


async def run_tool(ctx: ToolContext) -> dict:
    """Execute a claimed row only. Unclaimed L2 tools never reach the provider."""
    return _run_data_plane_tool(ctx.db, ctx.client_id, ctx.execution_id, ctx.port)
