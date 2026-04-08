"""Public production smoke checks that do not require database credentials."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


@dataclass
class SmokeResult:
    name: str
    ok: bool
    detail: str


def _base_url(value: str | None) -> str:
    if not value:
        raise RuntimeError("PUBLIC_BASE_URL is required")
    return value.rstrip("/") + "/"


def _url(base: str, path: str) -> str:
    return urljoin(base, path.lstrip("/"))


def _request(
    url: str,
    *,
    method: str = "GET",
    headers: Mapping[str, str] | None = None,
    timeout: float = 15.0,
) -> tuple[int, Mapping[str, str], bytes]:
    request = Request(url, method=method, headers=dict(headers or {}))
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - smoke script hits operator-provided URLs.
            return response.status, response.headers, response.read()
    except HTTPError as exc:
        return exc.code, exc.headers, exc.read()
    except URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc


def _json_body(body: bytes) -> dict:
    return json.loads(body.decode("utf-8"))


def _check_status(name: str, url: str, expected: set[int] | None = None) -> SmokeResult:
    expected = expected or {200}
    status, _, body = _request(url)
    if status not in expected:
        return SmokeResult(name, False, f"{url} returned {status}: {body[:160]!r}")
    return SmokeResult(name, True, f"{url} returned {status}")


def _check_json_status(name: str, url: str, expected_status: str) -> SmokeResult:
    status, _, body = _request(url)
    if status != 200:
        return SmokeResult(name, False, f"{url} returned {status}: {body[:160]!r}")
    try:
        payload = _json_body(body)
    except Exception as exc:
        return SmokeResult(name, False, f"{url} returned invalid JSON: {exc}")
    if payload.get("status") != expected_status:
        return SmokeResult(name, False, f"{url} status was {payload.get('status')!r}")
    return SmokeResult(name, True, f"{url} returned status={expected_status}")


def _check_api_version(name: str, url: str) -> SmokeResult:
    status, _, body = _request(url)
    if status != 200:
        return SmokeResult(name, False, f"{url} returned {status}: {body[:160]!r}")
    try:
        payload = _json_body(body)
    except Exception as exc:
        return SmokeResult(name, False, f"{url} returned invalid JSON: {exc}")
    if payload.get("service") != "agentnexlify" or not payload.get("version"):
        return SmokeResult(name, False, f"{url} returned unexpected payload: {payload!r}")
    return SmokeResult(name, True, f"{url} returned version={payload.get('version')}")


def _check_widget_script(name: str, url: str) -> SmokeResult:
    status, headers, body = _request(url)
    content_type = headers.get("content-type", "")
    if status != 200:
        return SmokeResult(name, False, f"{url} returned {status}: {body[:160]!r}")
    if "javascript" not in content_type and "text/plain" not in content_type:
        return SmokeResult(name, False, f"{url} content-type was {content_type!r}")
    if b"AgentNex" not in body and b"agentnexlify" not in body.lower():
        return SmokeResult(name, False, f"{url} did not look like the widget script")
    return SmokeResult(name, True, f"{url} returned widget script")


def _check_cors_preflight(name: str, url: str) -> SmokeResult:
    status, headers, body = _request(
        url,
        method="OPTIONS",
        headers={
            "Origin": "https://example-smoke.invalid",
            "Access-Control-Request-Method": "GET",
        },
    )
    if status not in {200, 204}:
        return SmokeResult(name, False, f"{url} preflight returned {status}: {body[:160]!r}")
    if "access-control-allow-origin" not in {key.lower() for key in headers.keys()}:
        return SmokeResult(name, False, f"{url} preflight did not include ACAO")
    return SmokeResult(name, True, f"{url} preflight returned {status}")


def run(public_base_url: str, api_base_url: str, widget_api_key: str | None) -> list[SmokeResult]:
    checks = [
        _check_status("frontend loads", _url(public_base_url, "/")),
        _check_json_status("frontend /api/v1 rewrite healthz", _url(public_base_url, "/api/v1/healthz"), "ok"),
        _check_api_version("frontend /api/v1 rewrite version", _url(public_base_url, "/api/v1/version")),
        _check_json_status("direct API healthz", _url(api_base_url, "/api/v1/healthz"), "ok"),
        _check_widget_script("widget script loads", _url(public_base_url, "/widget/agentnexlify-widget.js")),
        _check_cors_preflight("CORS preflight", _url(api_base_url, "/api/v1/healthz")),
    ]
    if widget_api_key:
        checks.append(
            _check_status(
                "widget config loads",
                _url(api_base_url, f"/api/v1/widget/config/{widget_api_key}"),
            )
        )
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-base-url", default=os.environ.get("PUBLIC_BASE_URL"))
    parser.add_argument("--api-base-url", default=os.environ.get("API_BASE_URL"))
    parser.add_argument("--widget-api-key", default=os.environ.get("PUBLIC_WIDGET_API_KEY"))
    args = parser.parse_args()

    public_base_url = _base_url(args.public_base_url)
    api_base_url = _base_url(args.api_base_url or args.public_base_url)

    results = run(public_base_url, api_base_url, args.widget_api_key)
    for result in results:
        prefix = "PASS" if result.ok else "FAIL"
        print(f"{prefix}: {result.name} - {result.detail}")

    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: smoke checks crashed - {exc}", file=sys.stderr)
        raise SystemExit(1)
