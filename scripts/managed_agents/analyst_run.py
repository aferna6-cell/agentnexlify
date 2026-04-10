"""CLI runner for the Data Analyst managed agent.

Reads a local CSV / TSV / JSON export, hands it to the Data Analyst
agent with a natural-language question, and writes the Markdown
response under `reports/`. Internal tool — no tenant auth.

Usage:
    python -m scripts.managed_agents.analyst_run \\
        --export /tmp/supabase-dump.csv \\
        --question "which tenants are inactive last 30 days?"

    python -m scripts.managed_agents.analyst_run \\
        --inline-csv day,visitors\\nmon,100\\ntue,120 \\
        --question "mean visitors"

Exit codes:
    0 — report written to disk
    1 — transport / credential / configuration failure or bad args
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
from backend.services.managed_agents_registry import data_analyst  # noqa: E402

_DEFAULT_OUT_DIR = _REPO_ROOT / "reports"

_PROMPT_TEMPLATE = """\
Analyze the provided data and answer the question below. Use pandas
and Python scripts saved under /tmp/. Your final reply MUST be a
Markdown report that includes:

- A short summary
- Method notes (columns, filters, transformations used)
- Table previews of key results
- File paths to any analysis scripts or generated artifacts
- Assumptions you had to make while cleaning the data

QUESTION:
{question}

DATA SOURCE:
{data_block}
"""


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "analysis"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__ or "")
    parser.add_argument(
        "--question",
        required=True,
        help="The analysis question to ask the agent.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--export",
        type=Path,
        help="Path to a CSV/TSV/JSON export file to inline into the prompt.",
    )
    source.add_argument(
        "--inline-csv",
        help="Raw CSV/TSV text to embed directly in the prompt.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output file path. Defaults to reports/<date>-<slug>.md.",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=120_000,
        help="Max bytes of export content to send inline (default 120k).",
    )
    return parser


def _load_data_block(args: argparse.Namespace) -> tuple[str, str]:
    if args.inline_csv:
        body = args.inline_csv.replace("\\n", "\n")
        return "inline", body
    assert args.export is not None  # argparse guarantees one of the two
    if not args.export.exists():
        raise SystemExit(f"export file not found: {args.export}")
    raw = args.export.read_bytes()
    if len(raw) > args.max_bytes:
        raise SystemExit(
            f"export too large ({len(raw)} bytes > {args.max_bytes}). "
            "Shrink it or raise --max-bytes."
        )
    return args.export.name, raw.decode("utf-8", errors="replace")


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    args = _build_parser().parse_args()
    logger = logging.getLogger("managed_agents.analyst_run")

    try:
        source_label, data_block_body = _load_data_block(args)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("failed to load data: %s", exc)
        return 1

    data_block = (
        f"source: {source_label}\n"
        "format: raw text (interpret as CSV unless clearly JSON/TSV)\n"
        "---\n"
        f"{data_block_body}\n"
        "---\n"
    )

    try:
        result = run_agent_session(
            handle_factory=data_analyst,
            agent_label="data_analyst",
            kickoff_prompt=_PROMPT_TEMPLATE.format(
                question=args.question.strip(),
                data_block=data_block,
            ),
            session_title=f"analyst: {args.question[:80]}",
            metadata={
                "flow": "data_analyst",
                "question": args.question[:240],
                "source": source_label[:120],
            },
            logger_name="managed_agents.analyst_run",
        )
    except SessionRunError as exc:
        logger.error("analyst run failed: %s", exc)
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
        out_path = _DEFAULT_OUT_DIR / f"{stamp}-{_slugify(args.question)}.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f"# Analyst report: {args.question.strip()}\n\n"
        f"- Generated: {datetime.now().isoformat(timespec='seconds')}\n"
        f"- Session: {result.session_id}\n"
        f"- Data source: {source_label}\n"
        f"- Events: {result.event_count}\n"
        f"- Elapsed: {result.elapsed_s:.1f}s\n\n"
        "---\n\n"
    )
    out_path.write_text(header + result.reply_text + "\n")
    print(f"report written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
