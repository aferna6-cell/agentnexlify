"""Replay widget-chat scenarios and score latency + response quality.

Examples:
    python ops/scripts/run_widget_llm_eval.py --api-key wk_live_123
    python ops/scripts/run_widget_llm_eval.py --base-url http://127.0.0.1:8000 --api-key wk_test_123 --repeats 5
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib import error, request


DEFAULT_BASE_URL = os.getenv(
    "AGENTNEXLIFY_BASE_URL",
    "https://agentnexlify-production.up.railway.app",
)
DEFAULT_SCENARIO_FILE = (
    Path(__file__).resolve().parent.parent / "evals" / "widget_chat_scenarios.jsonl"
)


@dataclass
class EvalScenario:
    label: str
    message: str
    notes: str = ""
    max_sentences: int | None = None
    min_response_chars: int | None = None
    max_response_chars: int | None = None
    must_not_contain: list[str] | None = None
    must_contain_any: list[str] | None = None
    must_contain_all: list[str] | None = None


@dataclass
class EvalResult:
    label: str
    iteration: int
    ok: bool
    latency_ms: int
    status_code: int
    response_text: str
    failures: list[str]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--api-key", default=os.getenv("AGENTNEXLIFY_WIDGET_API_KEY"))
    parser.add_argument("--scenario-file", default=str(DEFAULT_SCENARIO_FILE))
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--pause-ms", type=int, default=0)
    parser.add_argument("--output")
    parser.add_argument("--allow-failures", action="store_true")
    args = parser.parse_args()
    if not args.api_key:
        parser.error("--api-key is required (or set AGENTNEXLIFY_WIDGET_API_KEY)")
    if args.repeats < 1:
        parser.error("--repeats must be >= 1")
    return args


def _load_scenarios(path: str) -> list[EvalScenario]:
    scenarios: list[EvalScenario] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            label = payload.get("label")
            message = payload.get("message")
            if not isinstance(label, str) or not label.strip():
                raise ValueError(f"Scenario line {line_number} is missing a label")
            if not isinstance(message, str) or not message.strip():
                raise ValueError(f"Scenario line {line_number} is missing a message")
            scenarios.append(EvalScenario(**payload))
    if not scenarios:
        raise ValueError(f"No scenarios found in {path}")
    return scenarios


def _count_sentences(text: str) -> int:
    stripped = text.strip()
    if not stripped:
        return 0
    terminal_marks = sum(1 for char in stripped if char in ".!?")
    return max(1, terminal_marks)


def _evaluate_quality(scenario: EvalScenario, response_text: str) -> list[str]:
    failures: list[str] = []
    normalized = response_text.lower()

    if not response_text.strip():
        failures.append("response was empty")

    if scenario.max_sentences is not None:
        sentence_count = _count_sentences(response_text)
        if sentence_count > scenario.max_sentences:
            failures.append(
                f"response used {sentence_count} sentences (max {scenario.max_sentences})"
            )

    if scenario.min_response_chars is not None and len(response_text) < scenario.min_response_chars:
        failures.append(
            f"response had {len(response_text)} chars (min {scenario.min_response_chars})"
        )

    if scenario.max_response_chars is not None and len(response_text) > scenario.max_response_chars:
        failures.append(
            f"response had {len(response_text)} chars (max {scenario.max_response_chars})"
        )

    for phrase in scenario.must_not_contain or []:
        if phrase.lower() in normalized:
            failures.append(f"forbidden phrase present: {phrase}")

    required_any = scenario.must_contain_any or []
    if required_any and not any(phrase.lower() in normalized for phrase in required_any):
        failures.append(
            "response missed any-of phrases: " + ", ".join(required_any)
        )

    for phrase in scenario.must_contain_all or []:
        if phrase.lower() not in normalized:
            failures.append(f"missing required phrase: {phrase}")

    return failures


def _post_chat_message(base_url: str, api_key: str, message: str, session_id: str, timeout: float) -> tuple[int, dict[str, Any], int]:
    payload = json.dumps(
        {
            "api_key": api_key,
            "session_id": session_id,
            "message": message,
        }
    ).encode("utf-8")
    req = request.Request(
        url=base_url.rstrip("/") + "/api/v1/widget/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    started = time.perf_counter()
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            status_code = resp.status
            body = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        status_code = exc.code
        body = exc.read().decode("utf-8", errors="replace")
    latency_ms = int((time.perf_counter() - started) * 1000)

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        parsed = {"raw_body": body}

    return status_code, parsed, latency_ms


def _extract_response_text(payload: dict[str, Any]) -> str:
    for key in ("response", "reply", "message"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return ""


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


def _truncate(text: str, limit: int = 88) -> str:
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3].rstrip() + "..."


def main() -> int:
    args = _parse_args()
    scenarios = _load_scenarios(args.scenario_file)
    results: list[EvalResult] = []

    for scenario in scenarios:
        for iteration in range(1, args.repeats + 1):
            session_id = f"eval-{scenario.label}-{iteration}-{uuid.uuid4().hex[:8]}"
            status_code, payload, latency_ms = _post_chat_message(
                base_url=args.base_url,
                api_key=args.api_key,
                message=scenario.message,
                session_id=session_id,
                timeout=args.timeout,
            )
            response_text = _extract_response_text(payload)
            failures = [] if status_code == 200 else [f"unexpected status {status_code}"]
            failures.extend(_evaluate_quality(scenario, response_text))
            results.append(
                EvalResult(
                    label=scenario.label,
                    iteration=iteration,
                    ok=not failures,
                    latency_ms=latency_ms,
                    status_code=status_code,
                    response_text=response_text,
                    failures=failures,
                )
            )
            status_label = "PASS" if not failures else "FAIL"
            print(
                f"{status_label:4} {latency_ms:5} ms  {scenario.label:<18} "
                f"{_truncate(response_text or json.dumps(payload, sort_keys=True))}"
            )
            if args.pause_ms:
                time.sleep(args.pause_ms / 1000)

    latencies = [result.latency_ms for result in results]
    passed = sum(1 for result in results if result.ok)
    failed = len(results) - passed
    summary = {
        "base_url": args.base_url,
        "scenario_file": str(Path(args.scenario_file).resolve()),
        "scenario_count": len(scenarios),
        "repeats": args.repeats,
        "total_runs": len(results),
        "passed": passed,
        "failed": failed,
        "avg_latency_ms": round(statistics.fmean(latencies), 1) if latencies else 0,
        "p50_latency_ms": _percentile(latencies, 0.50),
        "p95_latency_ms": _percentile(latencies, 0.95),
        "max_latency_ms": max(latencies) if latencies else 0,
        "results": [asdict(result) for result in results],
    }

    print("")
    print(
        f"Summary: {passed}/{len(results)} passed | "
        f"avg={summary['avg_latency_ms']} ms | "
        f"p50={summary['p50_latency_ms']} ms | "
        f"p95={summary['p95_latency_ms']} ms | "
        f"max={summary['max_latency_ms']} ms"
    )

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2)
            handle.write("\n")
        print(f"Saved report to {output_path}")

    if failed and not args.allow_failures:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
