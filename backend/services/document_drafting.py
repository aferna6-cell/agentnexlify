"""AI document drafting via Claude Managed Agents.

Runs the `document_drafter` Managed Agent to produce real DOCX / XLSX /
PDF files for quotes, invoices, and proposals. The agent writes the
file to `/mnt/session/outputs/` inside its sandbox container; this
service downloads the bytes via the Anthropic Files API (beta:
files-api-2025-04-14) and persists them inline on the existing
`documents` table.

Why inline bytea instead of Supabase storage?
  - Drafted documents are small (<1 MB typical).
  - RLS / tenant isolation is already trivial on the documents table.
  - No new bucket provisioning required.
  - Can migrate to storage buckets later if file sizes grow.

This is a blocking path — the Managed Agents client is sync httpx.
Call from a FastAPI threadpool or BackgroundTask, never directly from
an async handler.
"""

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
    """Build the user message sent to the document_drafter agent."""
    lines = [f"Draft a {kind} as a real file (DOCX for quotes/proposals, XLSX for invoices)."]
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
        "Save the file to `/mnt/session/outputs/` with a descriptive name. "
        "In your final reply, return a JSON block with keys: "
        "`file_id` (the Anthropic Files API id of the saved file), "
        "`file_name` (the basename of the file you wrote), "
        "`file_type` (one of 'docx', 'xlsx', 'pdf'), "
        "`total` (the grand total as a number), "
        "`summary` (one sentence describing what you produced)."
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
        terminated=False, stop_reason_type=None, last_event_id=None,
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

    file_id = spec.get("file_id")
    if not isinstance(file_id, str) or not file_id.strip():
        raise DocumentDraftingError(
            f"drafter reply missing file_id (spec={spec!r})"
        )

    file_type = (spec.get("file_type") or "").lower().strip()
    if file_type not in _VALID_FILE_TYPES:
        raise DocumentDraftingError(
            f"drafter reply has invalid file_type {file_type!r}"
        )

    default_name = f"{kind}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}.{file_type}"
    file_name = _safe_filename(spec.get("file_name") or "", default_name)

    # 5. Verify the file actually exists + get size (cheap metadata call
    #    before we commit to a DB row). Full bytes are fetched lazily by
    #    the download endpoint; keeping bytea empty for V1 sidesteps
    #    PostgREST bytea-encoding footguns and lets us upgrade to inline
    #    storage or Supabase storage buckets later without migrating data.
    try:
        metadata = client.get_file_metadata(file_id)
    except ManagedAgentsError as exc:
        raise DocumentDraftingError(
            f"failed to look up file {file_id}: {exc}"
        ) from exc

    file_size = metadata.get("size_bytes") if isinstance(metadata, dict) else None

    # 6. Persist the document row. `file_bytes` stays NULL in V1 — the
    #    download endpoint streams fresh from Anthropic on demand. If
    #    Anthropic's session-file retention proves too short, V2 will
    #    cache bytes inline or in Supabase storage.
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
        "anthropic_file_id": file_id,
        "generated_by_agent": "document_drafter",
        "draft_metadata": {
            "session_id": session_id,
            "spec": spec,
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
        "document_drafting: persisted %s (size=%s bytes, type=%s) as document %s",
        kind, file_size, file_type, persisted.get("id"),
    )
    return persisted
