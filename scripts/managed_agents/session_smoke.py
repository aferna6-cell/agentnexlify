"""End-to-end session smoke test for the Claude Managed Agents integration.

Creates a real session against the Lead Qualifier agent, sends a single
test prompt, streams events until the session goes idle with a terminal
stop reason, and asserts that we received at least one assistant message.

This is the session-level counterpart to `smoke.py` (which only hits
read-only list endpoints). Running this script:
  1. Costs a small amount of model + container runtime (Lead Qualifier
     is Sonnet with minimal tools, expect a few cents per run).
  2. Exercises create_session, send_user_message, and stream_events —
     the three endpoints that `smoke.py` does NOT cover.
  3. Requires that provision.py has already been run (so the
     `.env.managed_agents` file contains LEAD_QUALIFIER_AGENT_ID +
     MANAGED_AGENTS_ENVIRONMENT_ID).

Usage:

    python -m scripts.managed_agents.session_smoke

Exit codes:
    0 — session completed with at least one assistant message
    1 — transport, credential, or configuration failure
    2 — session streamed but no assistant message was received
"""

import logging
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.services.managed_agents import (  # noqa: E402
    ManagedAgentsClient,
    ManagedAgentsError,
    SessionTerminalState,
)
from backend.services.managed_agents_registry import (  # noqa: E402
    ManagedAgentNotConfigured,
    lead_qualifier,
)

logger = logging.getLogger("managed_agents.session_smoke")

_TEST_PROMPT = (
    "Qualify this inbound lead:\n"
    "\n"
    "- Lead name: Smoke Test Lead\n"
    "- Email: smoke-test@example.com\n"
    "- Stated interest: managed-agents integration smoke test\n"
    "- Tenant business: AgentNexLiFy (automation SaaS)\n"
    "\n"
    "Return the structured JSON summary described in your system prompt. "
    "This is an automated integration test — keep the response short."
)


def _run_session(client: ManagedAgentsClient, *, agent_id: str, environment_id: str) -> int:
    logger.info("creating session against agent %s in env %s", agent_id, environment_id)
    session = client.create_session(
        agent_id=agent_id,
        environment_id=environment_id,
        title="managed-agents session smoke",
        metadata={"tenant_id": "smoke_test", "flow": "session_smoke"},
    )
    session_id = session["id"]
    logger.info("session created: %s", session_id)

    stream = client.stream_events(session_id)
    client.send_user_message(session_id, _TEST_PROMPT)
    logger.info("kickoff message sent; streaming events...")

    transcript: list[dict] = []
    terminal = SessionTerminalState(terminated=False, stop_reason_type=None, last_event_id=None)
    event_count = 0

    for event in stream:
        event_count += 1
        event_type = event.get("type", "")
        if event_count <= 20:
            logger.info("  event %d: type=%s", event_count, event_type)
        if event_type == "agent.message":
            transcript.append(
                {
                    "role": "assistant",
                    "content": event.get("content", []),
                    "id": event.get("id"),
                }
            )
        elif event_type == "session.status_terminated":
            terminal = SessionTerminalState(
                terminated=True,
                stop_reason_type=None,
                last_event_id=event.get("id"),
            )
            break
        elif event_type == "session.status_idle":
            stop_reason = event.get("stop_reason") or {}
            stop_type = stop_reason.get("type") if isinstance(stop_reason, dict) else None
            if stop_type != "requires_action":
                terminal = SessionTerminalState(
                    terminated=False,
                    stop_reason_type=stop_type,
                    last_event_id=event.get("id"),
                )
                break

    print()
    print("Session smoke result:")
    print(f"  session_id:       {session_id}")
    print(f"  events streamed:  {event_count}")
    print(f"  transcript turns: {len(transcript)}")
    print(f"  terminated:       {terminal.terminated}")
    print(f"  stop_reason:      {terminal.stop_reason_type}")

    if transcript:
        first = transcript[0]
        blocks = first.get("content") or []
        text_chunks = [b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text"]
        preview = (" ".join(text_chunks))[:300]
        print(f"  first reply:      {preview!r}")

    if not transcript:
        logger.error("session completed but produced no assistant messages")
        return 2

    print()
    print("Session smoke PASSED.")
    return 0


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    try:
        handle = lead_qualifier()
    except ManagedAgentNotConfigured as exc:
        logger.error("lead_qualifier not configured: %s", exc)
        logger.error("run `python -m scripts.managed_agents.provision` first")
        return 1

    try:
        client = ManagedAgentsClient()
    except ManagedAgentsError as exc:
        logger.error("client init failed: %s", exc)
        return 1

    try:
        return _run_session(
            client,
            agent_id=handle.agent_id,
            environment_id=handle.environment_id,
        )
    except ManagedAgentsError as exc:
        logger.error(
            "session smoke failed: %s (status=%s, request_id=%s, type=%s)",
            exc,
            exc.status,
            exc.request_id,
            exc.error_type,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
