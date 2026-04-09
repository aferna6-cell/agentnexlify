"""AI document drafting via Claude Managed Agents.

Runs the `document_drafter` Managed Agent to produce real DOCX / XLSX /
PDF files for quotes, invoices, and proposals.

### Runtime contract

The agent writes the file inside its sandbox container (via the docx /
xlsx / pdf anthropic skills, which use bash + Node.js/Python to
generate the binary). Because the Managed Agents runtime does NOT
auto-upload `/mnt/session/outputs/` to the Files API, and there is no
`file_create` tool on the agent toolset, the agent's final reply
includes the file as a base64-encoded `content_base64` field:

    {
      "file_name":      "quote_smoke_test.docx",
      "file_type":      "docx" | "xlsx" | "pdf",
      "total":          450,
      "summary":        "...",
      "content_base64": "UEsDBAoAAAAA..."  # full file bytes
    }

This contract is documented in `config/managed_agents.yaml` in the
`document_drafter.system` prompt. Re-run `provision.py document_drafter`
after any change to the prompt.

### Persistence

The decoded bytes are stored inline in `documents.file_bytes` (bytea)
via migration 100. PostgreSQL bytea is sent as a backslash-x-hex
escape so PostgREST can pass it through untouched. The download
endpoint reads the bytes back, so there is no Files API round-trip on
retrieval.

This module is blocking (sync httpx under the hood). Call from a
FastAPI threadpool or BackgroundTask, never directly from an async
handler.
"""

import base64
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from backend.models.database import get_supabase
from backend.services.managed_agents import (
    ManagedAgentsClient,
    ManagedAgentsError,
    SessionTerminalState,
)
from backend.services.managed_agents_registry import (
    ManagedAgentNotConfigured,
    document_drafter,
)

logger = logging.getLogger(__name__)

# Plans allowed to spend on the document drafter. Same gate as
# lead_qualification — free tier explicitly excluded.
_ELIGIBLE_PLANS = frozenset({"growth", "professional", "autopilot", "enterprise"})

_VALID_KINDS = frozenset({"quote", "invoice", "proposal"})

# Extension → agent skill mapping. The agent picks which file to
# generate based on the prompt, but we validate the returned extension
# against this list before persisting.
_VALID_FILE_TYPES = frozenset({"docx", "xlsx", "pdf"})


class DocumentDraftingError(Exception):
    """Raised when drafting cannot run or its output is unusable."""


