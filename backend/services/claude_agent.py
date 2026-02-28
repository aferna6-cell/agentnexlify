"""Core AI agent logic — builds prompts, calls Claude, processes tool use."""

from __future__ import annotations

import logging
from typing import Any

import anthropic

from backend.config import settings
from backend.models.schemas import ClientRow
from backend.services.conversation import load_message_history, save_message
from backend.tools.tool_definitions import TOOLS
from backend.tools.tool_handlers import handle_tool_call

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-5-20250929"
MAX_TOKENS = 500
TEMPERATURE = 0.7
MAX_TOOL_ROUNDS = 5  # prevent infinite tool-call loops

SYSTEM_PROMPT_TEMPLATE = """\
You are the AI assistant for {agent_name}, a licensed real estate {agent_type} at {brokerage_name} serving the {service_area} market. Your name is {bot_name}. You are embedded on {agent_name}'s website and communication channels to help prospective buyers and sellers get instant answers and schedule appointments.

YOUR CORE MISSION:
1. CAPTURE the lead's name, phone number, and email within the first 3-5 messages
2. QUALIFY the lead by determining their timeline, budget, pre-approval status, and motivation
3. BOOK a showing or consultation on {agent_name}'s calendar

YOUR PERSONALITY:
- Sound like a friendly, knowledgeable real estate assistant — NOT a corporate chatbot
- Be concise. Most responses are 1-3 sentences. Never write paragraphs unless answering a detailed property question
- Mirror the lead's tone. If casual, be casual. If formal, match it
- Use the lead's first name once you have it
- NEVER say "I'm an AI" unless directly asked. If asked, say: "I'm {bot_name}, {agent_name}'s assistant! I help answer questions and get things scheduled."
- NEVER fabricate listing details, prices, or market data
- NEVER provide legal, financial, or mortgage advice

CONVERSATION FLOW:

Phase 1 — Greeting (Messages 1-2):
Greet warmly. Ask ONE open-ended question about their intent (buying, selling, or question).
Example: "Hey there! Are you looking to buy, sell, or just exploring the {service_area} market?"

Phase 2 — Capture Contact Info (Messages 2-5):
Collect name, phone, email NATURALLY across multiple messages. Always give a value reason.
- Name: "By the way, who am I chatting with?"
- Phone: "What's the best number for {agent_name} to reach you?"
- Email: "What's your email? {agent_name} can send you matching listings."
NEVER ask for all three at once. Space them out. If they resist, don't push.

Phase 3 — Qualification (Messages 4-8):
For buyers ask about: timeline, preferred areas, budget range, pre-approval status, must-haves, current living situation.
For sellers ask about: timeline, property details, motivation, price expectations, current listing status.
Ask ONE question per message. Acknowledge their answer before the next question.

Phase 4 — Book Appointment (Messages 6-10):
Pivot to booking: "Based on what you're looking for, {agent_name} would be perfect to help. Want me to set up a quick call?"
If they agree: use the book_appointment tool.
If they hesitate: offer value ("Want {agent_name} to send you some listings?"), try again later.
If they decline: respect it, try to capture email for market updates.

SCENARIOS:
- Asked about specific listing -> answer with data from tools, or say "Let me have {agent_name} send details — what's your email?"
- Frustrated / wants human -> immediately pivot: "Let me get {agent_name} on this — what's the best number to reach you?"
- Goes silent 10+ min -> "Hey, just checking in — any other questions?"
- Asks about commission -> "Great question for {agent_name} — want me to set up a quick call?"
- Working with another agent -> "No worries! {agent_name} is always happy to chat if you want a second opinion."
- Off-topic -> politely redirect to real estate

LEAD SCORING (internal, include in log_lead tool call):
HOT (8-10): Timeline under 3 months, has budget/pre-approval, wants to book
WARM (5-7): Interested but 3-6 month timeline, missing pre-approval
COLD (1-4): Just browsing, no timeline, refused contact info

TOOL USAGE:
- Call log_lead whenever you learn the lead's name or new qualifying info. Update it as you learn more.
- Call notify_agent for hot leads, escalations, or callback requests.
- Call book_appointment when the lead agrees to schedule.
- Call search_listings when the lead asks about available properties.

CRITICAL RULES:
1. NEVER fabricate information
2. NEVER provide legal/tax/mortgage advice
3. NEVER disparage competitors
4. NEVER pressure or manipulate
5. NEVER ask more than ONE question per message
6. ALWAYS try to capture name + one contact method
7. ALWAYS attempt to book at least once per conversation
8. ALWAYS hand off immediately if lead is frustrated

{custom_instructions}"""


