"""Summarize recent Railway HTTP latency from JSON log lines.

Examples:
    python ops/scripts/summarize_railway_http_latency.py --path /api/v1/widget/chat --lines 200
    railway logs --http --json --lines 300 | python ops/scripts/summarize_railway_http_latency.py --method POST
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="Optional file containing JSON log lines.")
    parser.add_argument("--path", help="Only include requests whose path matches exactly.")
    parser.add_argument("--method", help="Only include a specific HTTP method.")
    parser.add_argument("--status", type=int, help="Only include a specific HTTP status code.")
    parser.add_argument("--lines", type=int, default=200, help="How many recent Railway log lines to fetch.")
    parser.add_argument("--output", help="Optional JSON file for the summary payload.")
    parser.add_argument(
        "--show-slowest",
        type=int,
        default=5,
        help="How many slowest requests to print.",
    )
    return parser.parse_args()


def _load_input_lines(args: argparse.Namespace) -> list[str]:
    if args.input:
        return Path(args.input).read_text(encoding="utf-8").splitlines()

    if not sys.stdin.isatty():
        return sys.stdin.read().splitlines()

    railway_executable = (
        os.getenv("RAILWAY_CLI_PATH")
        or shutil.which("railway")
        or shutil.which("railway.cmd")
    )
    if not railway_executable:
        raise RuntimeError("Could not find Railway CLI on PATH")

    command = [railway_executable, "logs", "--http", "--json", "--lines", str(args.lines)]
    if args.path:
        command.extend(["--path", args.path])

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "railway logs failed")
    return completed.stdout.splitlines()


def _parse_entries(lines: list[str]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def _filter_entries(entries: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for entry in entries:
        if args.path and entry.get("path") != args.path:
            continue
        if args.method and entry.get("method") != args.method:
            continue
        if args.status is not None and entry.get("httpStatus") != args.status:
            continue
        if not isinstance(entry.get("totalDuration"), int) and not isinstance(entry.get("upstreamRqDuration"), int):
            continue
        filtered.append(entry)
    return filtered


def _duration(entry: dict[str, Any]) -> int:
    value = entry.get("totalDuration")
    if isinstance(value, int):
        return value
    fallback = entry.get("upstreamRqDuration")
    if isinstance(fallback, int):
        return fallback
    return 0


def _percentile(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = (len(ordered) - 1) * percentile
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return ordered[lower]
    fraction = index - lower
    return int(ordered[lower] + (ordered[upper] - ordered[lower]) * fraction)


def main() -> int:
    args = _parse_args()
    lines = _load_input_lines(args)
    entries = _filter_entries(_parse_entries(lines), args)

    if not entries:
        print("No matching Railway HTTP log entries found.")
        return 1

    durations = [_duration(entry) for entry in entries]
    status_counts: dict[int, int] = {}
    for entry in entries:
        status = int(entry.get("httpStatus", 0))
        status_counts[status] = status_counts.get(status, 0) + 1

    summary = {
        "count": len(entries),
        "avg_latency_ms": round(statistics.fmean(durations), 1),
        "p50_latency_ms": _percentile(durations, 0.50),
        "p90_latency_ms": _percentile(durations, 0.90),
        "p95_latency_ms": _percentile(durations, 0.95),
        "max_latency_ms": max(durations),
        "min_latency_ms": min(durations),
        "status_counts": status_counts,
        "slowest": [
            {
                "timestamp": entry.get("timestamp"),
                "method": entry.get("method"),
                "path": entry.get("path"),
                "status": entry.get("httpStatus"),
                "latency_ms": _duration(entry),
                "request_id": entry.get("requestId"),
            }
            for entry in sorted(entries, key=_duration, reverse=True)[: max(args.show_slowest, 0)]
        ],
    }

    print(
        f"Requests: {summary['count']} | avg={summary['avg_latency_ms']} ms | "
        f"p50={summary['p50_latency_ms']} ms | p90={summary['p90_latency_ms']} ms | "
        f"p95={summary['p95_latency_ms']} ms | max={summary['max_latency_ms']} ms"
    )
    print("Status counts:", ", ".join(f"{status}={count}" for status, count in sorted(status_counts.items())))

    if summary["slowest"]:
        print("Slowest requests:")
        for item in summary["slowest"]:
            print(
                f"  {item['latency_ms']:5} ms  {item['status']}  {item['method']} "
                f"{item['path']}  {item['timestamp']}  {item['request_id']}"
            )

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"Saved summary to {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
