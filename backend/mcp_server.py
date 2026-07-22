"""AgentNexLiFy MCP Server — exposes business data as tools for AI assistants.

Allows business owners to connect AgentNexLiFy to Claude Desktop or ChatGPT
via the Model Context Protocol. They can ask "What leads came in today?" or
"What appointments do I have?" from their AI assistant.

Run standalone: python -m backend.mcp_server
Or import and mount alongside the FastAPI app.
"""

import logging
from datetime import datetime, timedelta, timezone

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

# stateless_http: production runs 4 uvicorn workers with no session
# affinity, so every request must be self-contained. streamable_http_path
# "/" because main.py mounts this app at /mcp - the public URL owners
# configure is <API_BASE>/mcp (what MCPSetupPage renders).
#
# DNS-rebinding protection is host-allowlist based and defaults to
# rejecting anything not localhost - prod probes got "Invalid Host
# header" behind Railway's proxy. This is a public API server
# authenticated by per-tenant mcp_ keys (not ambient browser
# credentials), so rebinding protection adds nothing here; disable it.
mcp = FastMCP(
    "AgentNexLiFy",
    instructions="AI-powered business automation — leads, appointments, conversations, and analytics. Authenticate with your dedicated MCP API key (Authorization: Bearer header, or pass it as the api_key argument).",
    stateless_http=True,
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    ),
)

# --- Auth helpers ---

def _header_api_key() -> str:
    """MCP key from the HTTP request headers, if this call came over HTTP.

    The Claude Desktop config we hand owners passes the key as an
    Authorization: Bearer header via mcp-remote, so tools work without
    pasting the key into every conversation. Stdio runs have no request -
    return empty and let the explicit api_key argument path handle it.
    """
    try:
        request = mcp.get_context().request_context.request
        if request is None:
            return ""
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()
        return (request.headers.get("x-api-key") or "").strip()
    except Exception:
        return ""


