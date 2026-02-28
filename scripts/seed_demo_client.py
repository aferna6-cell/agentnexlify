#!/usr/bin/env python3
"""Seed a demo real estate agent client for testing.

Usage:
    python -m scripts.seed_demo_client
"""

from __future__ import annotations

import secrets
import sys

from dotenv import load_dotenv

load_dotenv()

from backend.models.database import get_supabase  # noqa: E402


def main():
    db = get_supabase()

    widget_api_key = f"anx_{secrets.token_urlsafe(32)}"

    client_data = {
        "agent_name": "Sarah Mitchell",
        "agent_type": "agent",
        "brokerage_name": "Keller Williams Realty",
        "service_area": "Austin, TX",
        "bot_name": "Aria",
        "calendly_link": None,
        "notification_email": None,
        "notification_phone": None,
        "widget_api_key": widget_api_key,
        "active": True,
        "custom_instructions": "",
        "brand_color": "#6cff5c",
    }

    try:
        result = db.table("clients").insert(client_data).execute()
        client = result.data[0]
    except Exception as e:
        print(f"Error creating demo client: {e}")
        sys.exit(1)

    print("AgentNexLiFy — Demo Client Seeded")
    print("=" * 50)
    print()
    print(f"  Agent:     {client['agent_name']}")
    print(f"  Brokerage: {client['brokerage_name']}")
    print(f"  Area:      {client['service_area']}")
    print(f"  Bot Name:  {client['bot_name']}")
    print(f"  Client ID: {client['id']}")
    print()
    print(f"  Widget API Key: {widget_api_key}")
    print()
    print("  Embed code (add to any HTML page):")
    print()
    print(f'  <script src="http://localhost:8000/widget/agentnexlify-widget.js"')
    print(f'    data-api-key="{widget_api_key}"></script>')
    print()
    print("  For the test script:")
    print(f"  python -m scripts.test_conversation --api-key {widget_api_key}")


if __name__ == "__main__":
    main()
