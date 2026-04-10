"""CLI runner for the Field Monitor managed agent.

Produces the weekly AI/automation/SMB-SaaS digest and writes it into
`knowledge-base/raw/` so the kb-compile pipeline can promote it to the
wiki automatically.

Usage:
    python -m scripts.managed_agents.field_monitor_run
    python -m scripts.managed_agents.field_monitor_run --topic "AI agents launches"
    python -m scripts.managed_agents.field_monitor_run --out /tmp/digest.md

Exit codes:
    0 — digest written to disk
    1 — transport / credential / configuration failure
    2 — session completed but produced no assistant text
"""

import argparse
import logging
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
from backend.services.managed_agents_registry import field_monitor  # noqa: E402

_DEFAULT_OUT_DIR = _REPO_ROOT / "knowledge-base" / "raw"

_PROMPT_TEMPLATE = """\
Produce this week's digest focused on: {topic}

Follow your standard output format:
- Top 5 stories ranked by relevance
- For each story: headline, direct URL, exactly 3 short bullet summaries
- Close with one line naming the signal to watch next week

Use priority sources (Hacker News, Anthropic blog, Latent Space,
Stratechery, SMB SaaS blogs). Never fabricate headlines, links,
publication names, or dates.
"""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__ or "")
    parser.add_argument(
        "--topic",
        default="AI, automation, and SMB SaaS relevant to service-business automation",
        help="Focus topic for the weekly digest.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path. Defaults to knowledge-base/raw/field-monitor-<date>.md.",
    )
    return parser


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    args = _build_parser().parse_args()
    logger = logging.getLogger("managed_agents.field_monitor_run")

    try:
        result = run_agent_session(
            handle_factory=field_monitor,
            agent_label="field_monitor",
            kickoff_prompt=_PROMPT_TEMPLATE.format(topic=args.topic.strip()),
            session_title=f"field monitor digest: {args.topic[:80]}",
            metadata={"flow": "field_monitor", "topic": args.topic[:240]},
            logger_name="managed_agents.field_monitor_run",
        )
    except SessionRunError as exc:
        logger.error("field_monitor run failed: %s", exc)
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
        out_path = _DEFAULT_OUT_DIR / f"field-monitor-{stamp}.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "---\n"
        f"title: \"Field Monitor Digest {datetime.now().strftime('%Y-%m-%d')}\"\n"
        "category: market-intel\n"
        f"source: managed_agents.field_monitor\n"
        f"generated_at: {datetime.now().isoformat(timespec='seconds')}\n"
        f"session_id: {result.session_id}\n"
        "---\n\n"
    )
    out_path.write_text(header + result.reply_text + "\n")
    print(f"digest written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
