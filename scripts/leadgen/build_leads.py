"""
Lead-generation CLI for AgentNexLiFy outreach.

Usage:
    python -m scripts.leadgen.build_leads \\
        --vertical "roofing" \\
        --city "Austin, TX" \\
        --out leads.csv \\
        [--max 200] \\
        [--api-key YOUR_KEY]

Environment:
    GOOGLE_PLACES_API_KEY  - Google Places API key (required if --api-key not set)
    DEMO_URL_TEMPLATE      - URL template with {place_id} placeholder
                             (default: https://agentnexlify.com/demo?ref={place_id})
"""

import argparse
import csv
import logging
import os
import sys
from typing import Optional

from scripts.leadgen.enrich import best_email, extract_emails_from_site
from scripts.leadgen.places import is_usable, search_text

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

CSV_HEADER = [
    "name",
    "category",
    "phone",
    "website",
    "email",
    "address",
    "city",
    "rating",
    "place_id",
    "demo_url",
]

_DEFAULT_DEMO_TEMPLATE = "https://agentnexlify.com/demo?ref={place_id}"


def run(args: argparse.Namespace) -> int:
    """
    Orchestrate lead generation.

    Returns the number of leads written to CSV.
    Exits via sys.exit(2) if the API key is missing.
    """
    api_key: Optional[str] = args.api_key or os.environ.get("GOOGLE_PLACES_API_KEY")
    if not api_key:
        print(
            "ERROR: Google Places API key required.\n"
            "  Set GOOGLE_PLACES_API_KEY environment variable or pass --api-key.",
            file=sys.stderr,
        )
        sys.exit(2)

    demo_template = os.environ.get("DEMO_URL_TEMPLATE", _DEFAULT_DEMO_TEMPLATE)
    query = f"{args.vertical} in {args.city}"

    logger.info("Searching: %s (max %d results)", query, args.max)
    places = search_text(query, api_key, max_results=args.max)

    usable = [p for p in places if is_usable(p)]
    logger.info("Found %d places, %d operational with website", len(places), len(usable))

    # Deduplicate by place_id (search_text already dedupes internally,
    # but guard against future callers combining multiple search runs)
    seen_ids: set = set()
    deduped = []
    for place in usable:
        pid = place.get("place_id", "")
        if pid and pid not in seen_ids:
            seen_ids.add(pid)
            deduped.append(place)

    rows = []
    email_count = 0

    for place in deduped:
        website = place.get("website", "")
        emails = extract_emails_from_site(website) if website else []
        email = best_email(emails)
        if email:
            email_count += 1

        place_id = place.get("place_id", "")
        try:
            demo_url = demo_template.format(place_id=place_id)
        except (KeyError, ValueError) as exc:
            logger.warning("demo_url_template format error: %s", exc)
            demo_url = _DEFAULT_DEMO_TEMPLATE.format(place_id=place_id)

        rows.append({
            "name": place.get("name", ""),
            "category": place.get("category", ""),
            "phone": place.get("phone", ""),
            "website": website,
            "email": email or "",
            "address": place.get("address", ""),
            "city": args.city,
            "rating": place.get("rating", ""),
            "place_id": place_id,
            "demo_url": demo_url,
        })

    out_path = args.out
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(rows)

    print(
        f"Done. {len(rows)} businesses written to {out_path} "
        f"({email_count} with email)."
    )
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pull local businesses from Google Places and enrich with emails.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m scripts.leadgen.build_leads "
            "--vertical roofing --city 'Austin, TX'\n"
            "  python -m scripts.leadgen.build_leads "
            "--vertical plumbing --city 'Denver, CO' --max 100 --out denver.csv\n"
            "\n"
            "Environment variables:\n"
            "  GOOGLE_PLACES_API_KEY   Google Places API key (required)\n"
            "  DEMO_URL_TEMPLATE       URL template, e.g. "
            "https://demo.example.com?ref={place_id}\n"
        ),
    )
    parser.add_argument(
        "--vertical",
        required=True,
        help="Business type to search for (e.g. 'roofing', 'dental', 'plumbing')",
    )
    parser.add_argument(
        "--city",
        required=True,
        help="City to search in (e.g. 'Austin, TX')",
    )
    parser.add_argument(
        "--out",
        default="leads.csv",
        help="Output CSV file path (default: leads.csv)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=200,
        help="Maximum number of leads to fetch (default: 200, cap: ~60 per query)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help=(
            "Google Places API key. "
            "Defaults to GOOGLE_PLACES_API_KEY environment variable."
        ),
    )
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
