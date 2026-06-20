"""
Merge + dedup lead CSVs into one import-ready file.

The Google Places search caps at ~60 results per query, so the workflow is to
run build_leads.py once per neighborhood/city and combine the outputs. This
tool does that combine step (the README previously left it manual): it reads
N CSVs, deduplicates by place_id (so the same business found in two overlapping
searches is emailed once, not twice), drops rows with no email by default, and
writes a single clean CSV.

Usage:
    # merge explicit files
    python -m scripts.leadgen.merge_leads a.csv b.csv c.csv --out leads.csv

    # merge everything matching a glob
    python -m scripts.leadgen.merge_leads --glob "leads_*.csv" --out leads.csv

    # emit Instantly-ready columns (email + company_name + custom vars)
    python -m scripts.leadgen.merge_leads --glob "leads_*.csv" \\
        --out instantly.csv --instantly

Flags:
    --out PATH        Output CSV path (default: merged_leads.csv)
    --glob PATTERN    Glob for input files (alternative to positional paths)
    --instantly       Emit Instantly-import column names instead of raw schema
    --keep-no-email   Keep rows with no email (default: drop them)
"""

import argparse
import csv
import glob as globmod
import logging
import sys
from typing import Optional

from scripts.leadgen.build_leads import CSV_HEADER

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Instantly's cold-import auto-maps these names; extra columns become custom
# variables usable in a sequence as {{demo_url}}, {{city}}, etc.
INSTANTLY_HEADER = [
    "email",
    "company_name",
    "owner_name",
    "website",
    "phone",
    "city",
    "category",
    "demo_url",
    "contact_form",
]


def _dedup_key(row: dict) -> str:
    """Stable identity for a lead. place_id is canonical; fall back to website
    then business name so rows lacking a place_id still dedup sensibly."""
    pid = (row.get("place_id") or "").strip()
    if pid:
        return f"pid:{pid}"
    site = (row.get("website") or "").strip().lower().rstrip("/")
    if site:
        return f"site:{site}"
    return "name:" + (row.get("name") or "").strip().lower()


def _has_email(row: dict) -> bool:
    return bool((row.get("email") or "").strip())


def merge_rows(rows: list[dict], *, require_email: bool = True) -> list[dict]:
    """Dedup rows by identity key. On collision, prefer the row that has an
    email (a later run may have enriched a business the first run missed).
    Drops emailless rows when require_email is True. Order is preserved by
    first-seen key."""
    by_key: dict[str, dict] = {}
    order: list[str] = []
    for row in rows:
        key = _dedup_key(row)
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = row
            order.append(key)
        elif not _has_email(existing) and _has_email(row):
            by_key[key] = row  # upgrade to the enriched duplicate

    merged = [by_key[k] for k in order]
    if require_email:
        merged = [r for r in merged if _has_email(r)]
    return merged


def to_instantly(row: dict) -> dict:
    """Map a raw lead row to Instantly-import columns."""
    return {
        "email": row.get("email", ""),
        "company_name": row.get("name", ""),
        "owner_name": row.get("owner_name", ""),
        "website": row.get("website", ""),
        "phone": row.get("phone", ""),
        "city": row.get("city", ""),
        "category": row.get("category", ""),
        "demo_url": row.get("demo_url", ""),
        "contact_form": row.get("contact_form", ""),
    }


def read_csvs(paths: list[str]) -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        try:
            with open(path, newline="", encoding="utf-8") as fh:
                rows.extend(csv.DictReader(fh))
        except FileNotFoundError:
            logger.warning("input not found, skipping: %s", path)
    return rows


def write_csv(path: str, rows: list[dict], *, instantly: bool) -> None:
    header = INSTANTLY_HEADER if instantly else CSV_HEADER
    out_rows = [to_instantly(r) for r in rows] if instantly else rows
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(out_rows)


def run(args: argparse.Namespace) -> int:
    paths = list(args.inputs)
    if args.glob:
        paths.extend(sorted(globmod.glob(args.glob)))
    if not paths:
        print(
            "ERROR: no input CSVs. Pass file paths or --glob 'leads_*.csv'.",
            file=sys.stderr,
        )
        sys.exit(2)

    raw = read_csvs(paths)
    merged = merge_rows(raw, require_email=not args.keep_no_email)
    write_csv(args.out, merged, instantly=args.instantly)

    dropped = len(raw) - len(merged)
    print(
        f"Done. {len(raw)} rows in -> {len(merged)} unique written to "
        f"{args.out} ({dropped} duplicate/emailless removed)"
        + (" [Instantly format]" if args.instantly else "")
    )
    return len(merged)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge + dedup lead CSVs into one import-ready file.",
    )
    parser.add_argument("inputs", nargs="*", help="Input CSV paths")
    parser.add_argument("--glob", default=None, help="Glob for input files")
    parser.add_argument("--out", default="merged_leads.csv", help="Output CSV path")
    parser.add_argument(
        "--instantly",
        action="store_true",
        help="Emit Instantly-import columns (email, company_name, custom vars)",
    )
    parser.add_argument(
        "--keep-no-email",
        action="store_true",
        help="Keep rows with no email (default: drop them)",
    )
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
