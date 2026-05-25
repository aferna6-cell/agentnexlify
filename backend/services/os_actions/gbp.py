"""Agent OS action handler: gbp.post.

Posts a local update to the tenant's Google Business Profile. OAuth tokens
live in the ``integrations`` table under provider='google_business_profile'
(set up by ``backend/routers/gbp.py``). Requires the tenant to have a
``location_id`` stored in metadata — without it the run fails with a clear
prompt to complete GBP location setup.

Required connectors: ``google_business_profile``.
"""

import json
import logging
import re

import httpx

from backend.models.database import get_service_supabase
from backend.services.llm_runtime import call_claude_messages
from backend.services.os_actions.base import ActionContext, ActionResult, ActionSpec

logger = logging.getLogger(__name__)

_GBP_BASE = "https://mybusiness.googleapis.com/v4"

_EXTRACTION_SYSTEM = """\
You extract a Google Business Profile update payload from an approved
marketing message. Return STRICT JSON with these keys:
- summary (string, post body, <= 1500 chars, plaintext)
- topic_type (one of: STANDARD, EVENT, OFFER — default STANDARD)
- call_to_action_url (string or null)

If no usable post body, return {"error": "empty body"}.\
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
        operation="os_action_gbp_extract",
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        system=_EXTRACTION_SYSTEM,
        messages=[{"role": "user", "content": f"Approved post draft:\n\n{body}"}],
        metadata={"client_id": client_id},
    )
    return _parse_json_block(response.text) or {}


def _load_gbp(client_id: str) -> dict | None:
    """Return {'access_token', 'account_id', 'location_id'} or None."""
    db = get_service_supabase()
    row = (
        db.table("integrations")
        .select("access_token, metadata")
        .eq("tenant_id", client_id)
        .eq("provider", "google_business_profile")
        .limit(1)
        .execute()
    )
    if not row.data:
        return None
    record = row.data[0]
    metadata = record.get("metadata") if isinstance(record, dict) else None
    if not isinstance(metadata, dict):
        metadata = {}
    location_id = metadata.get("location_id")
    account_id = metadata.get("account_id")
    access_token = record.get("access_token")
    if not (location_id and account_id and access_token):
        return None
    return {
        "access_token": access_token,
        "account_id": account_id,
        "location_id": location_id,
    }


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
            "os_action_gbp: extraction failed client_id=%s",
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

    summary = (payload.get("summary") or "").strip()
    topic_type = (payload.get("topic_type") or "STANDARD").upper()
    cta_url = (payload.get("call_to_action_url") or "").strip() or None

    if topic_type not in {"STANDARD", "EVENT", "OFFER"}:
        topic_type = "STANDARD"
    if not summary:
        return ActionResult(
            status="failed",
            request_payload=payload,
            error_detail={"stage": "validate", "message": "empty summary"},
        )

    creds = _load_gbp(ctx.client_id)
    if not creds:
        return ActionResult(
            status="failed",
            request_payload={
                "summary": summary,
                "topic_type": topic_type,
                "cta_url": cta_url,
            },
            error_detail={
                "stage": "connector",
                "message": "google_business_profile not connected or location_id missing",
            },
        )

    request_payload = {
        "summary": summary[:1500],
        "topic_type": topic_type,
        "cta_url": cta_url,
    }
    api_body: dict = {
        "languageCode": "en-US",
        "summary": request_payload["summary"],
        "topicType": topic_type,
    }
    if cta_url:
        api_body["callToAction"] = {"actionType": "LEARN_MORE", "url": cta_url}

    url = (
        f"{_GBP_BASE}/accounts/{creds['account_id']}"
        f"/locations/{creds['location_id']}/localPosts"
    )
    headers = {
        "Authorization": f"Bearer {creds['access_token']}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=api_body, headers=headers)
    except Exception as e:
        logger.exception("os_action_gbp: HTTP error client_id=%s", ctx.client_id)
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={"stage": "gbp_api", "message": str(e)[:300]},
        )

    if resp.status_code >= 400:
        return ActionResult(
            status="failed",
            request_payload=request_payload,
            error_detail={
                "stage": "gbp_api",
                "status_code": resp.status_code,
                "message": resp.text[:500],
            },
        )

    response_body = resp.json() if resp.content else {}
    return ActionResult(
        status="succeeded",
        request_payload=request_payload,
        response_payload={"name": response_body.get("name"), "raw": response_body},
    )


SPEC = ActionSpec(
    name="gbp.post",
    worker="campaign",
    run=_run,
    required_connectors=["google_business_profile"],
    description="Publish a local post to the tenant's Google Business Profile.",
)
