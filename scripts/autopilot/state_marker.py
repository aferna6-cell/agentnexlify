"""Idempotency marker helpers for autopilot issue classification.

The classifier posts comments containing `<!-- autopilot-state:HASH -->`.
The hash covers the issue body and human comments, excluding prior autopilot
marker comments, so the loop can detect new information without reposting the
same request for details on every cron tick.
"""

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from typing import Any

MARKER_RE = re.compile(r"<!--\s*autopilot-state:([0-9a-f]{64})\s*-->")


def make_state_marker(state_hash: str) -> str:
    """Return the HTML marker comment for a SHA-256 issue state hash."""

    if not re.fullmatch(r"[0-9a-f]{64}", state_hash):
        raise ValueError("state_hash must be a lowercase SHA-256 hex digest")
    return f"<!-- autopilot-state:{state_hash} -->"


def parse_state_markers(text: str | None) -> list[str]:
    """Extract all autopilot state hashes from a comment body."""

    if not text:
        return []
    return MARKER_RE.findall(text)


def _comment_body(comment: Any) -> str:
    if isinstance(comment, str):
        return comment
    if isinstance(comment, Mapping):
        body = comment.get("body")
        return "" if body is None else str(body)
    return ""


def human_comment_bodies(comments: Iterable[Any]) -> list[str]:
    """Return non-marker comment bodies that should influence state."""

    bodies: list[str] = []
    for comment in comments:
        body = _comment_body(comment).strip()
        if not body:
            continue
        if MARKER_RE.search(body):
            continue
        bodies.append(body)
    return bodies


def compute_state_hash(issue_state: Mapping[str, Any]) -> str:
    """Compute a stable SHA-256 hash for issue body and human comments."""

    payload = {
        "title": str(issue_state.get("title") or "").strip(),
        "body": str(issue_state.get("body") or "").strip(),
        "comments": sorted(human_comment_bodies(issue_state.get("comments") or [])),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def latest_state_hash(comments: Iterable[Any]) -> str | None:
    """Return the most recent marker hash seen in the supplied comments."""

    latest: str | None = None
    for comment in comments:
        markers = parse_state_markers(_comment_body(comment))
        if markers:
            latest = markers[-1]
    return latest


def is_current(issue_state: Mapping[str, Any]) -> bool:
    """Return true when comments contain a marker for the current issue state."""

    comments = issue_state.get("comments") or []
    return latest_state_hash(comments) == compute_state_hash(issue_state)
