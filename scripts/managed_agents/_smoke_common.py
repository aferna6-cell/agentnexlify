"""Shared helpers for the new managed-agent smoke tests.

Each smoke script (`support_smoke`, `extractor_smoke`, `researcher_smoke`,
`field_monitor_smoke`, `analyst_smoke`) runs a real session against its
target agent. The lifecycle is identical: resolve handle, open stream
BEFORE sending kickoff, collect assistant text blocks, assert the
session_id contract, print a summary.

This helper exists so each script stays ~40 lines and the session-id
regression guard (91651b0) is enforced in one place.

NOT a smoke script itself — the leading underscore and the absence of
a `main()` entry point keep it out of `python -m scripts.managed_agents.*`
discoverability.
"""

import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.services.managed_agents import (  # noqa: E402
    ManagedAgentsClient,
    ManagedAgentsError,
    SessionTerminalState,
)
from backend.services.managed_agents_registry import (  # noqa: E402
    ManagedAgentHandle,
    ManagedAgentNotConfigured,
)


@dataclass
class SmokeResult:
    """Everything a smoke validator needs to inspect a completed run."""

    session_id: str
    event_count: int
    transcript: list[dict[str, Any]] = field(default_factory=list)
    reply_text: str = ""
    terminal: SessionTerminalState | None = None
    elapsed_s: float = 0.0


Validator = Callable[[SmokeResult], str | None]
"""A validator returns None on pass, or an error string on fail."""


def _extract_text_blocks(content: list[Any] | None) -> str:
    if not content:
        return ""
    parts: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)


class SessionRunError(RuntimeError):
    """Raised by run_agent_session on transport / configuration failures."""


def run_agent_session(
    *,
    handle_factory: Callable[[], ManagedAgentHandle],
    agent_label: str,
    kickoff_prompt: str,
    session_title: str,
    metadata: dict[str, Any],
    logger_name: str,
    max_events_logged: int = 20,
) -> SmokeResult:
    """Run one session end-to-end and return the captured result.

    Raises SessionRunError on unrecoverable transport or configuration
    failures. Smoke scripts wrap this in `run_smoke_session`; runner
    scripts call it directly so they can write the reply to disk
    without pass/fail semantics.
    """
    logger = logging.getLogger(logger_name)

    try:
        handle = handle_factory()
    except ManagedAgentNotConfigured as exc:
        raise SessionRunError(
            f"{agent_label} not configured: {exc}. Run "
            "`python -m scripts.managed_agents.provision` first."
        ) from exc

    try:
        client = ManagedAgentsClient()
    except ManagedAgentsError as exc:
        raise SessionRunError(f"client init failed: {exc}") from exc

    logger.info(
        "creating session: agent=%s env=%s label=%s",
        handle.agent_id,
        handle.environment_id,
        agent_label,
    )

    try:
        session = client.create_session(
            agent_id=handle.agent_id,
            environment_id=handle.environment_id,
            title=session_title,
            metadata=metadata,
        )
    except ManagedAgentsError as exc:
        raise SessionRunError(
            f"create_session failed: {exc} "
            f"(status={exc.status}, request_id={exc.request_id}, type={exc.error_type})"
        ) from exc

    session_id = session["id"]
    logger.info("session created: %s", session_id)

    # Contract: stream BEFORE sending the first message. Regression guard
    # for the 91651b0 bug — flipping these lines drops events and breaks
    # the terminal state machine.
    started = time.monotonic()
    try:
        stream = client.stream_events(session_id)
        client.send_user_message(session_id, kickoff_prompt)
    except ManagedAgentsError as exc:
        raise SessionRunError(f"stream/send failed: {exc}") from exc

    logger.info("kickoff message sent; streaming events...")

    transcript: list[dict[str, Any]] = []
    assistant_chunks: list[str] = []
    terminal = SessionTerminalState(
        terminated=False,
        stop_reason_type=None,
        last_event_id=None,
        session_id=session_id,
    )
    event_count = 0

    try:
        for event in stream:
            event_count += 1
            event_type = event.get("type", "")
            if event_count <= max_events_logged:
                logger.info("  event %d: type=%s", event_count, event_type)

            if event_type == "agent.message":
                blocks = event.get("content") or []
                transcript.append(
                    {"role": "assistant", "content": blocks, "id": event.get("id")}
                )
                assistant_chunks.append(_extract_text_blocks(blocks))
                continue

            if event_type == "session.status_terminated":
                terminal = SessionTerminalState(
                    terminated=True,
                    stop_reason_type=None,
                    last_event_id=event.get("id"),
                    session_id=session_id,
                )
                break

            if event_type == "session.status_idle":
                stop_reason = event.get("stop_reason") or {}
                stop_type = (
                    stop_reason.get("type")
                    if isinstance(stop_reason, dict)
                    else None
                )
                if stop_type != "requires_action":
                    terminal = SessionTerminalState(
                        terminated=False,
                        stop_reason_type=stop_type,
                        last_event_id=event.get("id"),
                        session_id=session_id,
                    )
                    break
    except ManagedAgentsError as exc:
        raise SessionRunError(
            f"stream_events failed: {exc} "
            f"(status={exc.status}, request_id={exc.request_id}, type={exc.error_type})"
        ) from exc

    elapsed = time.monotonic() - started
    reply_text = "\n".join(chunk for chunk in assistant_chunks if chunk).strip()
    return SmokeResult(
        session_id=session_id,
        event_count=event_count,
        transcript=transcript,
        reply_text=reply_text,
        terminal=terminal,
        elapsed_s=elapsed,
    )


