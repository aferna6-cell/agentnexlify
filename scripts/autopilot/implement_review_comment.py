"""CLI runner for applying review comments on autopilot pull requests.

Reads the GitHub Actions review-comment payload, asks Claude Sonnet to prepare
a focused implementation brief, applies that brief through Codex, runs the
repo pre-commit gate, then commits, pushes, and replies to the review thread.

Usage:
    python scripts/autopilot/implement_review_comment.py

Exit codes:
    0 - review comment addressed
    1 - hard failure
    2 - no changes made or max review iterations reached
"""

import base64
import json
import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.autopilot.classify_and_dispatch import (  # noqa: E402
    AUTOPILOT_AUTHOR_EMAIL,
    AUTOPILOT_AUTHOR_NAME,
    AutopilotError,
    TokenBudget,
)

REVIEW_MODEL = "claude-sonnet-4-6"
MAX_AUTOPILOT_REVIEW_COMMITS = 5

REVIEW_SYSTEM = (
    "A human reviewer left this comment on an autopilot pull request. "
    "Produce a focused implementation brief for Codex. Touch only the file "
    "and surrounding context unless the change requires edits elsewhere. "
    "Return concise Markdown with the requested change, constraints, and "
    "verification command. Do not include secrets or unrelated refactors."
)


@dataclass(frozen=True)
class ReviewEvent:
    """Normalized pull request review-comment webhook payload."""

    repository: str
    pr_number: int
    branch: str
    head_sha: str
    comment_id: int
    comment_body: str
    path: str
    line: int


def _tail(text: str, max_chars: int = 2000) -> str:
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _run(
    args: list[str],
    *,
    cwd: Path = _REPO_ROOT,
    input_text: str | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        args,
        cwd=str(cwd),
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and completed.returncode != 0:
        raise AutopilotError(
            "command failed "
            f"({args[0]} exit {completed.returncode})\n"
            f"stdout:\n{_tail(completed.stdout)}\n"
            f"stderr:\n{_tail(completed.stderr)}"
        )
    return completed


def _gh_json(args: list[str]) -> Any:
    completed = _run(["gh", *args])
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AutopilotError(f"gh returned invalid JSON for {' '.join(args)}") from exc


def _require_cli(name: str) -> None:
    if shutil.which(name) is None:
        raise AutopilotError(
            f"required CLI `{name}` was not found on PATH; review dispatch aborted"
        )


def _token_budget_from_env() -> TokenBudget:
    raw_limit = os.environ.get("AUTOPILOT_MAX_TOKENS_PER_RUN", "200000")
    try:
        max_tokens = int(raw_limit)
    except ValueError as exc:
        raise AutopilotError("autopilot token budget must be an integer") from exc
    return TokenBudget(max_tokens=max_tokens)


def _event_path() -> Path:
    raw_path = os.environ.get("GITHUB_EVENT_PATH")
    if not raw_path:
        raise AutopilotError("GitHub event payload path is not configured")
    return Path(raw_path)


def _load_event() -> ReviewEvent:
    try:
        payload = json.loads(_event_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AutopilotError("failed to read GitHub review-comment payload") from exc

    try:
        comment = payload["comment"]
        pull_request = payload["pull_request"]
        repository = payload["repository"]["full_name"]
        line = comment.get("line") or comment.get("original_line")
        if line is None:
            raise KeyError("line")
        return ReviewEvent(
            repository=str(repository),
            pr_number=int(pull_request["number"]),
            branch=str(pull_request["head"]["ref"]),
            head_sha=str(pull_request["head"]["sha"]),
            comment_id=int(comment["id"]),
            comment_body=str(comment.get("body") or ""),
            path=str(comment["path"]),
            line=int(line),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AutopilotError("payload is missing required review-comment fields") from exc


def _reply_to_comment(event: ReviewEvent, body: str) -> None:
    _run(
        [
            "gh",
            "api",
            "-X",
            "POST",
            f"repos/{event.repository}/pulls/{event.pr_number}/comments/{event.comment_id}/replies",
            "-f",
            f"body={body}",
        ]
    )


def _fetch_file_text(event: ReviewEvent) -> str:
    response = _gh_json(
        [
            "api",
            f"repos/{event.repository}/contents/{event.path}?ref={event.head_sha}",
        ]
    )
    encoded = str(response.get("content") or "")
    if not encoded:
        raise AutopilotError(f"file content was empty for {event.path}")
    return base64.b64decode(encoded).decode("utf-8")


def _surrounding_context(event: ReviewEvent) -> str:
    lines = _fetch_file_text(event).splitlines()
    start = max(event.line - 11, 0)
    end = min(event.line + 10, len(lines))
    numbered = []
    for index in range(start, end):
        marker = ">" if index + 1 == event.line else " "
        numbered.append(f"{marker} {index + 1:4d}: {lines[index]}")
    return "\n".join(numbered)


def _anthropic_text(response: Any) -> str:
    parts: list[str] = []
    for block in getattr(response, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(str(text))
    return "\n".join(parts).strip()


def _ask_sonnet_for_brief(
    event: ReviewEvent,
    context: str,
    *,
    budget: TokenBudget,
    logger: logging.Logger,
) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise AutopilotError("Anthropic API key is not configured for this runner")

    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=REVIEW_MODEL,
        max_tokens=1800,
        system=REVIEW_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Pull request #{event.pr_number}\n"
                    f"Branch: {event.branch}\n"
                    f"Review comment location: {event.path}:{event.line}\n\n"
                    f"Human review comment:\n{event.comment_body}\n\n"
                    f"Surrounding code context:\n```text\n{context}\n```"
                ),
            }
        ],
    )
    budget.add_response_usage(response)
    logger.info(
        "review handler used %d/%d Anthropic SDK tokens",
        budget.used_tokens,
        budget.max_tokens,
    )
    brief = _anthropic_text(response)
    if not brief:
        raise AutopilotError("Sonnet returned an empty implementation brief")
    return brief