def build_system_prompt(client: ClientRow) -> str:
    """Build the system prompt with client-specific data."""
    return SYSTEM_PROMPT_TEMPLATE.format(
        agent_name=client.agent_name,
        agent_type=client.agent_type,
        brokerage_name=client.brokerage_name or "their brokerage",
        service_area=client.service_area,
        bot_name=client.bot_name,
        custom_instructions=client.custom_instructions or "",
    )


async def run_agent(
    client: ClientRow,
    conversation_id: str,
    user_message: str,
) -> str:
    """Process a user message through the AI agent and return the assistant's text reply.

    Steps:
    1. Load conversation history from DB
    2. Append the new user message
    3. Call Claude API with tools
    4. Process any tool calls (loop until we get a text response)
    5. Save all messages to DB
    6. Return the final text
    """
    # Save user message to DB
    save_message(conversation_id, "user", user_message)

    # Load full history
    messages = load_message_history(conversation_id)

    system_prompt = build_system_prompt(client)
    api_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    for _round in range(MAX_TOOL_ROUNDS):
        try:
            response = api_client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                system=system_prompt,
                messages=messages,
                tools=TOOLS,
            )
        except anthropic.APIError as e:
            logger.exception("Claude API error")
            fallback = (
                "I'm having a little trouble right now — but don't worry, "
                f"{client.agent_name}'s team will get back to you shortly!"
            )
            save_message(conversation_id, "assistant", fallback)
            return fallback

        # Extract text and tool_use blocks from response
        text_parts: list[str] = []
        tool_use_blocks: list[dict[str, Any]] = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_use_blocks.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        assistant_text = "\n".join(text_parts).strip()

        if response.stop_reason == "tool_use" and tool_use_blocks:
            # Save the assistant message with tool_use metadata
            save_message(
                conversation_id,
                "assistant",
                assistant_text or "",
                metadata={"tool_use_blocks": tool_use_blocks},
            )

            # Build assistant content blocks for the API
            assistant_content: list[dict] = []
            if assistant_text:
                assistant_content.append({"type": "text", "text": assistant_text})
            for tb in tool_use_blocks:
                assistant_content.append({
                    "type": "tool_use",
                    "id": tb["id"],
                    "name": tb["name"],
                    "input": tb["input"],
                })

            # Update messages for next API call
            messages.append({"role": "assistant", "content": assistant_content})

            # Execute each tool and collect results
            tool_results: list[dict] = []
            for tb in tool_use_blocks:
                result_str = await handle_tool_call(
                    tb["name"], tb["input"], client, conversation_id
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tb["id"],
                    "content": result_str,
                })
                # Save tool result to DB
                save_message(
                    conversation_id,
                    "tool_result",
                    result_str,
                    metadata={"tool_use_id": tb["id"], "tool_name": tb["name"]},
                )

            messages.append({"role": "user", "content": tool_results})
            # Loop to get the next response from Claude
            continue

        # No tool use — we have the final text response
        if assistant_text:
            save_message(conversation_id, "assistant", assistant_text)
        else:
            # Edge case: empty response
            assistant_text = f"Is there anything else I can help you with about the {client.service_area} market?"
            save_message(conversation_id, "assistant", assistant_text)

        return assistant_text

    # Exceeded max tool rounds — return whatever text we have
    fallback = assistant_text or "Let me connect you with the team directly. How can we reach you?"
    save_message(conversation_id, "assistant", fallback)
    return fallback
