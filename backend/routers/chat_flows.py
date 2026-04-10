"""Chat flows — visual conversation flow builder CRUD + preset templates + analytics."""

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.models.database import get_service_supabase
from backend.routers.auth import _get_current_tenant, require_role

logger = logging.getLogger(__name__)

# Simple in-memory cache for flow analytics (matches pattern from analytics.py)
_cache: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 300  # 5 minutes


def _get_cached(key: str) -> dict | None:
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < _CACHE_TTL:
            return data
        del _cache[key]
    return None


def _set_cache(key: str, data: dict) -> None:
    if len(_cache) > 200:
        cutoff = time.time() - _CACHE_TTL
        expired = [k for k, (ts, _) in _cache.items() if ts < cutoff]
        for k in expired:
            del _cache[k]
    _cache[key] = (time.time(), data)

router = APIRouter(prefix="/api/v1/chat-flows", tags=["chat-flows"])

# --- Preset Flow Templates ---

PRESET_TEMPLATES = [
    {
        "name": "General Business",
        "description": "Greeting → FAQ → Appointment or transfer to human",
        "flow_json": {
            "nodes": [
                {"id": "greeting", "type": "greeting", "data": {"message": "Hi! How can I help you today?"}, "position": {"x": 250, "y": 0}},
                {"id": "faq", "type": "ai_response", "data": {"label": "Answer FAQ"}, "position": {"x": 250, "y": 150}},
                {"id": "check_intent", "type": "condition", "data": {"label": "Wants appointment?", "condition": "appointment|schedule|book"}, "position": {"x": 250, "y": 300}},
                {"id": "book", "type": "action", "data": {"action": "show_booking", "label": "Show Booking Form"}, "position": {"x": 100, "y": 450}},
                {"id": "handoff", "type": "handoff", "data": {"label": "Transfer to Team"}, "position": {"x": 400, "y": 450}},
            ],
            "edges": [
                {"source": "greeting", "target": "faq"},
                {"source": "faq", "target": "check_intent"},
                {"source": "check_intent", "target": "book", "label": "Yes"},
                {"source": "check_intent", "target": "handoff", "label": "No"},
            ],
        },
    },
    {
        "name": "Restaurant",
        "description": "Greeting → Menu → Order → Confirmation",
        "flow_json": {
            "nodes": [
                {"id": "greeting", "type": "greeting", "data": {"message": "Welcome! Would you like to see our menu or place an order?"}, "position": {"x": 250, "y": 0}},
                {"id": "menu", "type": "action", "data": {"action": "show_menu", "label": "Show Menu"}, "position": {"x": 100, "y": 150}},
                {"id": "order", "type": "action", "data": {"action": "take_order", "label": "Take Order"}, "position": {"x": 400, "y": 150}},
                {"id": "confirm", "type": "action", "data": {"action": "confirm_order", "label": "Confirm Order"}, "position": {"x": 250, "y": 300}},
                {"id": "hours", "type": "ai_response", "data": {"label": "Answer Hours/Location"}, "position": {"x": 250, "y": 450}},
            ],
            "edges": [
                {"source": "greeting", "target": "menu", "label": "Menu"},
                {"source": "greeting", "target": "order", "label": "Order"},
                {"source": "menu", "target": "order"},
                {"source": "order", "target": "confirm"},
                {"source": "greeting", "target": "hours", "label": "Other"},
            ],
        },
    },
    {
        "name": "Contractor / Service",
        "description": "Greeting → Service Type → Quote Request → Book Estimate",
        "flow_json": {
            "nodes": [
                {"id": "greeting", "type": "greeting", "data": {"message": "Hi! What service can we help you with?"}, "position": {"x": 250, "y": 0}},
                {"id": "service", "type": "question", "data": {"label": "What service?", "question": "What type of service do you need?"}, "position": {"x": 250, "y": 150}},
                {"id": "quote", "type": "action", "data": {"action": "collect_info", "label": "Collect Quote Details"}, "position": {"x": 100, "y": 300}},
                {"id": "book", "type": "action", "data": {"action": "show_booking", "label": "Book Free Estimate"}, "position": {"x": 400, "y": 300}},
                {"id": "faq", "type": "ai_response", "data": {"label": "Answer Questions"}, "position": {"x": 250, "y": 450}},
            ],
            "edges": [
                {"source": "greeting", "target": "service"},
                {"source": "service", "target": "quote", "label": "Needs quote"},
                {"source": "service", "target": "book", "label": "Wants estimate"},
                {"source": "service", "target": "faq", "label": "Has questions"},
                {"source": "quote", "target": "book"},
            ],
        },
    },
]


class FlowCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: str | None = Field(None, max_length=500)
    flow_json: dict = Field(default_factory=lambda: {"nodes": [], "edges": []})


class FlowUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=500)
    flow_json: dict | None = None
    is_active: bool | None = None


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


@router.get("/{tenant_id}")
async def list_flows(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """List all chat flows for a tenant."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    result = (
        db.table("chat_flows")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .execute()
    )
    return {"flows": result.data or []}


@router.get("/{tenant_id}/templates")
async def list_templates(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """List preset flow templates."""
    _verify_tenant(claims, tenant_id)
    return {"templates": PRESET_TEMPLATES}


@router.post("/{tenant_id}")
async def create_flow(
    tenant_id: str,
    req: FlowCreate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create a new chat flow."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    data = {
        "tenant_id": tenant_id,
        "name": req.name.strip(),
        "flow_json": req.flow_json,
    }
    if req.description:
        data["description"] = req.description.strip()

    result = db.table("chat_flows").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create flow")
    return result.data[0]


@router.post("/{tenant_id}/from-template/{template_index}")
async def create_from_template(
    tenant_id: str,
    template_index: int,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create a flow from a preset template."""
    _verify_tenant(claims, tenant_id)

    if template_index < 0 or template_index >= len(PRESET_TEMPLATES):
        raise HTTPException(status_code=400, detail="Invalid template index")

    template = PRESET_TEMPLATES[template_index]
    db = get_service_supabase()
    data = {
        "tenant_id": tenant_id,
        "name": template["name"],
        "description": template["description"],
        "flow_json": template["flow_json"],
    }
    result = db.table("chat_flows").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create flow from template")
    return result.data[0]


@router.put("/{tenant_id}/{flow_id}")
async def update_flow(
    tenant_id: str,
    flow_id: str,
    req: FlowUpdate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Update a chat flow."""
    _verify_tenant(claims, tenant_id)

    updates = {}
    if req.name is not None:
        updates["name"] = req.name.strip()
    if req.description is not None:
        updates["description"] = req.description.strip()
    if req.flow_json is not None:
        updates["flow_json"] = req.flow_json
    if req.is_active is not None:
        # Deactivate all other flows first if activating this one
        if req.is_active:
            db = get_service_supabase()
            db.table("chat_flows").update({"is_active": False}).eq("tenant_id", tenant_id).eq("is_active", True).execute()
        updates["is_active"] = req.is_active

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    db = get_service_supabase()
    result = (
        db.table("chat_flows")
        .update(updates)
        .eq("id", flow_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Flow not found")
    return result.data[0]


@router.delete("/{tenant_id}/{flow_id}")
async def delete_flow(
    tenant_id: str,
    flow_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Delete a chat flow."""
    _verify_tenant(claims, tenant_id)

    db = get_service_supabase()
    db.table("chat_flows").delete().eq("id", flow_id).eq("tenant_id", tenant_id).execute()
    return {"deleted": True}


# ------------------------------------------------------------------
# Flow Analytics
# ------------------------------------------------------------------

# Safety cap for unbounded queries
_QUERY_LIMIT = 5000


def _period_to_days(period: str) -> int:
    mapping = {"7d": 7, "30d": 30, "90d": 90}
    return mapping.get(period, 30)


@router.get("/{tenant_id}/{flow_id}/analytics")
async def flow_analytics(
    tenant_id: str,
    flow_id: str,
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    """Get analytics for a specific chat flow.

    Returns:
    - total_conversations: how many conversations used this flow in the period
    - daily_usage: conversation count per day
    - node_stats: per-node trigger counts (mock data for v1, real tracking in future)
    - summary: most/least triggered nodes and suggested improvements
    """
    _verify_tenant(claims, tenant_id)

    cache_key = f"flow_analytics:{tenant_id}:{flow_id}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    days = _period_to_days(period)
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    now_iso = datetime.now(timezone.utc).isoformat()
    db = get_service_supabase()

    # 1. Verify the flow exists and belongs to the tenant
    try:
        flow_res = (
            db.table("chat_flows")
            .select("id, name, flow_json, is_active, created_at")
            .eq("id", flow_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.error("flow_analytics: failed to fetch flow %s for tenant %s", flow_id, tenant_id, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch flow")

    if not flow_res.data:
        raise HTTPException(status_code=404, detail="Flow not found")

    flow = flow_res.data[0]
    flow_json = flow.get("flow_json") or {}
    nodes = flow_json.get("nodes", [])

    # 2. Count conversations that used this flow from activity_log
    total_conversations = 0
    daily_usage: dict[str, int] = defaultdict(int)
    session_ids: list[str] = []

    try:
        activity_res = (
            db.table("activity_log")
            .select("created_at, metadata")
            .eq("tenant_id", tenant_id)
            .eq("activity_type", "flow_used")
            .gte("created_at", start)
            .lt("created_at", now_iso)
            .limit(_QUERY_LIMIT)
            .execute()
        )

        for row in activity_res.data or []:
            meta = row.get("metadata") or {}
            if meta.get("flow_id") == flow_id:
                total_conversations += 1
                date_str = row["created_at"][:10]
                daily_usage[date_str] += 1
                sid = meta.get("session_id")
                if sid:
                    session_ids.append(sid)

    except Exception:
        logger.warning(
            "flow_analytics: failed to query activity_log for flow %s tenant %s",
            flow_id, tenant_id, exc_info=True,
        )

    # Build full date range for daily chart
    today = datetime.now(timezone.utc).date()
    daily_data = []
    for i in range(days):
        d = (today - timedelta(days=days - 1 - i)).isoformat()
        daily_data.append({"date": d, "count": daily_usage.get(d, 0)})

    # 3. Generate per-node stats (mock/estimated for v1)
    # In v1 we estimate node triggers proportionally from total conversations,
    # since the flow is prompt-injected and we don't track individual node hits yet.
    node_stats = []
    if nodes and total_conversations > 0:
        for idx, node in enumerate(nodes):
            ntype = node.get("type", "")
            label = node.get("data", {}).get("label") or node.get("data", {}).get("message") or ntype
            nid = node.get("id", f"node_{idx}")

            # Greeting nodes are always hit; others scale down based on position in flow
            if ntype == "greeting":
                estimated_triggers = total_conversations
            elif ntype in ("ai_response", "question"):
                # These tend to get triggered most of the time
                estimated_triggers = max(1, int(total_conversations * 0.8))
            elif ntype == "condition":
                estimated_triggers = max(1, int(total_conversations * 0.6))
            elif ntype == "action":
                estimated_triggers = max(1, int(total_conversations * 0.4))
            elif ntype == "handoff":
                estimated_triggers = max(1, int(total_conversations * 0.15))
            else:
                estimated_triggers = max(1, int(total_conversations * 0.5))

            node_stats.append({
                "node_id": nid,
                "label": label,
                "type": ntype,
                "estimated_triggers": estimated_triggers,
            })
    elif nodes:
        # No conversations yet -- all zeros
        for idx, node in enumerate(nodes):
            label = node.get("data", {}).get("label") or node.get("data", {}).get("message") or node.get("type", "")
            node_stats.append({
                "node_id": node.get("id", f"node_{idx}"),
                "label": label,
                "type": node.get("type", ""),
                "estimated_triggers": 0,
            })

    # 4. Build summary
    most_triggered = None
    least_triggered = None
    if node_stats:
        sorted_nodes = sorted(node_stats, key=lambda n: n["estimated_triggers"], reverse=True)
        most_triggered = {
            "node_id": sorted_nodes[0]["node_id"],
            "label": sorted_nodes[0]["label"],
            "count": sorted_nodes[0]["estimated_triggers"],
        }
        # Least triggered excludes greeting (always 100%)
        non_greeting = [n for n in sorted_nodes if n["type"] != "greeting"]
        if non_greeting:
            least_triggered = {
                "node_id": non_greeting[-1]["node_id"],
                "label": non_greeting[-1]["label"],
                "count": non_greeting[-1]["estimated_triggers"],
            }

    suggestions = []
    if total_conversations == 0:
        suggestions.append("This flow has not been used yet. Activate it and drive traffic to your widget to start collecting data.")
    else:
        if least_triggered and total_conversations > 5:
            ratio = least_triggered["count"] / total_conversations if total_conversations > 0 else 0
            if ratio < 0.2:
                suggestions.append(
                    f"The '{least_triggered['label']}' step is reached by very few visitors. "
                    "Consider simplifying the flow or making the path to this step more prominent."
                )
        handoff_nodes = [n for n in node_stats if n["type"] == "handoff"]
        if handoff_nodes and handoff_nodes[0]["estimated_triggers"] > total_conversations * 0.3:
            suggestions.append(
                "Over 30% of conversations reach the handoff step. Consider adding more FAQ content "
                "or automated responses to reduce the need for human handoff."
            )
        if not suggestions:
            suggestions.append("Flow is performing well. Keep monitoring as conversation volume grows.")

    result = {
        "flow_id": flow_id,
        "flow_name": flow.get("name", ""),
        "is_active": flow.get("is_active", False),
        "period": period,
        "total_conversations": total_conversations,
        "daily_usage": daily_data,
        "node_stats": node_stats,
        "summary": {
            "most_triggered_node": most_triggered,
            "least_triggered_node": least_triggered,
            "suggestions": suggestions,
        },
    }

    _set_cache(cache_key, result)
    return result
