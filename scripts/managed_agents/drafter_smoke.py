"""End-to-end smoke test for the Document Drafter managed agent.

Runs a real session against the `document_drafter` agent with a
minimal test quote, streams events, and inspects everything the agent
does so we can see:

  1. Which tools it actually calls (docx / xlsx / pdf skills vs bash)
  2. How file IDs are surfaced — via the agent's JSON reply, via a
     session event, or not at all
  3. Whether the file retrieval path via `get_file_content` works

This script is READ-WRITE against the Managed Agents API (creates a
session, spends container runtime + Opus tokens). Expect ~$0.10-0.50
per run depending on how thorough the agent is.

Usage:
    python -m scripts.managed_agents.drafter_smoke
    python -m scripts.managed_agents.drafter_smoke --save-events out.jsonl
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from pprint import pformat

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.services.managed_agents import (  # noqa: E402
    ManagedAgentsClient,
    ManagedAgentsError,
)
from backend.services.managed_agents_registry import (  # noqa: E402
    ManagedAgentNotConfigured,
    document_drafter,
)

logger = logging.getLogger("managed_agents.drafter_smoke")

_TEST_PROMPT = """\
Draft a quote as a real DOCX file. Automated integration test.

Business:
  - Name: AgentNexLiFy Smoke Test LLC
  - Phone: +1-555-0100

Customer:
  - Name: Smoke Test Customer
  - Email: test@example.com

Line items:
  1. Driveway pressure wash — qty 1 @ 300
  2. Deck treatment — qty 1 @ 150

Follow your system prompt exactly. Generate the docx, export with
`base64 -w0`, and return ONLY the JSON reply with keys file_name,
file_type, total, summary, content_base64. Keep the document minimal —
this is a test.
"""


def _summarize_event(event: dict) -> str:
    t = event.get("type", "?")
    extras = []
    if t == "agent.tool_use":
        name = event.get("name") or event.get("tool_name") or "?"
        extras.append(f"tool={name}")
        inp = event.get("input") or {}
        if isinstance(inp, dict):
            for k in ("command", "path", "file_path", "filename"):
                if k in inp:
                    extras.append(f"{k}={str(inp[k])[:80]}")
                    break
    elif t == "agent.tool_result":
        extras.append(f"id={event.get('tool_use_id', '?')}")
        content = event.get("content") or []
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        extras.append(f"text={block.get('text', '')[:80]!r}")
                    elif block.get("type") == "file":
                        extras.append(f"FILE_BLOCK={block}")
                        break
    elif t == "session.status_idle":
        stop = (event.get("stop_reason") or {}).get("type")
        extras.append(f"stop={stop}")
    elif t == "session.error":
        err = event.get("error") or {}
        extras.append(f"err={err.get('message', '?')}")
    return f"{t} " + " ".join(extras)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--save-events", help="Write full event stream as JSONL")
    args = parser.parse_args()

    try:
        handle = document_drafter()
    except ManagedAgentNotConfigured as exc:
        logger.error("document_drafter not configured: %s", exc)
        return 1

    client = ManagedAgentsClient()

    logger.info(
        "creating session agent=%s env=%s",
        handle.agent_id, handle.environment_id,
    )
    try:
        session = client.create_session(
            agent_id=handle.agent_id,
            environment_id=handle.environment_id,
            title="drafter smoke test",
            metadata={"flow": "drafter_smoke"},
        )
    except ManagedAgentsError as exc:
        logger.error("create_session failed: %s", exc)
        return 1

    session_id = session["id"]
    logger.info("session_id=%s", session_id)

    stream = client.stream_events(session_id)
    client.send_user_message(session_id, _TEST_PROMPT)

    events_log = None
    if args.save_events:
        events_log = open(args.save_events, "w", encoding="utf-8")

    discovered_file_ids: list[str] = []
    final_text_chunks: list[str] = []

    try:
        for event in stream:
            if events_log:
                events_log.write(json.dumps(event) + "\n")
                events_log.flush()

            summary = _summarize_event(event)
            logger.info("  %s", summary)

            # Hunt for file IDs wherever they might show up.
            # Pattern A: session.file_created (hypothetical event name)
            if event.get("type", "").startswith("session.file"):
                fid = event.get("file_id") or (event.get("file") or {}).get("id")
                if fid:
                    discovered_file_ids.append(fid)
                    logger.info("    >>> captured file_id from session event: %s", fid)

            # Pattern B: tool_result content carries a file block
            if event.get("type") == "agent.tool_result":
                for block in event.get("content") or []:
                    if isinstance(block, dict):
                        fid = block.get("file_id") or (block.get("source") or {}).get("file_id")
                        if fid:
                            discovered_file_ids.append(fid)
                            logger.info(
                                "    >>> captured file_id from tool_result: %s",
                                fid,
                            )

            # Pattern C: agent.message text
            if event.get("type") == "agent.message":
                for block in event.get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "text":
                        final_text_chunks.append(block.get("text", ""))

            if event.get("type") == "session.status_terminated":
                break
            if event.get("type") == "session.status_idle":
                stop = (event.get("stop_reason") or {}).get("type")
                if stop != "requires_action":
                    break
    finally:
        if events_log:
            events_log.close()

    final_text = "\n".join(final_text_chunks)
    logger.info("=" * 60)
    logger.info("FINAL TEXT (first 1000 chars):")
    logger.info(final_text[:1000])
    logger.info("=" * 60)

    logger.info("Discovered file IDs during stream: %s", discovered_file_ids)

    # Try to parse file_id from final JSON reply (Plan B's contract).
    import re
    parsed = None
    match = re.search(r"\{.*\}", final_text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    if not parsed:
        logger.error("Could not parse JSON from agent reply.")
        return 2

    # Redact the base64 payload so the log summary is readable.
    redacted = {
        k: (f"<{len(v)} chars>" if k == "content_base64" and isinstance(v, str) else v)
        for k, v in parsed.items()
    }
    logger.info("Parsed final JSON (redacted): %s", pformat(redacted))

    b64 = parsed.get("content_base64")
    if not isinstance(b64, str) or not b64:
        logger.error("Agent reply did not include content_base64.")
        return 2

    import base64
    try:
        raw = base64.b64decode(b64, validate=True)
    except Exception as exc:
        logger.error("content_base64 failed to decode: %s", exc)
        return 2

    logger.info("Decoded %d bytes", len(raw))

    # DOCX magic: PK\x03\x04 (ZIP header)
    if parsed.get("file_type") == "docx":
        if not raw.startswith(b"PK\x03\x04"):
            logger.error(
                "Decoded bytes do not look like a DOCX (missing PK header). First 32 bytes: %r",
                raw[:32],
            )
            return 2
        logger.info("DOCX magic header verified (PK\\x03\\x04)")

    if args.save_events:
        file_name = parsed.get("file_name") or "output.bin"
        out = Path(args.save_events).with_name(Path(args.save_events).stem + "." + file_name)
        out.write_bytes(raw)
        logger.info("wrote decoded file to %s", out)

    print()
    print("Drafter smoke complete.")
    print(f"  session_id: {session_id}")
    print(f"  file_name:  {parsed.get('file_name')}")
    print(f"  file_type:  {parsed.get('file_type')}")
    print(f"  total:      {parsed.get('total')}")
    print(f"  size:       {len(raw)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
