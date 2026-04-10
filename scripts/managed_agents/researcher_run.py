"""CLI runner for the Deep Researcher managed agent.

Produces a research brief for a given topic and writes the result as a
dated Markdown file under `research-briefs/`. This is an internal tool
for Aidan — no tenant auth, no HTTP surface.

Usage:
    python -m scripts.managed_agents.researcher_run "GoHighLevel pricing 2026"
    python -m scripts.managed_agents.researcher_run "Drillbit YC" --out /tmp/drillbit.md

Exit codes:
    0 — brief written to disk
    1 — transport / credential / configuration failure
    2 — session completed but produced no assistant text
"""

import argparse
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.managed_agents._smoke_common import (  # noqa: E402
    SessionRunError,
    run_agent_session,
)
from backend.services.managed_agents_registry import deep_researcher  # noqa: E402

_DEFAULT_OUT_DIR = _REPO_ROOT / "research-briefs"

_PROMPT_TEMPLATE = """\
Produce a research brief on: {topic}

Follow your standard brief format exactly:

Summary
Key Findings
Sources
Open Questions

Use at least five distinct sources. Favor primary/first-party material
for product facts, pricing, and feature claims. Never invent URLs or
quotes. Keep the brief tight — aim for around 500-800 words total.
"""


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "untitled"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__ or "")
    parser.add_argument("topic", help="Research topic passed to the agent.")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Explicit output file path. Defaults to research-briefs/<date>-<slug>.md.",
    )
    return parser


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    args = _build_parser().parse_args()
    logger = logging.getLogger("managed_agents.researcher_run")

    try:
        result = run_agent_session(
            handle_factory=deep_researcher,
            agent_label="deep_researcher",
            kickoff_prompt=_PROMPT_TEMPLATE.format(topic=args.topic.strip()),
            session_title=f"research brief: {args.topic[:80]}",
            metadata={"flow": "deep_researcher", "topic": args.topic[:240]},
            logger_name="managed_agents.researcher_run",
        )
    except SessionRunError as exc:
        logger.error("researcher run failed: %s", exc)
        return 1

    if not result.reply_text:
        logger.error(
            "session completed but produced no assistant text (events=%d)",
            result.event_count,
        )
        return 2

    if args.out is not None:
        out_path = args.out
    else:
        _DEFAULT_OUT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d")
        out_path = _DEFAULT_OUT_DIR / f"{stamp}-{_slugify(args.topic)}.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f"# Research brief: {args.topic.strip()}\n\n"
        f"- Generated: {datetime.now().isoformat(timespec='seconds')}\n"
        f"- Session: {result.session_id}\n"
        f"- Events: {result.event_count}\n"
        f"- Elapsed: {result.elapsed_s:.1f}s\n\n"
        "---\n\n"
    )
    out_path.write_text(header + result.reply_text + "\n")
    print(f"brief written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