def _get_tenant_by_api_key(api_key: str) -> dict | None:
    """Look up tenant by dedicated MCP API key only. Returns tenant dict or None.

    Falls back to the Authorization header when no explicit key was passed.
    """
    api_key = (api_key or "").strip() or _header_api_key()

    if not api_key or not api_key.startswith("mcp_"):
        return None

    db = get_service_supabase()
    result = (
        db.table("tenants")
        .select("id, business_name, owner_email, plan, business_type, mcp_enabled")
        .eq("mcp_api_key", api_key)
        .eq("mcp_enabled", True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


# --- Tool 1: List Recent Leads ---

@mcp.tool()
def list_recent_leads(api_key: str = "", days: int = 7, limit: int = 20) -> str:
    """List recent leads captured by the chat widget.

    Args:
        api_key: Your AgentNexLiFy MCP API key (optional when the connection sends an Authorization header)
        days: Number of days to look back (default 7)
        limit: Maximum number of leads to return (default 20, max 50)
    """
    tenant = _get_tenant_by_api_key(api_key)
    if not tenant:
        return "Error: Invalid MCP API key. Check your AgentNexLiFy dashboard for your dedicated MCP key."

    limit = min(limit, 50)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    db = get_service_supabase()
    result = (
        db.table("leads")
        .select("name, email, phone, status, lead_score, areas_of_interest, conversation_summary, created_at")
        .eq("client_id", tenant["id"])
        .gte("created_at", since)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    leads = result.data or []
    if not leads:
        return f"No new leads in the last {days} days for {tenant['business_name']}."

    lines = [f"## {len(leads)} Recent Leads for {tenant['business_name']} (last {days} days)\n"]
    for lead in leads:
        name = lead.get("name") or "Unknown"
        email = lead.get("email") or "no email"
        phone = lead.get("phone") or "no phone"
        status = lead.get("status", "new")
        score = lead.get("lead_score") or 0
        interest = lead.get("areas_of_interest") or ""
        summary = lead.get("conversation_summary") or ""
        created = lead.get("created_at", "")[:10]

        line = f"- **{name}** ({email}, {phone}) — status: {status}, score: {score}"
        if interest:
            line += f", interest: {interest}"
        if summary:
            line += f"\n  > {summary[:100]}"
        line += f" [{created}]"
        lines.append(line)

    return "\n".join(lines)


# --- Tool 2: List Today's Appointments ---

@mcp.tool()
def list_today_appointments(api_key: str = "") -> str:
    """List today's appointments.

    Args:
        api_key: Your AgentNexLiFy MCP API key (optional when the connection sends an Authorization header)
    """
    tenant = _get_tenant_by_api_key(api_key)
    if not tenant:
        return "Error: Invalid API key."

    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    db = get_service_supabase()
    result = (
        db.table("appointments")
        .select("customer_name, customer_email, customer_phone, start_time, end_time, status, notes")
        .eq("tenant_id", tenant["id"])
        .gte("start_time", start_of_day.isoformat())
        .lt("start_time", end_of_day.isoformat())
        .order("start_time")
        .execute()
    )

    appts = result.data or []
    if not appts:
        return f"No appointments today for {tenant['business_name']}."

    lines = [f"## {len(appts)} Appointments Today for {tenant['business_name']}\n"]
    for a in appts:
        name = a.get("customer_name") or "Unknown"
        start = a.get("start_time", "")
        try:
            dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            time_str = dt.strftime("%I:%M %p")
        except Exception:
            time_str = start
        status = a.get("status", "booked")
        phone = a.get("customer_phone") or ""
        lines.append(f"- **{time_str}** — {name} ({status}){f' {phone}' if phone else ''}")

    return "\n".join(lines)


# --- Tool 3: Get Unread Conversations ---

@mcp.tool()
def get_unread_conversations(api_key: str = "", limit: int = 10) -> str:
    """Get recent conversations that may need attention.

    Args:
        api_key: Your AgentNexLiFy MCP API key (optional when the connection sends an Authorization header)
        limit: Maximum conversations to return (default 10)
    """
    tenant = _get_tenant_by_api_key(api_key)
    if not tenant:
        return "Error: Invalid API key."

    limit = min(limit, 25)
    db = get_service_supabase()
    result = (
        db.table("conversations")
        .select("id, session_id, status, lead_id, tags, created_at")
        .eq("client_id", tenant["id"])
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    convos = result.data or []
    if not convos:
        return f"No recent conversations for {tenant['business_name']}."

    lines = [f"## {len(convos)} Recent Conversations for {tenant['business_name']}\n"]
    for c in convos:
        status = c.get("status", "active")
        tags = ", ".join(c.get("tags") or []) or "no tags"
        created = c.get("created_at", "")[:16].replace("T", " ")
        lines.append(f"- [{created}] status: {status}, tags: {tags}")

    return "\n".join(lines)


# --- Tool 4: Get Action Items ---

@mcp.tool()
def get_action_items(api_key: str = "", status: str = "pending") -> str:
    """Get AI-extracted action items from conversations.

    Args:
        api_key: Your AgentNexLiFy MCP API key (optional when the connection sends an Authorization header)
        status: Filter by status — "pending", "done", or "all" (default "pending")
    """
    tenant = _get_tenant_by_api_key(api_key)
    if not tenant:
        return "Error: Invalid API key."

    db = get_service_supabase()
    query = (
        db.table("action_items")
        .select("description, due_date, priority, status, created_at")
        .eq("tenant_id", tenant["id"])
        .order("created_at", desc=True)
        .limit(30)
    )
    if status != "all":
        query = query.eq("status", status)

    result = query.execute()
    items = result.data or []

    if not items:
        return f"No {status} action items for {tenant['business_name']}."

    lines = [f"## {len(items)} Action Items ({status}) for {tenant['business_name']}\n"]
    for item in items:
        desc = item.get("description", "")
        priority = item.get("priority", "medium")
        due = item.get("due_date") or "no due date"
        emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "⚪")
        lines.append(f"- {emoji} {desc} (due: {due})")

    return "\n".join(lines)


# --- Tool 5: Get Analytics Summary ---

@mcp.tool()
def get_analytics_summary(api_key: str = "", days: int = 30) -> str:
    """Get a summary of business analytics — leads, conversations, appointments.

    Args:
        api_key: Your AgentNexLiFy MCP API key (optional when the connection sends an Authorization header)
        days: Number of days to analyze (default 30)
    """
    tenant = _get_tenant_by_api_key(api_key)
    if not tenant:
        return "Error: Invalid API key."

    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    db = get_service_supabase()

    # Count leads
    leads = db.table("leads").select("id", count="exact").eq("client_id", tenant["id"]).gte("created_at", since).execute()
    lead_count = leads.count or 0

    # Count conversations
    convos = db.table("conversations").select("id", count="exact").eq("client_id", tenant["id"]).gte("created_at", since).execute()
    convo_count = convos.count or 0

    # Count appointments
    appts = db.table("appointments").select("id", count="exact").eq("tenant_id", tenant["id"]).gte("start_time", since).execute()
    appt_count = appts.count or 0

    # Conversion rate
    rate = round((lead_count / convo_count * 100), 1) if convo_count > 0 else 0

    return (
        f"## Analytics Summary for {tenant['business_name']} (last {days} days)\n\n"
        f"- **Conversations:** {convo_count}\n"
        f"- **Leads captured:** {lead_count}\n"
        f"- **Appointments booked:** {appt_count}\n"
        f"- **Conversion rate:** {rate}% (leads / conversations)\n"
    )


# --- Tool 6: Reply to Conversation ---

@mcp.tool()
def reply_to_conversation(session_id: str, message: str, api_key: str = "") -> str:
    """Send a reply to a chat conversation as the business owner.

    Args:
        api_key: Your AgentNexLiFy MCP API key (optional when the connection sends an Authorization header)
        session_id: The session ID of the conversation to reply to
        message: The reply message text
    """
    tenant = _get_tenant_by_api_key(api_key)
    if not tenant:
        return "Error: Invalid API key."

    if not message or not message.strip():
        return "Error: Message cannot be empty."

    db = get_service_supabase()

    # Insert into chat_messages as an assistant (team reply)
    db.table("chat_messages").insert({
        "tenant_id": tenant["id"],
        "session_id": session_id,
        "role": "assistant",
        "content": message.strip(),
    }).execute()

    return f"Reply sent to conversation {session_id}: \"{message[:50]}{'...' if len(message) > 50 else ''}\""


# --- Standalone entry point ---

if __name__ == "__main__":
    mcp.run()
