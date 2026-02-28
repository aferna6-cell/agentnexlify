"""Chat endpoints — send message and get history."""

import logging

from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.models.database import get_supabase
from backend.models.schemas import ChatMessageRequest, ChatMessageResponse, ClientRow
from backend.services.claude_agent import run_agent
from backend.services.conversation import get_or_create_conversation, get_conversation_messages

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])
limiter = Limiter(key_func=get_remote_address)


def _get_client_by_api_key(api_key: str) -> ClientRow:
    """Look up a client by their widget API key."""
    db = get_supabase()
    result = (
        db.table("clients")
        .select("*")
        .eq("widget_api_key", api_key)
        .eq("active", True)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    return ClientRow(**result.data[0])


@router.post("/message", response_model=ChatMessageResponse)
@limiter.limit("20/minute")
async def send_message(request: Request, req: ChatMessageRequest):
    """Main chat endpoint — process a user message and return the AI response."""
    client = _get_client_by_api_key(req.client_api_key)

    conversation = get_or_create_conversation(client.id, req.session_id)
    conversation_id = conversation["id"]

    reply = await run_agent(client, conversation_id, req.message)

    return ChatMessageResponse(reply=reply, conversation_id=conversation_id)


@router.get("/history/{session_id}")
async def get_history(session_id: str, client_api_key: str):
    """Get chat history for a session. Used when widget reconnects."""
    client = _get_client_by_api_key(client_api_key)

    db = get_supabase()
    conv_result = (
        db.table("conversations")
        .select("id")
        .eq("client_id", client.id)
        .eq("session_id", session_id)
        .eq("status", "active")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not conv_result.data:
        return {"messages": [], "bot_name": client.bot_name, "agent_name": client.agent_name}

    conversation_id = conv_result.data[0]["id"]
    messages = get_conversation_messages(conversation_id)

    # Filter to only user and assistant messages for the widget
    display_messages = [
        {
            "role": m["role"],
            "content": m["content"],
            "created_at": m["created_at"],
        }
        for m in messages
        if m["role"] in ("user", "assistant") and m["content"]
    ]

    return {
        "messages": display_messages,
        "bot_name": client.bot_name,
        "agent_name": client.agent_name,
    }


@router.get("/config")
async def get_widget_config(client_api_key: str):
    """Get widget configuration (bot name, agent name, brand color)."""
    client = _get_client_by_api_key(client_api_key)
    return {
        "bot_name": client.bot_name,
        "agent_name": client.agent_name,
        "brand_color": client.brand_color,
    }
