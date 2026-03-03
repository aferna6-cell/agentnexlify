"""Claude tool-use schema definitions for the real estate chatbot."""

from __future__ import annotations

TOOLS: list[dict] = [
    {
        "name": "book_appointment",
        "description": (
            "Book a showing, consultation call, or listing appointment for the lead "
            "with the real estate agent. Use this when the lead agrees to schedule a "
            "meeting. If Calendly is configured the booking is created automatically; "
            "otherwise the agent is notified with the details."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_name": {
                    "type": "string",
                    "description": "Full name of the lead.",
                },
                "lead_email": {
                    "type": "string",
                    "description": "Lead's email address.",
                },
                "lead_phone": {
                    "type": "string",
                    "description": "Lead's phone number.",
                },
                "preferred_date": {
                    "type": "string",
                    "description": "Preferred date for the appointment (ISO 8601 or natural language).",
                },
                "preferred_time": {
                    "type": "string",
                    "description": "Preferred time for the appointment.",
                },
                "appointment_type": {
                    "type": "string",
                    "enum": ["showing", "consultation_call", "listing_appointment"],
                    "description": "Type of appointment to book.",
                },
            },
            "required": ["lead_name", "appointment_type"],
        },
    },
    {
        "name": "search_listings",
        "description": (
            "Search for property listings matching the lead's criteria. "
            "Use this when the lead asks about available properties."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City, neighborhood, or ZIP code.",
                },
                "min_price": {
                    "type": "integer",
                    "description": "Minimum price in dollars.",
                },
                "max_price": {
                    "type": "integer",
                    "description": "Maximum price in dollars.",
                },
                "bedrooms": {
                    "type": "integer",
                    "description": "Minimum number of bedrooms.",
                },
                "bathrooms": {
                    "type": "integer",
                    "description": "Minimum number of bathrooms.",
                },
                "property_type": {
                    "type": "string",
                    "description": "Property type (house, condo, townhouse, land, etc.).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "log_lead",
        "description": (
            "Save or update lead information collected during the conversation. "
            "Call this whenever you've gathered new info about the lead "
            "(at minimum a name). Call it multiple times as you learn more."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Lead's full name."},
                "email": {"type": "string", "description": "Lead's email."},
                "phone": {"type": "string", "description": "Lead's phone number."},
                "lead_type": {
                    "type": "string",
                    "enum": ["buyer", "seller", "both", "investor", "unknown"],
                    "description": "Type of lead.",
                },
                "timeline": {
                    "type": "string",
                    "description": "When they want to buy/sell (e.g. '1-3 months').",
                },
                "budget": {
                    "type": "string",
                    "description": "Budget or price range.",
                },
                "pre_approved": {
                    "type": "boolean",
                    "description": "Whether the lead has mortgage pre-approval.",
                },
                "areas_of_interest": {
                    "type": "string",
                    "description": "Neighborhoods or areas they're interested in.",
                },
                "must_haves": {
                    "type": "string",
                    "description": "Must-have features (e.g. 'pool, 3+ bedrooms').",
                },
                "lead_score": {
                    "type": "integer",
                    "description": "Lead score from 1 (cold) to 10 (hot).",
                },
                "lead_temperature": {
                    "type": "string",
                    "enum": ["hot", "warm", "cold"],
                    "description": "Lead temperature category.",
                },
                "conversation_summary": {
                    "type": "string",
                    "description": "Brief summary of the conversation so far.",
                },
                "next_steps": {
                    "type": "string",
                    "description": "Recommended next steps for the agent.",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "notify_agent",
        "description": (
            "Send an urgent notification to the real estate agent. "
            "Use for hot leads, escalations (frustrated lead wants a human), "
            "or when a callback is requested."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "urgency": {
                    "type": "string",
                    "enum": ["hot_lead", "escalation", "callback_requested"],
                    "description": "Urgency level of the notification.",
                },
                "lead_name": {
                    "type": "string",
                    "description": "Name of the lead.",
                },
                "lead_phone": {
                    "type": "string",
                    "description": "Lead's phone number for callback.",
                },
                "message": {
                    "type": "string",
                    "description": "Message body for the notification.",
                },
            },
            "required": ["urgency", "message"],
        },
    },
]
