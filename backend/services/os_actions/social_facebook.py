"""Agent OS action handler: social.facebook.post.

Publishes a text-only feed post to the tenant's connected Facebook Page via
the Graph API. OAuth tokens live in the ``integrations`` table under
provider='facebook' (set up by ``backend/routers/channels_facebook.py``).

Required connectors: ``facebook``. If the tenant has no connected page the
run fails with a clear error_detail so the UI can prompt to connect.
"""

import json
import logging
import re
from typing import Any

import httpx

from backend.config import settings
from backend.models.database import get_service_supabase
from backend.services.llm_runtime import call_claude_messages
from backend.services.os_actions.base import ActionContext, ActionResult, ActionSpec

logger = logging.getLogger(__name__)

_FB_API_VERSION = getattr(settings, "facebook_api_version", "v21.0") or "v21.0"
_FB_GRAPH_BASE = f"https://graph.facebook.com/{_FB_API_VERSION}"

_EXTRACTION_SYSTEM = """\
You extract a Facebook post payload from an approved marketing message.
Return STRICT JSON with these keys:
- message (string, post body — plaintext, no HTML; <= 5000 chars)
- link (string or null, optional URL to attach)

If the deliverable has no postable text, return {"error": "no post body"}.\
"""


def _parse_json_block(text: str) -> dict | None:
    if not text:
        return None
    stripped = text.strip()
    if stripped.startswith("```"):
        match = re.search(r"```(?:json)?\s*(.+?)```", stripped, re.DOTALL)
        if match:
            stripped = match.group(1).strip()
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass
    return None


async def _extract_post(body: str, client_id: str) -> dict:
    response = await call_claude_messages(
        operation="os_action_facebook_extract",
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        system=_EXTRACTION_SYSTEM,
        messages=[{"role": "user", "content": f"Approved post draft:\n\n{body}"}],
        metadata={"client_id": client_id},
    )
    return _parse_json_block(response.text) or {}


def _load_fb_page(client_id: str) -> dict | None:
    """Return {'page_id', 'page_access_token'} or None if not connected."""
    db = get_service_supabase()
    row = (
        db.table("integrations")
        .select("access_token, metadata")
        .eq("tenant_id", client_id)
        .eq("provider", "facebook")
        .limit(1)
        .execute()
    )
    if not row.data:
        return None
    record = row.data[0]
    metadata = record.get("metadata") or {}
    page_id = metadata.get("page_id") if isinstance(metadata, dict) else None
    page_access_token = record.get("access_token")
    if not page_id or not page_access_token:
        return None
    return {"page_id": page_id, "page_access_token": page_access_token}


async def _run(ctx: ActionContext) -> ActionResult:
    body = (ctx.deliverable.get("body") or "").strip()
    if not body:
        return ActionResult(
            status="failed",
            error_detail={"message": "deliverable has empty body"},
        )

    try:
        payload = await _extract_post(body, ctx.client_id)
    except Exception as e:
        logger.warning(
            "os_action_facebook: extraction failed client_id=%s",
            ctx.client_id,
            exc_info=True,
        )
        return ActionResult(
            status="failed",
            error_detail={"stage": "extract", "message": str(e)[:300]},
        )

    if "error" in payload:
        return ActionResult(
            status="failed",
            error_detail={"stage": "extract", "message": payload["error"]},
        )

    message = (payload.get("message") or "").strip()
    link = (payload.get("link") or "").strip() or None
    if not message:
        return ActionResult(
            status="failed",
            request_payload=payload,
            error_detail={"stage": "validate", "message": "empty message"},
        )

    page = _load_fb_page(ctx.client_id)
    if not page:
        return ActionResult(
            status="failed",
            request_payload={"message": message, "link": link},
            error_detail={
                "stage": "connector",
                "message": "facebook page not connected for this tenant",
            },
        )

    request_payload = {"message": message[:5000], "link": link}
    api_body: dict[str, Any] = {
        "message": request_payload["message"],
        "access_token": page["page_access_token"],
    }
    if link:
        api_body["link"] = link

    url = f"{_FB_GRAPH_BASE}/{page['page_id']}/feed"

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, data=api_body)
    except Exception as e:
        logger.exception("os_action_facebook: HTTP error client_id=%s", ctx.client_id)
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={"stage": "fb_api", "message": str(e)[:300]},
        )

    if resp.status_code >= 400:
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={
                "stage": "fb_api",
                "status_code": resp.status_code,
                "message": resp.text[:500],
            },
        )

    response_body = resp.json() if resp.content else {}
    post_id = response_body.get("id")
    return ActionResult(
        status="succeeded",
        request_payload=request_payload,
        response_payload={"post_id": post_id, "raw": response_body},
    )


SPEC = ActionSpec(
    name="social.facebook.post",
    worker="campaign",
    run=_run,
    required_connectors=["facebook"],
    description="Publish a feed post to the tenant's connected Facebook Page.",
)
