"""Agent Control Center data-access helpers (Supabase fetches)."""

import logging
from collections import defaultdict

from backend.services.analytics_common import _QUERY_LIMIT
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)


def _chunks(items: list[str], size: int = 200):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def fetch_chat_messages(db, tenant_id: str, start: str) -> list[dict] | None:
    """Return chat messages or None on error."""
    try:
        res = (
            tenant_table(db, "chat_messages", tenant_id)
            .select("session_id, role, content, created_at")
            .eq("tenant_id", tenant_id)
            .gte("created_at", start)
            .order("created_at")
            .limit(_QUERY_LIMIT)
            .execute()
        )
        return res.data or []
    except Exception:
        logger.warning("control-center: failed to fetch chat_messages for %s", tenant_id, exc_info=True)
        return None


def fetch_conversations(db, tenant_id: str, session_ids: list[str]):
    """Return (conversation_meta, conversation_id_to_session, lead_id_to_session, assigned_ids)."""
    conversation_meta: dict[str, dict] = {}
    conversation_id_to_session: dict[str, str] = {}
    lead_id_to_session: dict[str, str] = {}
    assigned_ids: set[str] = set()

    try:
        for chunk in _chunks(session_ids):
            conv_res = (
                tenant_table(db, "conversations", tenant_id)
                .select("id, session_id, lead_id, assigned_to, channel, lead_captured, created_at, last_message_at")
                .eq("client_id", tenant_id)
                .in_("session_id", chunk)
                .execute()
            )
            for row in conv_res.data or []:
                session_id = row.get("session_id")
                if not session_id:
                    continue
                conversation_meta[session_id] = row
                if row.get("id"):
                    conversation_id_to_session[row["id"]] = session_id
                if row.get("lead_id"):
                    lead_id_to_session[row["lead_id"]] = session_id
                if row.get("assigned_to"):
                    assigned_ids.add(row["assigned_to"])
    except Exception:
        logger.warning("control-center: failed to fetch conversations for %s", tenant_id, exc_info=True)

    return conversation_meta, conversation_id_to_session, lead_id_to_session, assigned_ids


def fetch_leads(
    db,
    tenant_id: str,
    start: str,
    sessions: dict,
    conversation_id_to_session: dict[str, str],
    lead_id_to_session: dict[str, str],
    conversation_meta: dict[str, dict],
    assigned_ids: set[str],
):
    """Return leads_by_session map. Mutates assigned_ids."""
    leads_by_session: dict[str, dict] = {}
    lead_rows_by_id: dict[str, dict] = {}

    try:
        leads_res = (
            tenant_table(db, "leads", tenant_id)
            .select("id, conversation_id, name, email, status, lead_temperature, deal_value, assigned_to, source, created_at")
            .eq("client_id", tenant_id)
            .gte("created_at", start)
            .order("created_at", desc=True)
            .limit(_QUERY_LIMIT)
            .execute()
        )
        for lead in leads_res.data or []:
            lead_id = lead.get("id")
            if lead_id:
                lead_rows_by_id[lead_id] = lead

            session_id = None
            if lead_id and lead_id in lead_id_to_session:
                session_id = lead_id_to_session[lead_id]
            elif lead.get("conversation_id") in conversation_id_to_session:
                session_id = conversation_id_to_session[lead["conversation_id"]]
            elif lead.get("conversation_id") in sessions:
                session_id = lead["conversation_id"]

            if session_id and session_id not in leads_by_session:
                leads_by_session[session_id] = lead
                if lead.get("assigned_to"):
                    assigned_ids.add(lead["assigned_to"])
    except Exception:
        logger.warning("control-center: failed to fetch leads for %s", tenant_id, exc_info=True)

    for session_id, meta in conversation_meta.items():
        if session_id not in leads_by_session and meta.get("lead_id") in lead_rows_by_id:
            leads_by_session[session_id] = lead_rows_by_id[meta["lead_id"]]

    return leads_by_session


def fetch_appointments(db, tenant_id: str, lead_ids: list[str]) -> dict[str, list[dict]]:
    appointments_by_lead: dict[str, list[dict]] = defaultdict(list)
    if not lead_ids:
        return appointments_by_lead
    try:
        for chunk in _chunks(lead_ids):
            appt_res = (
                tenant_table(db, "appointments", tenant_id)
                .select("id, lead_id, status, created_at, start_time")
                .eq("tenant_id", tenant_id)
                .in_("lead_id", chunk)
                .execute()
            )
            for row in appt_res.data or []:
                if row.get("lead_id"):
                    appointments_by_lead[row["lead_id"]].append(row)
    except Exception:
        logger.warning("control-center: failed to fetch appointments for %s", tenant_id, exc_info=True)
    return appointments_by_lead


def fetch_invoices(db, tenant_id: str, lead_ids: list[str]) -> dict[str, list[dict]]:
    invoices_by_lead: dict[str, list[dict]] = defaultdict(list)
    if not lead_ids:
        return invoices_by_lead
    try:
        for chunk in _chunks(lead_ids):
            invoice_res = (
                tenant_table(db, "invoices", tenant_id)
                .select("id, lead_id, status, total, amount_paid, created_at, paid_at")
                .eq("tenant_id", tenant_id)
                .in_("lead_id", chunk)
                .execute()
            )
            for row in invoice_res.data or []:
                if row.get("lead_id"):
                    invoices_by_lead[row["lead_id"]].append(row)
    except Exception:
        logger.warning("control-center: failed to fetch invoices for %s", tenant_id, exc_info=True)
    return invoices_by_lead


def fetch_team_members(db, tenant_id: str, assigned_ids: set[str]) -> dict[str, str]:
    assigned_name_by_id: dict[str, str] = {}
    if not assigned_ids:
        return assigned_name_by_id
    try:
        for chunk in _chunks(sorted(assigned_ids)):
            member_res = (
                tenant_table(db, "team_members", tenant_id)
                .select("id, name, email")
                .eq("tenant_id", tenant_id)
                .in_("id", chunk)
                .execute()
            )
            for member in member_res.data or []:
                member_id = member.get("id")
                if member_id:
                    assigned_name_by_id[member_id] = member.get("name") or member.get("email") or "Team member"
    except Exception:
        logger.warning("control-center: failed to fetch team members for %s", tenant_id, exc_info=True)
    return assigned_name_by_id