def _write_prompt_file(event: ReviewEvent, brief: str, context: str) -> Path:
    prompt_dir = _REPO_ROOT / ".autopilot-prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompt_dir / f"review-comment-{event.comment_id}.md"
    prompt = f"""\
You are Codex running the AgentNexLiFy autopilot PR review handler.

Model routing target: {REVIEW_MODEL}.

Implement this human review comment on PR #{event.pr_number}.

File and line:
{event.path}:{event.line}

Human review comment:
{event.comment_body}

Sonnet implementation brief:
{brief}

Surrounding code context:
```text
{context}
```

Requirements:
- Apply the requested change directly.
- Keep edits narrowly scoped to the reviewed file unless the brief requires another file.
- Do not commit, push, or reply to GitHub; this script handles that.
- Do not hardcode secrets.
- Do not add future-annotations imports.
- Leave the repository ready for `bash scripts/hooks/pre-commit`.
"""
    prompt_path.write_text(prompt, encoding="utf-8")
    return prompt_path


def _run_codex(prompt_path: Path) -> None:
    _require_cli("codex")
    prompt_text = prompt_path.read_text(encoding="utf-8")
    _run(["codex", "exec", "--write", prompt_text])


def _configure_git_author() -> None:
    _run(["git", "config", "user.name", AUTOPILOT_AUTHOR_NAME])
    _run(["git", "config", "user.email", AUTOPILOT_AUTHOR_EMAIL])


def _autopilot_commit_count() -> int:
    completed = _run(
        ["git", "log", f"--author={AUTOPILOT_AUTHOR_NAME}", "--pretty=%H"],
        check=False,
    )
    if completed.returncode != 0:
        return 0
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    return len(lines)


def _run_pre_commit_gate() -> None:
    _run(["git", "add", "-A"])
    _run(["bash", "scripts/hooks/pre-commit"])


def _commit_and_push(event: ReviewEvent) -> str:
    _configure_git_author()
    _run_pre_commit_gate()
    _run(
        [
            "git",
            "commit",
            "-m",
            f"autopilot: address review comment on {event.path}:{event.line}",
        ]
    )
    _run(["git", "push", "origin", f"HEAD:{event.branch}"])
    return _run(["git", "rev-parse", "--short", "HEAD"]).stdout.strip()


def run(logger: logging.Logger) -> int:
    _require_cli("codex")
    event = _load_event()

    count = _autopilot_commit_count()
    if count >= MAX_AUTOPILOT_REVIEW_COMMITS:
        body = "max review iterations reached, human merge required"
        _reply_to_comment(event, body)
        logger.warning("PR %s hit review iteration cap", event.pr_number)
        return 2

    context = _surrounding_context(event)
    budget = _token_budget_from_env()
    brief = _ask_sonnet_for_brief(event, context, budget=budget, logger=logger)
    prompt_path = _write_prompt_file(event, brief, context)
    logger.info("dispatching review comment %s to Codex", event.comment_id)
    _run_codex(prompt_path)

    status = _run(["git", "status", "--porcelain"]).stdout.strip()
    if not status:
        _reply_to_comment(event, "Failed: Codex completed without producing changes.")
        logger.info("review comment %s produced no diff", event.comment_id)
        return 2

    sha = _commit_and_push(event)
    _reply_to_comment(event, f"Addressed in {sha}")
    return 0


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger = logging.getLogger("autopilot.implement_review_comment")
    try:
        return run(logger)
    except AutopilotError as exc:
        logger.error("autopilot review handler failed: %s", exc)
        try:
            event = _load_event()
            _reply_to_comment(event, f"Failed: {_tail(str(exc), 4000)}")
        except AutopilotError:
            logger.error("could not reply to review comment after failure")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
