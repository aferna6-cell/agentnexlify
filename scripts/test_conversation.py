#!/usr/bin/env python3
"""CLI tool to test the AgentNexLiFy agent in the terminal.

Usage:
    python -m scripts.test_conversation --api-key <WIDGET_API_KEY>
    python -m scripts.test_conversation --api-key <WIDGET_API_KEY> --base-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import uuid

import httpx


def main():
    parser = argparse.ArgumentParser(description="Test AgentNexLiFy chatbot")
    parser.add_argument("--api-key", required=True, help="Widget API key")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    args = parser.parse_args()

    session_id = f"test_{uuid.uuid4().hex[:12]}"
    base = args.base_url.rstrip("/")

    print("AgentNexLiFy — Conversation Test")
    print("=" * 50)
    print(f"  Session: {session_id}")
    print(f"  API:     {base}")
    print()
    print('Type your messages below. Type "quit" to exit.')
    print("-" * 50)
    print()

    client = httpx.Client(timeout=60.0)

    # Get config
    try:
        config = client.get(f"{base}/api/chat/config", params={"client_api_key": args.api_key})
        config.raise_for_status()
        cfg = config.json()
        bot_name = cfg.get("bot_name", "Aria")
        agent_name = cfg.get("agent_name", "Agent")
        print(f"  [{bot_name} for {agent_name}]")
        print()
    except Exception as e:
        print(f"  Warning: couldn't fetch config: {e}")
        bot_name = "Bot"
        print()

    # Send initial greeting (empty message triggers greeting)
    try:
        resp = client.post(
            f"{base}/api/chat/message",
            json={
                "client_api_key": args.api_key,
                "session_id": session_id,
                "message": "hi",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        print(f"  {bot_name}: {data['reply']}")
        print()
    except Exception as e:
        print(f"  Error getting greeting: {e}")
        print()

    while True:
        try:
            user_input = input("  You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("\nGoodbye!")
            break

        try:
            resp = client.post(
                f"{base}/api/chat/message",
                json={
                    "client_api_key": args.api_key,
                    "session_id": session_id,
                    "message": user_input,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            print(f"  {bot_name}: {data['reply']}")
            print()
        except httpx.HTTPStatusError as e:
            print(f"  Error ({e.response.status_code}): {e.response.text}")
            print()
        except Exception as e:
            print(f"  Error: {e}")
            print()


if __name__ == "__main__":
    main()
