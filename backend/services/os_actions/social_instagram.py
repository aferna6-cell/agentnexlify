"""Agent OS action handler: social.instagram.post.

Publishes an image post to the tenant's connected Instagram business
account via the Graph API (two-step: create media container, then publish).
OAuth tokens live in the ``integrations`` table under provider='instagram'
(or under 'facebook' with an instagram_business_account_id in metadata —
both shapes supported).

Required connectors: ``instagram``. If the tenant has no IG business
account linked, the run fails with a clear error_detail.
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
You extract an Instagram post payload from an approved marketing message.
Return STRICT JSON with these keys:
- caption (string, IG caption — plaintext, no HTML; <= 2200 chars)
- image_url (string, public HTTPS URL to the image to post)

If the deliverable has no image URL, return {"error": "missing image_url"}.\
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
        operation="os_action_instagram_extract",
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        system=_EXTRACTION_SYSTEM,
        messages=[{"role": "user", "content": f"Approved post draft:\n\n{body}"}],
        metadata={"client_id": client_id},
    )
    return _parse_json_block(response.text) or {}


def _load_ig_account(client_id: str) -> dict | None:
    """Return {'ig_user_id', 'access_token'} or None if not connected.

    Looks up either provider='instagram' OR provider='facebook' with
    instagram_business_account_id in metadata.
    """
    db = get_service_supabase()
    ig_row = (
        db.table("integrations")
        .select("access_token, metadata")
        .eq("tenant_id", client_id)
        .eq("provider", "instagram")
        .limit(1)
        .execute()
    )
    if ig_row.data:
        record = ig_row.data[0]
        metadata = record.get("metadata") if isinstance(record, dict) else None
        if not isinstance(metadata, dict):
            metadata = {}
        ig_user_id = metadata.get("ig_user_id") or metadata.get(
            "instagram_business_account_id"
        )
        access_token = record.get("access_token")
        if ig_user_id and access_token:
            return {"ig_user_id": ig_user_id, "access_token": access_token}

    fb_row = (
        db.table("integrations")
        .select("access_token, metadata")
        .eq("tenant_id", client_id)
        .eq("provider", "facebook")
        .limit(1)
        .execute()
    )
    if not fb_row.data:
        return None
    record = fb_row.data[0]
    metadata = record.get("metadata") if isinstance(record, dict) else None
    if not isinstance(metadata, dict):
        metadata = {}
    ig_user_id = metadata.get("instagram_business_account_id")
    access_token = record.get("access_token")
    if ig_user_id and access_token:
        return {"ig_user_id": ig_user_id, "access_token": access_token}
    return None


async def _create_container(
    client: httpx.AsyncClient,
    ig_user_id: str,
    access_token: str,
    image_url: str,
    caption: str,
) -> tuple[str | None, dict]:
    url = f"{_FB_GRAPH_BASE}/{ig_user_id}/media"
    resp = await client.post(
        url,
        data={
            "image_url": image_url,
            "caption": caption,
            "access_token": access_token,
        },
    )
    body = resp.json() if resp.content else {}
    if resp.status_code >= 400:
        return None, {
            "stage": "ig_create_container",
            "status_code": resp.status_code,
            "message": resp.text[:500],
        }
    return body.get("id"), body


async def _publish_container(
    client: httpx.AsyncClient,
    ig_user_id: str,
    access_token: str,
    creation_id: str,
) -> tuple[str | None, dict]:
    url = f"{_FB_GRAPH_BASE}/{ig_user_id}/media_publish"
    resp = await client.post(
        url,
        data={"creation_id": creation_id, "access_token": access_token},
    )
    body = resp.json() if resp.content else {}
    if resp.status_code >= 400:
        return None, {
            "stage": "ig_publish",
            "status_code": resp.status_code,
            "message": resp.text[:500],
        }
    return body.get("id"), body


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
            "os_action_instagram: extraction failed client_id=%s",
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

    caption = (payload.get("caption") or "").strip()
    image_url = (payload.get("image_url") or "").strip()
    if not image_url.startswith("https://"):
        return ActionResult(
            status="failed",
            request_payload=payload,
            error_detail={"stage": "validate", "message": "image_url must be HTTPS"},
        )

    account = _load_ig_account(ctx.client_id)
    if not account:
        return ActionResult(
            status="failed",
            request_payload={"caption": caption, "image_url": image_url},
            error_detail={
                "stage": "connector",
                "message": "instagram business account not connected for this tenant",
            },
        )

    request_payload: dict[str, Any] = {
        "caption": caption[:2200],
        "image_url": image_url,
        "ig_user_id": account["ig_user_id"],
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            creation_id, create_body = await _create_container(
                client,
                account["ig_user_id"],
                account["access_token"],
                image_url,
                request_payload["caption"],
            )
            if not creation_id:
                return ActionResult(
                    status="failed",
                    request_payload=request_payload,
                    error_detail=create_body,
                )
            media_id, publish_body = await _publish_container(
                client,
                account["ig_user_id"],
                account["access_token"],
                creation_id,
            )
    except Exception as e:
        logger.exception("os_action_instagram: HTTP error client_id=%s", ctx.client_id)
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={"stage": "ig_api", "message": str(e)[:300]},
        )

    if not media_id:
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail=publish_body,
        )

    return ActionResult(
        status="succeeded",
        request_payload=request_payload,
        response_payload={"media_id": media_id, "creation_id": creation_id},
    )


SPEC = ActionSpec(
    name="social.instagram.post",
    worker="campaign",
    run=_run,
    required_connectors=["instagram"],
    description="Publish an image post to the tenant's connected Instagram business account.",
)