def _build_prompt(
    kind: str,
    tenant: dict[str, Any],
    customer: dict[str, Any],
    line_items: list[dict[str, Any]],
    notes: str | None,
) -> str:
    """Build the user message sent to the document_drafter agent.

    The agent's system prompt defines the full output contract
    (including `content_base64`). This function only needs to supply
    the data.
    """
    lines = [f"Draft a {kind}."]
    lines.append("")
    lines.append("Business:")
    lines.append(f"  - Name: {tenant.get('business_name') or '(unknown)'}")
    if tenant.get("business_phone"):
        lines.append(f"  - Phone: {tenant['business_phone']}")
    if tenant.get("business_address"):
        lines.append(f"  - Address: {tenant['business_address']}")
    lines.append("")
    lines.append("Customer:")
    lines.append(f"  - Name: {customer.get('name') or '(unknown)'}")
    if customer.get("email"):
        lines.append(f"  - Email: {customer['email']}")
    if customer.get("phone"):
        lines.append(f"  - Phone: {customer['phone']}")
    lines.append("")
    lines.append("Line items:")
    for i, item in enumerate(line_items, start=1):
        desc = item.get("description") or item.get("service") or f"Item {i}"
        qty = item.get("qty") or item.get("quantity") or 1
        unit = item.get("unit_price") or item.get("price") or 0
        lines.append(f"  {i}. {desc} — qty {qty} @ {unit}")
    if notes:
        lines.append("")
        lines.append(f"Notes: {notes}")
    lines.append("")
    lines.append(
        "Follow your system prompt exactly: generate the file via the "
        "appropriate skill, export with `base64 -w0`, and return only "
        "the JSON reply with file_name, file_type, total, summary, "
        "content_base64."
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


def _extract_json_from_reply(text: str) -> dict[str, Any] | None:
    """Pull the first JSON object from the agent's final reply."""
    text = text.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        try:
            parsed = json.loads(brace.group(0))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    return None


def _run_drafter_session(
    client: ManagedAgentsClient,
    *,
    agent_id: str,
    environment_id: str,
    prompt: str,
    tenant_id: str,
    lead_id: str | None,
    kind: str,
) -> tuple[SessionTerminalState, str, str | None]:
    """Run the document drafter session and return:
        (terminal_state, final_assistant_text, session_id)
    """
    session = client.create_session(
        agent_id=agent_id,
        environment_id=environment_id,
        title=f"draft-{kind} {tenant_id}",
        metadata={
            "tenant_id": tenant_id,
            "lead_id": lead_id or "",
            "kind": kind,
            "flow": "document_drafting",
        },
    )
    session_id = session["id"]
    logger.info(
        "document_drafting: session %s created (kind=%s tenant=%s lead=%s)",
        session_id, kind, tenant_id, lead_id,
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

    return terminal, "\n".join(c for c in assistant_chunks if c), session_id


def _safe_filename(name: str, default: str) -> str:
    """Strip any path components and normalize whitespace.

    The agent might return `/mnt/session/outputs/quote.pdf` — we only
    want the basename, and we want to reject anything that looks like
    directory traversal.
    """
    if not name:
        return default
    base = name.strip().split("/")[-1].split("\\")[-1]
    if not base or base in (".", ".."):
        return default
    # Replace characters that are ugly in downloads.
    cleaned = re.sub(r"[^A-Za-z0-9._\- ]+", "_", base).strip()
    return cleaned or default


def draft_document(
    *,
    tenant_id: str,
    lead_id: str | None,
    kind: str,
    customer: dict[str, Any],
    line_items: list[dict[str, Any]],
    notes: str | None = None,
) -> dict[str, Any]:
    """Draft a document via the document_drafter agent and persist it.

    Returns the persisted documents row. Raises DocumentDraftingError on
    any terminal failure (bad kind, plan gate, agent failure, parse).
    """
    if kind not in _VALID_KINDS:
        raise DocumentDraftingError(
            f"invalid kind {kind!r}, must be one of {sorted(_VALID_KINDS)}"
        )
    if not line_items:
        raise DocumentDraftingError("line_items must not be empty")

    db = get_supabase()

    # 1. Load + plan-gate tenant
    tenant_res = (
        db.table("tenants")
        .select("id, business_name, business_phone, business_address, plan")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not tenant_res.data:
        raise DocumentDraftingError(f"tenant {tenant_id} not found")
    tenant = tenant_res.data[0]

    plan = (tenant.get("plan") or "free").lower()
    if plan not in _ELIGIBLE_PLANS:
        raise DocumentDraftingError(
            f"plan {plan!r} is not eligible for document drafting"
        )

    # 2. Get agent handle
    try:
        handle = document_drafter()
    except ManagedAgentNotConfigured as exc:
        raise DocumentDraftingError(str(exc)) from exc

    # 3. Run the session
    prompt = _build_prompt(kind, tenant, customer, line_items, notes)
    client = ManagedAgentsClient()

    try:
        terminal, reply_text, session_id = _run_drafter_session(
            client,
            agent_id=handle.agent_id,
            environment_id=handle.environment_id,
            prompt=prompt,
            tenant_id=tenant_id,
            lead_id=lead_id,
            kind=kind,
        )
    except ManagedAgentsError as exc:
        raise DocumentDraftingError(
            f"drafter session failed: {exc}"
        ) from exc

    if not reply_text:
        raise DocumentDraftingError(
            f"drafter produced no assistant messages "
            f"(terminated={terminal.terminated} stop={terminal.stop_reason_type})"
        )

    # 4. Parse the JSON spec from the final reply
    spec = _extract_json_from_reply(reply_text)
    if not spec:
        raise DocumentDraftingError(
            "drafter reply did not contain parseable JSON"
        )

    file_type = (spec.get("file_type") or "").lower().strip()
    if file_type not in _VALID_FILE_TYPES:
        raise DocumentDraftingError(
            f"drafter reply has invalid file_type {file_type!r}"
        )

    b64 = spec.get("content_base64")
    if not isinstance(b64, str) or not b64.strip():
        raise DocumentDraftingError(
            "drafter reply missing content_base64 (agent must base64-encode the file)"
        )

    # Strip any whitespace the agent may have introduced despite the
    # `base64 -w0` instruction — we've seen it wrap lines occasionally.
    b64 = re.sub(r"\s+", "", b64)

    try:
        file_bytes = base64.b64decode(b64, validate=True)
    except Exception as exc:
        raise DocumentDraftingError(
            f"content_base64 failed to decode: {exc}"
        ) from exc

    if not file_bytes:
        raise DocumentDraftingError("decoded file_bytes is empty")

    # Magic-byte sanity check — the agent is supposed to produce a real
    # DOCX/XLSX/PDF, not a text blob. DOCX/XLSX are ZIP archives
    # (PK\x03\x04); PDF starts with %PDF-.
    if file_type in ("docx", "xlsx"):
        if not file_bytes.startswith(b"PK\x03\x04"):
            raise DocumentDraftingError(
                f"decoded bytes do not look like a {file_type} (missing PK header)"
            )
    elif file_type == "pdf":
        if not file_bytes.startswith(b"%PDF-"):
            raise DocumentDraftingError(
                "decoded bytes do not look like a PDF (missing %PDF- magic)"
            )

    file_size = len(file_bytes)
    default_name = f"{kind}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}.{file_type}"
    file_name = _safe_filename(spec.get("file_name") or "", default_name)

    # 5. Persist the document row. `file_bytes` is stored inline as a
    #    PostgreSQL bytea hex escape (`\x<hex>`) so PostgREST can pass
    #    it through as-is. Redact content_base64 from the stored spec
    #    so we don't double up on storage.
    spec_for_metadata = {k: v for k, v in spec.items() if k != "content_base64"}

    row: dict[str, Any] = {
        "tenant_id": tenant_id,
        "title": (
            f"{kind.title()} for {customer.get('name') or 'customer'} "
            f"({datetime.now(timezone.utc).strftime('%Y-%m-%d')})"
        ),
        "status": "draft",
        "kind": kind,
        "file_type": file_type,
        "file_name": file_name,
        "file_bytes": "\\x" + file_bytes.hex(),
        "generated_by_agent": "document_drafter",
        "draft_metadata": {
            "session_id": session_id,
            "spec": spec_for_metadata,
            "customer": customer,
            "line_items": line_items,
            "notes": notes,
            "file_size_bytes": file_size,
        },
    }
    if lead_id:
        row["lead_id"] = lead_id
    if customer.get("name"):
        row["signer_name"] = customer["name"]
    if customer.get("email"):
        row["signer_email"] = customer["email"]

    insert_res = db.table("documents").insert(row).execute()
    if not insert_res.data:
        raise DocumentDraftingError("documents.insert returned no data")

    persisted = insert_res.data[0]
    logger.info(
        "document_drafting: persisted %s (%d bytes, type=%s) as document %s",
        kind, file_size, file_type, persisted.get("id"),
    )
    return persisted
