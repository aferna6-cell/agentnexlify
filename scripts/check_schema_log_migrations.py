#!/usr/bin/env python3
"""Read-only drift check: schema-log applied status vs live schema_migrations.

Compares `docs/dev-knowledge/schema-log.md` to a caller-supplied dump of
`supabase_migrations.schema_migrations` (`version`, `name` only).

This script never applies migrations, never opens a database connection, and
never prints credentials or customer data.

Usage:
    python3 scripts/check_schema_log_migrations.py --live-json live.json

`live.json` must be a JSON array of objects with `version` and `name`, e.g.
the result of:

    SELECT version, name FROM supabase_migrations.schema_migrations ORDER BY version;

Exit codes:
    0 — no drift in the watch window
    1 — drift findings
    2 — live state could not be read (fail-closed)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_LOG = REPO_ROOT / "docs" / "dev-knowledge" / "schema-log.md"
DEFERRED_PATH = REPO_ROOT / "ops" / "schema" / "deferred-migrations.json"

DEFAULT_DEFERRED = frozenset({201})
DEFAULT_WATCH_FROM = 195

HEADING_RE = re.compile(
    r"^##[ \t]+(?:Migration[ \t]+)?(\d{3})(?:_([A-Za-z0-9_]+))?",
    re.MULTILINE,
)
HEADING_STATUS_RE = re.compile(
    r"\((NOT YET APPLIED|APPLIED)\b",
    re.IGNORECASE,
)
APPLIED_FIELD_RE = re.compile(
    r"\*\*Applied\*\*[^:\n]*:\s*(.+)",
    re.IGNORECASE,
)
SECRET_RE = re.compile(
    r"(postgres(?:ql)?://[^\s]+)"
    r"|(Bearer\s+\S+)"
    r"|((?:SUPABASE|DATABASE|SERVICE|API)[_A-Z]*KEY\s*=\s*\S+)"
    r"|(\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9._-]+)",
    re.IGNORECASE,
)


class LiveStateUnavailable(Exception):
    """Live schema_migrations rows could not be read."""


@dataclass(frozen=True)
class DocEntry:
    number: int
    slug: str
    name: str
    status: str
    heading: str


@dataclass(frozen=True)
class Finding:
    kind: str
    number: int | None
    name: str
    detail: str

    def render(self) -> str:
        label = f"{self.number} " if self.number is not None else ""
        name = self.name or "-"
        return f"{self.kind}: {label}{name} — {self.detail}"


def redact_secrets(text: str) -> str:
    return SECRET_RE.sub("[redacted]", text)


def _status_from_applied_value(value: str) -> str | None:
    lowered = value.strip().lower()
    if lowered.startswith(("not yet", "not applied", "pending", "no —", "no -", "no,")):
        return "unapplied"
    if lowered.startswith(("applied", "yes", "verified")):
        return "applied"
    if re.match(r"\d{4}-\d{2}-\d{2}", lowered):
        return "applied"
    return None


def parse_schema_log(text: str) -> list[DocEntry]:
    matches = list(HEADING_RE.finditer(text))
    entries: list[DocEntry] = []
    for index, match in enumerate(matches):
        number = int(match.group(1))
        slug = (match.group(2) or "").strip()
        heading = text[match.start() : text.find("\n", match.start())]
        if heading == text[match.start() :]:
            heading = heading.strip()
        else:
            heading = heading.strip()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.start() : end]
        status = "unknown"
        heading_status = HEADING_STATUS_RE.search(heading)
        if heading_status:
            status = "unapplied" if heading_status.group(1).upper().startswith("NOT") else "applied"
        else:
            field = APPLIED_FIELD_RE.search(block)
            if field:
                status = _status_from_applied_value(field.group(1)) or "unknown"
        name = f"{number}_{slug}" if slug else str(number)
        entries.append(
            DocEntry(number=number, slug=slug, name=name, status=status, heading=heading)
        )
    return entries


def load_deferred_allowlist(path: Path | None = None) -> frozenset[int]:
    target = path or DEFERRED_PATH
    if target is None or not target.exists():
        return DEFAULT_DEFERRED
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_DEFERRED
    raw = payload.get("deferred_unapplied", [])
    numbers = []
    for item in raw:
        try:
            numbers.append(int(item))
        except (TypeError, ValueError):
            continue
    return frozenset(numbers) or DEFAULT_DEFERRED


def _as_live_rows(raw: object) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        raise LiveStateUnavailable("live dump must be a JSON array of {version, name}")
    rows: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise LiveStateUnavailable("live dump rows must be objects with version and name")
        rows.append(
            {
                "version": str(item.get("version") or ""),
                "name": str(item.get("name") or ""),
            }
        )
    return rows


def load_live_rows(source: Path | None) -> list[dict[str, str]]:
    if source is None:
        raise LiveStateUnavailable("no live schema_migrations dump provided")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LiveStateUnavailable("live dump file is missing") from exc
    except OSError as exc:
        raise LiveStateUnavailable("live dump file could not be read") from exc
    except json.JSONDecodeError as exc:
        raise LiveStateUnavailable("live dump is not valid JSON") from exc
    return _as_live_rows(payload)


def _live_number_and_slug(name: str) -> tuple[int | None, str]:
    match = re.match(r"^(\d{3})_(.+)$", name)
    if match:
        return int(match.group(1)), match.group(2)
    return None, name


def _docs_for_live(entry_name: str, docs_by_number: dict[int, list[DocEntry]]) -> list[DocEntry]:
    number, slug = _live_number_and_slug(entry_name)
    matched: list[DocEntry] = []
    if number is not None and number in docs_by_number:
        matched.extend(docs_by_number[number])
    elif slug:
        for entries in docs_by_number.values():
            for doc in entries:
                if doc.slug and doc.slug == slug:
                    matched.append(doc)
    return matched


def compare(
    docs: list[DocEntry],
    live_rows: list[dict[str, str]] | None,
    deferred: frozenset[int],
    watch_from: int = DEFAULT_WATCH_FROM,
) -> list[Finding]:
    if live_rows is None:
        return [
            Finding(
                kind="live_unreadable",
                number=None,
                name="schema_migrations",
                detail="live state could not be read; failing closed",
            )
        ]

    findings: list[Finding] = []
    docs_by_number: dict[int, list[DocEntry]] = {}
    for doc in docs:
        docs_by_number.setdefault(doc.number, []).append(doc)

    for number, entries in docs_by_number.items():
        if number < watch_from:
            continue
        if len(entries) > 1:
            findings.append(
                Finding(
                    kind="duplicate_doc",
                    number=number,
                    name=entries[0].name,
                    detail=f"{len(entries)} schema-log headings share this number",
                )
            )

    names_seen: dict[str, int] = {}
    versions_seen: dict[str, int] = {}
    live_by_number: dict[int, list[dict[str, str]]] = {}

    for row in live_rows:
        version = row.get("version") or ""
        name = row.get("name") or ""
        if not version or not name:
            findings.append(
                Finding(
                    kind="unparseable_live_row",
                    number=_live_number_and_slug(name)[0],
                    name=name or "(missing name)",
                    detail="live row is missing version or name",
                )
            )
            continue
        names_seen[name] = names_seen.get(name, 0) + 1
        versions_seen[version] = versions_seen.get(version, 0) + 1
        number, slug = _live_number_and_slug(name)
        matched_docs = _docs_for_live(name, docs_by_number)
        if number is None and matched_docs:
            number = matched_docs[0].number
        if number is None:
            continue
        if number < watch_from:
            continue
        live_by_number.setdefault(number, []).append(row)
        if matched_docs:
            doc_slugs = {doc.slug for doc in matched_docs if doc.slug}
            if slug and doc_slugs and slug not in doc_slugs:
                findings.append(
                    Finding(
                        kind="name_mismatch",
                        number=number,
                        name=name,
                        detail=f"live slug {slug} does not match schema-log {sorted(doc_slugs)}",
                    )
                )

    for name, count in names_seen.items():
        number, _ = _live_number_and_slug(name)
        if number is not None and number < watch_from:
            continue
        if count > 1:
            findings.append(
                Finding(
                    kind="duplicate_live_name",
                    number=number,
                    name=name,
                    detail=f"live schema_migrations repeats this name {count} times",
                )
            )
    for version, count in versions_seen.items():
        if count > 1:
            findings.append(
                Finding(
                    kind="duplicate_live_version",
                    number=None,
                    name=version,
                    detail=f"live schema_migrations repeats this version {count} times",
                )
            )

    watched_numbers = {
        doc.number
        for doc in docs
        if doc.number >= watch_from and doc.status in {"applied", "unapplied"}
    }
    watched_numbers.update(num for num in live_by_number if num >= watch_from)

    for number in sorted(watched_numbers):
        doc_entries = docs_by_number.get(number, [])
        if not doc_entries:
            continue
        status = doc_entries[0].status
        name = doc_entries[0].name
        live_hits = live_by_number.get(number, [])
        if live_hits and status == "unapplied":
            findings.append(
                Finding(
                    kind="live_applied_docs_unapplied",
                    number=number,
                    name=name,
                    detail="live schema_migrations has this migration; schema-log still says unapplied",
                )
            )
        elif status == "applied" and not live_hits:
            findings.append(
                Finding(
                    kind="docs_applied_live_missing",
                    number=number,
                    name=name,
                    detail="schema-log says applied; live schema_migrations has no matching row",
                )
            )
        elif status == "unapplied" and not live_hits and number not in deferred:
            # Intentionally silent: unapplied + missing is consistent.
            # Deferred 201 is the documented exception that must stay silent too.
            continue

    return findings


def run_check(
    schema_log: Path,
    live_json: Path | None,
    deferred: Iterable[int] | None = None,
    watch_from: int = DEFAULT_WATCH_FROM,
) -> tuple[int, list[str]]:
    allowlist = frozenset(deferred) if deferred is not None else load_deferred_allowlist()
    try:
        text = schema_log.read_text(encoding="utf-8")
    except OSError as exc:
        return 2, [f"live_unreadable: schema-log — {redact_secrets(str(exc))}"]
    docs = parse_schema_log(text)
    try:
        live_rows = load_live_rows(live_json)
    except LiveStateUnavailable as exc:
        live_rows = None
        extra = redact_secrets(str(exc))
    else:
        extra = ""
    findings = compare(docs, live_rows, deferred=allowlist, watch_from=watch_from)
    if live_rows is None and extra and findings:
        findings = [
            Finding(
                kind="live_unreadable",
                number=None,
                name="schema_migrations",
                detail=extra,
            )
        ]
    lines = [item.render() for item in findings]
    if not findings:
        return 0, ["OK: schema-log matches live schema_migrations in the watch window"]
    if any(item.kind == "live_unreadable" for item in findings):
        return 2, lines
    return 1, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live-json",
        type=Path,
        help="JSON array of {version, name} from supabase_migrations.schema_migrations",
    )
    parser.add_argument(
        "--schema-log",
        type=Path,
        default=SCHEMA_LOG,
        help="schema-log markdown path",
    )
    parser.add_argument(
        "--deferred",
        type=int,
        nargs="*",
        help="override deferred-unapplied allowlist (default: ops/schema/deferred-migrations.json)",
    )
    parser.add_argument(
        "--watch-from",
        type=int,
        default=DEFAULT_WATCH_FROM,
        help="only compare migration numbers >= this (default: 195)",
    )
    args = parser.parse_args(argv)
    code, lines = run_check(
        schema_log=args.schema_log,
        live_json=args.live_json,
        deferred=args.deferred,
        watch_from=args.watch_from,
    )
    for line in lines:
        print(redact_secrets(line))
    return code


if __name__ == "__main__":
    sys.exit(main())
