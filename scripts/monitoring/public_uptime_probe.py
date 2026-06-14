"""Probe public production endpoints and optionally post failures to Slack."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "ops" / "monitoring" / "uptime-checks.json"


@dataclass
class ProbeResult:
    name: str
    ok: bool
    detail: str


def _request(
    url: str,
    *,
    method: str,
    timeout: float,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    request = Request(url, data=body, method=method, headers=headers or {})
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - operator-owned public endpoints.
            return response.status, dict(response.headers), response.read()
    except HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()
    except URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc


def _expected_json_matches(payload: Any, expected: dict[str, Any]) -> bool:
    if not isinstance(payload, dict):
        return False
    for key, expected_value in expected.items():
        if payload.get(key) != expected_value:
            return False
    return True


def _probe(check: dict[str, Any], timeout: float) -> ProbeResult:
    name = str(check["name"])
    url = str(check["url"])
    method = str(check.get("method", "GET")).upper()
    expected_status = int(check.get("expected_status", 200))

    try:
        status, headers, body = _request(url, method=method, timeout=timeout)
    except Exception as exc:
        return ProbeResult(name, False, f"{url} request failed: {exc}")

    if status != expected_status:
        return ProbeResult(name, False, f"{url} returned {status}, expected {expected_status}")

    expected_json = check.get("expected_json")
    if expected_json:
        # Judge by the body, not the content-type header: Railway's edge
        # serves an empty content-type to some networks (observed from
        # GitHub-hosted runners) while the JSON body is correct. A valid,
        # matching body is UP; the header is diagnostic detail only.
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception as exc:
            content_type = headers.get("content-type", "")
            return ProbeResult(
                name,
                False,
                f"{url} returned unparseable JSON (content-type {content_type!r}, "
                f"first bytes {body[:80]!r}): {exc}",
            )
        if not _expected_json_matches(payload, expected_json):
            return ProbeResult(name, False, f"{url} JSON did not include {expected_json!r}")

    return ProbeResult(name, True, f"{url} returned {status}")


def _post_slack(webhook_url: str, failures: list[ProbeResult]) -> None:
    lines = ["*AgentNexLiFy uptime probe failed*"]
    for failure in failures:
        lines.append(f"- {failure.name}: {failure.detail}")
    payload = json.dumps({"text": "\n".join(lines)}).encode("utf-8")
    status, _, body = _request(
        webhook_url,
        method="POST",
        timeout=10.0,
        body=payload,
        headers={"Content-Type": "application/json"},
    )
    if status >= 300:
        raise RuntimeError(f"Slack webhook returned {status}: {body[:160]!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=os.environ.get("UPTIME_MONITOR_CONFIG", str(DEFAULT_CONFIG)),
        help="Path to uptime-checks.json",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("UPTIME_MONITOR_TIMEOUT", "15")),
    )
    parser.add_argument(
        "--slack-webhook-url",
        default=os.environ.get("SLACK_ALERT_WEBHOOK_URL"),
        help="Optional Slack incoming webhook URL for failure alerts",
    )
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    results = [_probe(check, args.timeout) for check in config["checks"]]

    for result in results:
        prefix = "PASS" if result.ok else "FAIL"
        print(f"{prefix}: {result.name} - {result.detail}")

    failures = [result for result in results if not result.ok]
    if failures and args.slack_webhook_url:
        _post_slack(args.slack_webhook_url, failures)
        print(f"ALERT: posted {len(failures)} failure(s) to Slack")
    elif failures:
        print("WARN: SLACK_ALERT_WEBHOOK_URL is not set; no external alert was posted")

    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