def run_smoke_session(
    *,
    handle_factory: Callable[[], ManagedAgentHandle],
    agent_label: str,
    kickoff_prompt: str,
    session_title: str,
    metadata: dict[str, Any],
    logger_name: str,
    validator: Validator | None = None,
    max_events_logged: int = 20,
) -> int:
    """Run one smoke session end-to-end.

    Returns a process exit code:
        0 — session completed, transcript non-empty, validator passed
        1 — transport / credential / configuration failure
        2 — session streamed but smoke assertions failed
    """
    logger = logging.getLogger(logger_name)

    try:
        result = run_agent_session(
            handle_factory=handle_factory,
            agent_label=agent_label,
            kickoff_prompt=kickoff_prompt,
            session_title=session_title,
            metadata=metadata,
            logger_name=logger_name,
            max_events_logged=max_events_logged,
        )
    except SessionRunError as exc:
        logger.error("%s smoke aborted: %s", agent_label, exc)
        return 1

    terminal = result.terminal
    session_id = result.session_id
    assert terminal is not None  # run_agent_session always sets it

    print()
    print(f"{agent_label} smoke result:")
    print(f"  session_id:       {session_id}")
    print(f"  events streamed:  {result.event_count}")
    print(f"  transcript turns: {len(result.transcript)}")
    print(f"  terminated:       {terminal.terminated}")
    print(f"  stop_reason:      {terminal.stop_reason_type}")
    print(f"  elapsed:          {result.elapsed_s:.1f}s")
    if result.reply_text:
        preview = result.reply_text.replace("\n", " ")[:300]
        print(f"  reply preview:    {preview!r}")

    if not result.transcript:
        logger.error("session completed but produced no assistant messages")
        return 2

    # Regression guard (91651b0): SessionTerminalState.session_id must
    # equal the id returned by create_session, and must differ from any
    # last_event_id.
    if terminal.session_id != session_id:
        logger.error(
            "SessionTerminalState.session_id drift: terminal=%r created=%r",
            terminal.session_id,
            session_id,
        )
        return 2
    if terminal.last_event_id and terminal.last_event_id == terminal.session_id:
        logger.error("session_id equals last_event_id — contract broken")
        return 2

    if validator is not None:
        problem = validator(result)
        if problem:
            logger.error("%s smoke validator failed: %s", agent_label, problem)
            return 2

    print()
    print(f"{agent_label} smoke PASSED.")
    return 0
