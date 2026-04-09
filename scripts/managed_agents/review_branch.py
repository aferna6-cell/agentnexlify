"""Run the Codebase Reviewer managed agent against a branch of this repo.

Usage:

    # Review the current branch of origin/agentnexlify:
    GITHUB_TOKEN=ghp_... python -m scripts.managed_agents.review_branch \
        --branch my-feature-branch

    # Review a specific GitHub repo instead (defaults to agentnexlify):
    GITHUB_TOKEN=ghp_... python -m scripts.managed_agents.review_branch \
        --repo https://github.com/aferna6-cell/agentnexlify --branch main

    # Ask a targeted question instead of the default "review this branch":
    GITHUB_TOKEN=ghp_... python -m scripts.managed_agents.review_branch \
        --branch main \
        --prompt "Focus on backend/routers/widget_chat.py — audit tenant isolation."

Requires:
    - ANTHROPIC_API_KEY in .env
    - GITHUB_TOKEN environment variable (PAT with Contents:Read on the repo)
    - CODEBASE_REVIEWER_AGENT_ID + MANAGED_AGENTS_ENVIRONMENT_ID populated
      (see scripts/managed_agents/provision.py)
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.services.managed_agents import (  # noqa: E402
    ManagedAgentsClient,
    ManagedAgentsError,
)
from backend.services.managed_agents_registry import (  # noqa: E402
    ManagedAgentNotConfigured,
    codebase_reviewer,
)

logger = logging.getLogger("managed_agents.review_branch")

DEFAULT_REPO_URL = "https://github.com/aferna6-cell/agentnexlify"
DEFAULT_MOUNT_PATH = "/workspace/agentnexlify"
DEFAULT_PROMPT = (
    "Review the currently checked-out branch of the mounted repo at "
    f"{DEFAULT_MOUNT_PATH}. Use `git log -n 20` to see the recent commit "
    "history, `git diff main...HEAD -- backend frontend widget` to see "
    "what has changed, and follow the system prompt's checklist.\n\n"
    "Report your findings in the structured format described in your "
    "system prompt."
)


def _render_block(block: dict) -> str:
    if block.get("type") == "text":
        return block.get("text", "")
    return ""


def _render_content(content: list) -> str:
    return "".join(_render_block(b) for b in content or [])


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    parser = argparse.ArgumentParser(description=__doc__ or "")
    parser.add_argument("--repo", default=DEFAULT_REPO_URL)
    parser.add_argument("--branch", default="main")
    parser.add_argument("--mount-path", default=DEFAULT_MOUNT_PATH)
    parser.add_argument("--prompt", default=None)
    parser.add_argument(
        "--save-events",
        help="Optional path to write the full event stream as JSONL.",
    )
    args = parser.parse_args()

    github_token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not github_token:
        raise SystemExit(
            "GITHUB_TOKEN is required — export a PAT with `Contents: Read` "
            "on the target repo before running this script."
        )

    try:
        handle = codebase_reviewer()
    except ManagedAgentNotConfigured as exc:
        raise SystemExit(
            f"{exc}\n\n"
            "Run `python -m scripts.managed_agents.provision` first."
        )

    client = ManagedAgentsClient()

    logger.info(
        "creating session agent=%s env=%s repo=%s branch=%s",
        handle.agent_id, handle.environment_id, args.repo, args.branch,
    )
    try:
        session = client.create_session(
            agent_id=handle.agent_id,
            environment_id=handle.environment_id,
            title=f"codebase-review {args.branch}",
            resources=[
                {
                    "type": "github_repository",
                    "url": args.repo,
                    "authorization_token": github_token,
                    "mount_path": args.mount_path,
                    "checkout": {"type": "branch", "name": args.branch},
                }
            ],
            metadata={"flow": "codebase_review", "branch": args.branch},
        )
    except ManagedAgentsError as exc:
        raise SystemExit(f"create_session failed: {exc}")

    session_id = session["id"]
    logger.info("session created: %s", session_id)

    # Stream-first: open the SSE stream before sending the kickoff message.
    try:
        stream = client.stream_events(session_id)
    except ManagedAgentsError as exc:
        raise SystemExit(f"stream_events failed: {exc}")

    client.send_user_message(session_id, args.prompt or DEFAULT_PROMPT)

    events_log = (
        open(args.save_events, "w", encoding="utf-8") if args.save_events else None
    )

    print()
    print(f"=== Codebase Reviewer session {session_id} ===")
    print()

    try:
        for event in stream:
            if events_log:
                events_log.write(json.dumps(event) + "\n")
                events_log.flush()

            event_type = event.get("type", "")
            if event_type == "agent.message":
                text = _render_content(event.get("content") or [])
                if text:
                    print(text, end="", flush=True)
            elif event_type == "span.model_request_end":
                usage = event.get("model_usage") or {}
                if usage:
                    logger.debug("model usage: %s", usage)
            elif event_type == "agent.tool_use":
                tool = event.get("tool_name") or event.get("name") or "?"
                logger.info("tool_use: %s", tool)
            elif event_type == "session.status_terminated":
                print()
                logger.info("session terminated")
                break
            elif event_type == "session.status_idle":
                stop = event.get("stop_reason") or {}
                stop_type = (
                    stop.get("type") if isinstance(stop, dict) else None
                )
                if stop_type != "requires_action":
                    print()
                    logger.info("session idle (stop_reason=%s)", stop_type)
                    break
    except ManagedAgentsError as exc:
        raise SystemExit(f"stream error: {exc}")
    finally:
        if events_log:
            events_log.close()

    print()
    print(f"=== Session {session_id} complete ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
