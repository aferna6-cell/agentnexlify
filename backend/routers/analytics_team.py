"""Team performance + UTM lead source analytics endpoints.

Split into separate file to avoid making analytics.py even larger.
Imported and included in analytics.py router.
"""

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.dependencies import verify_tenant
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

# Reuse cache from analytics.py (imported at runtime to avoid circular imports)
_local_cache: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 300


def _get_cached(key: str) -> dict | None:
    if key in _local_cache:
        ts, data = _local_cache[key]
        if time.time() - ts < _CACHE_TTL:
            return data
        del _local_cache[key]
    return None


def _set_cache(key: str, data: dict) -> None:
    if len(_local_cache) > 200:
        cutoff = time.time() - _CACHE_TTL
        expired = [k for k, (ts, _) in _local_cache.items() if ts < cutoff]
        for k in expired:
            del _local_cache[k]
    _local_cache[key] = (time.time(), data)


# ---------------------------------------------------------------------------
# Team Performance Dashboard
# ---------------------------------------------------------------------------


@router.get("/{tenant_id}/team-performance")
async def get_team_performance(
    tenant_id: str,
    days: int = Query(30, ge=7, le=365),
    claims: dict = Depends(_get_current_tenant),
):
    """Get per-team-member performance metrics.

    Returns for each team member:
    - conversations_handled: count of conversations assigned to them
    - avg_response_time_seconds: average first-response time
    - leads_assigned: count of leads assigned to them
    - appointments_booked: count of appointments they're linked to
    - action_items_completed: count of completed action items
    """
    verify_tenant(claims, tenant_id)

    cache_key = f"team_perf:{tenant_id}:{days}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    db = get_supabase()
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days)).isoformat()

    # 1. Fetch team members (including owner)
    members: list[dict] = []
    try:
        owner_result = (
            db.table("tenants")
            .select("id, owner_email, owner_name")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        if owner_result.data:
            o = owner_result.data[0]
            members.append({
                "id": str(o["id"]),
                "name": o.get("owner_name") or o.get("owner_email") or "Owner",
                "email": o.get("owner_email") or "",
                "role": "owner",
            })
    except Exception:
        logger.warning("team_perf: failed to fetch owner for %s", tenant_id, exc_info=True)

    try:
        team_result = (
            db.table("team_members")
            .select("id, name, email, role, invite_accepted")
            .eq("tenant_id", tenant_id)
            .eq("invite_accepted", True)
            .execute()
        )
        for m in team_result.data or []:
            members.append({
                "id": str(m["id"]),
                "name": m.get("name") or m.get("email") or "Team Member",
                "email": m.get("email") or "",
                "role": m.get("role") or "member",
            })
    except Exception:
        logger.warning("team_perf: failed to fetch team members for %s", tenant_id, exc_info=True)

    if not members:
        result = {"members": [], "period_days": days}
        _set_cache(cache_key, result)
        return result

    member_ids = [m["id"] for m in members]
    member_names = {m["id"]: m["name"] for m in members}

    # 2. Conversations assigned to each member (conversations table uses client_id)
    conv_counts: dict[str, int] = defaultdict(int)
    try:
        convos = (
            db.table("conversations")
            .select("assigned_to")
            .eq("client_id", tenant_id)
            .gte("created_at", start)
            .not_.is_("assigned_to", "null")
            .limit(5000)
            .execute()
        )
        for c in convos.data or []:
            assigned = c.get("assigned_to")
            if assigned:
                conv_counts[assigned] += 1
    except Exception:
        logger.warning("team_perf: failed to fetch conversations for %s", tenant_id, exc_info=True)

    # 3. Response times per member (response_metrics doesn't have assigned_to,
    #    so we use conversation assignment + response_metrics join in Python)
    avg_response_times: dict[str, float] = {}
    try:
        # Get assigned conversations with session_ids
        assigned_convos = (
            db.table("conversations")
            .select("session_id, assigned_to")
            .eq("client_id", tenant_id)
            .gte("created_at", start)
            .not_.is_("assigned_to", "null")
            .limit(5000)
            .execute()
        )
        session_to_assignee: dict[str, str] = {}
        for c in assigned_convos.data or []:
            if c.get("session_id") and c.get("assigned_to"):
                session_to_assignee[c["session_id"]] = c["assigned_to"]

        if session_to_assignee:
            # Fetch response metrics for these conversations
            metrics_result = (
                db.table("response_metrics")
                .select("conversation_id, response_time_seconds")
                .eq("tenant_id", tenant_id)
                .gte("created_at", start)
                .limit(5000)
                .execute()
            )
            # Also need conversation_id -> session_id mapping
            conv_id_to_session: dict[str, str] = {}
            try:
                conv_ids_result = (
                    db.table("conversations")
                    .select("id, session_id")
                    .eq("client_id", tenant_id)
                    .gte("created_at", start)
                    .limit(5000)
                    .execute()
                )
                for c in conv_ids_result.data or []:
                    conv_id_to_session[c["id"]] = c.get("session_id") or ""
            except Exception:
                pass

            member_times: dict[str, list[int]] = defaultdict(list)
            for m in metrics_result.data or []:
                conv_id = m.get("conversation_id")
                rt = m.get("response_time_seconds")
                if conv_id and rt is not None:
                    session_id = conv_id_to_session.get(conv_id)
                    if session_id:
                        assignee = session_to_assignee.get(session_id)
                        if assignee:
                            member_times[assignee].append(rt)

            for mid, times in member_times.items():
                if times:
                    avg_response_times[mid] = round(sum(times) / len(times), 1)
    except Exception:
        logger.warning("team_perf: failed to fetch response times for %s", tenant_id, exc_info=True)

    # 4. Leads assigned to each member (leads table uses client_id)
    lead_counts: dict[str, int] = defaultdict(int)
    try:
        leads = (
            db.table("leads")
            .select("assigned_to")
            .eq("client_id", tenant_id)
            .gte("created_at", start)
            .not_.is_("assigned_to", "null")
            .limit(5000)
            .execute()
        )
        for l in leads.data or []:
            assigned = l.get("assigned_to")
            if assigned:
                lead_counts[assigned] += 1
    except Exception:
        logger.warning("team_perf: failed to fetch leads for %s", tenant_id, exc_info=True)

    # 5. Appointments booked — attribute to team member via lead assignment
    #    (appointments table has no created_by column; use lead_id -> leads.assigned_to)
    appt_counts: dict[str, int] = defaultdict(int)
    try:
        appts = (
            db.table("appointments")
            .select("lead_id")
            .eq("tenant_id", tenant_id)
            .gte("created_at", start)
            .neq("status", "cancelled")
            .not_.is_("lead_id", "null")
            .limit(5000)
            .execute()
        )
        appt_lead_ids = list({a["lead_id"] for a in (appts.data or []) if a.get("lead_id")})
        if appt_lead_ids:
            # Look up which team member owns each lead
            chunk_size = 200
            for i in range(0, len(appt_lead_ids), chunk_size):
                chunk = appt_lead_ids[i:i + chunk_size]
                lead_assign_result = (
                    db.table("leads")
                    .select("id, assigned_to")
                    .in_("id", chunk)
                    .not_.is_("assigned_to", "null")
                    .execute()
                )
                for la in lead_assign_result.data or []:
                    assigned = la.get("assigned_to")
                    if assigned:
                        appt_counts[assigned] += 1
    except Exception:
        logger.warning("team_perf: failed to fetch appointments for %s", tenant_id, exc_info=True)

    # 6. Action items completed (action_items table uses tenant_id)
    action_counts: dict[str, int] = defaultdict(int)
    try:
        actions = (
            db.table("action_items")
            .select("assigned_to")
            .eq("tenant_id", tenant_id)
            .eq("status", "done")
            .gte("created_at", start)
            .not_.is_("assigned_to", "null")
            .limit(5000)
            .execute()
        )
        for ai in actions.data or []:
            assigned = ai.get("assigned_to")
            if assigned:
                action_counts[assigned] += 1
    except Exception:
        logger.warning("team_perf: failed to fetch action items for %s", tenant_id, exc_info=True)

    # Build response
    member_metrics = []
    for m in members:
        mid = m["id"]
        member_metrics.append({
            "id": mid,
            "name": m["name"],
            "email": m["email"],
            "role": m["role"],
            "conversations_handled": conv_counts.get(mid, 0),
            "avg_response_time_seconds": avg_response_times.get(mid, 0),
            "leads_assigned": lead_counts.get(mid, 0),
            "appointments_booked": appt_counts.get(mid, 0),
            "action_items_completed": action_counts.get(mid, 0),
        })

    # Sort by conversations handled (most active first)
    member_metrics.sort(key=lambda x: -x["conversations_handled"])

    result = {
        "members": member_metrics,
        "period_days": days,
        "total_conversations": sum(conv_counts.values()),
        "total_leads_assigned": sum(lead_counts.values()),
    }

    _set_cache(cache_key, result)
    return result


# ---------------------------------------------------------------------------
# Lead Source UTM Analytics
# ---------------------------------------------------------------------------


@router.get("/{tenant_id}/lead-sources-utm")
async def lead_sources_utm(
    tenant_id: str,
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    claims: dict = Depends(_get_current_tenant),
):
    """Breakdown of leads by UTM source, medium, and campaign.

    Reads the `source` and `metadata` fields from the leads table.
    UTM params are stored when the widget captures a lead with visitor_info
    containing utm_source, utm_medium, utm_campaign.

    Returns:
    - by_source: lead count per utm_source value
    - by_medium: lead count per utm_medium value
    - by_campaign: lead count per utm_campaign value
    - total_with_utm: count of leads that have any UTM data
    - total_without_utm: count of leads with no UTM data
    - conversion_by_source: for each source, how many converted to appointments
    """
    verify_tenant(claims, tenant_id)

    cache_key = f"utm_sources:{tenant_id}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    days = {"7d": 7, "30d": 30, "90d": 90}[period]
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    now_iso = datetime.now(timezone.utc).isoformat()

    db = get_supabase()

    # Fetch leads with source and metadata (leads table uses client_id)
    try:
        leads_result = (
            db.table("leads")
            .select("id, source, status, created_at")
            .eq("client_id", tenant_id)
            .gte("created_at", start)
            .lt("created_at", now_iso)
            .limit(5000)
            .execute()
        )
        leads = leads_result.data or []
    except Exception:
        logger.warning("utm_sources: failed to fetch leads for %s", tenant_id, exc_info=True)
        leads = []

    # Also fetch activity_log entries with UTM metadata for these leads
    lead_ids = [l["id"] for l in leads]
    utm_by_lead: dict[str, dict] = {}  # lead_id -> {utm_source, utm_medium, utm_campaign}

    if lead_ids:
        try:
            # Activity log stores UTM data in metadata field when leads are captured
            chunk_size = 200
            for i in range(0, len(lead_ids), chunk_size):
                chunk = lead_ids[i:i + chunk_size]
                activity_result = (
                    db.table("activity_log")
                    .select("lead_id, metadata")
                    .eq("tenant_id", tenant_id)
                    .eq("activity_type", "lead_captured")
                    .in_("lead_id", chunk)
                    .limit(5000)
                    .execute()
                )
                for a in activity_result.data or []:
                    lid = a.get("lead_id")
                    meta = a.get("metadata")
                    if lid and meta and isinstance(meta, dict):
                        utm_data = {}
                        if meta.get("utm_source"):
                            utm_data["utm_source"] = meta["utm_source"]
                        if meta.get("utm_medium"):
                            utm_data["utm_medium"] = meta["utm_medium"]
                        if meta.get("utm_campaign"):
                            utm_data["utm_campaign"] = meta["utm_campaign"]
                        if utm_data:
                            utm_by_lead[lid] = utm_data
        except Exception:
            logger.warning("utm_sources: failed to fetch activity log UTM data for %s", tenant_id, exc_info=True)

    # Aggregate by source, medium, campaign
    by_source: dict[str, int] = defaultdict(int)
    by_medium: dict[str, int] = defaultdict(int)
    by_campaign: dict[str, int] = defaultdict(int)
    converted_by_source: dict[str, int] = defaultdict(int)
    total_with_utm = 0
    total_without_utm = 0

    converted_statuses = {"appointment_booked", "closed"}

    for lead in leads:
        lid = lead["id"]
        source_val = lead.get("source") or ""
        status = lead.get("status") or "new"
        utm = utm_by_lead.get(lid, {})

        # Determine the effective source
        effective_source = utm.get("utm_source") or source_val or "direct"
        effective_medium = utm.get("utm_medium") or ""
        effective_campaign = utm.get("utm_campaign") or ""

        has_utm = bool(utm.get("utm_source") or utm.get("utm_medium") or utm.get("utm_campaign"))

        if has_utm:
            total_with_utm += 1
        else:
            total_without_utm += 1

        by_source[effective_source] += 1
        if effective_medium:
            by_medium[effective_medium] += 1
        if effective_campaign:
            by_campaign[effective_campaign] += 1

        if status in converted_statuses:
            converted_by_source[effective_source] += 1

    # Build sorted breakdowns
    source_breakdown = [
        {
            "source": s,
            "count": c,
            "converted": converted_by_source.get(s, 0),
            "conversion_rate": round((converted_by_source.get(s, 0) / c * 100), 1) if c > 0 else 0,
        }
        for s, c in sorted(by_source.items(), key=lambda x: -x[1])
    ]

    medium_breakdown = [
        {"medium": m, "count": c}
        for m, c in sorted(by_medium.items(), key=lambda x: -x[1])
    ]

    campaign_breakdown = [
        {"campaign": c, "count": cnt}
        for c, cnt in sorted(by_campaign.items(), key=lambda x: -x[1])
    ]

    result = {
        "by_source": source_breakdown,
        "by_medium": medium_breakdown,
        "by_campaign": campaign_breakdown,
        "total_leads": len(leads),
        "total_with_utm": total_with_utm,
        "total_without_utm": total_without_utm,
    }

    _set_cache(cache_key, result)
    return result
