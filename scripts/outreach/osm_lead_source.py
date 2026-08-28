#!/usr/bin/env python3
"""Keyless candidate sourcing from OpenStreetMap (Overpass API).

Produces the candidates CSV that `instantly_lead_engine.py` consumes —
`company_name,domain` — WITHOUT the Google Places API key that blocked the
outreach loop (Open Loops: `GOOGLE_PLACES_API_KEY` never landed in Railway).
Overpass is free, keyless, and licensed for this use (ODbL attribution note
below); only businesses that publish a `website` tag are emitted, so every
row already carries the domain the engine needs for its `info@<domain>`
role-email + verification pass.

Vertical presets map to OSM tags for our 13 launched verticals; the two
top-signal verticals (salon, plumber/HVAC) are the defaults.

Usage:
    python3 scripts/outreach/osm_lead_source.py \
        --vertical salon --area "Connecticut" \
        --out scripts/outreach/candidates/salon-ct.csv [--limit 300]

Then feed the CSV to the engine exactly as before:
    python3 scripts/outreach/instantly_lead_engine.py \
        --candidates scripts/outreach/candidates/salon-ct.csv --campaign ...

No secrets. Stdlib only. ODbL: data (c) OpenStreetMap contributors — keep
this notice when redistributing sourced lists.
"""

import argparse
import csv
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from instantly_lead_engine import normalize_domain  # noqa: E402

# Public Overpass endpoints, tried in order. Some networks block one host but
# allow another; a per-mirror failure falls through to the next.
OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.osm.jp/api/interpreter",
)

# Same managed-proxy accommodations as instantly_lead_engine.py.
_UA = "curl/8.5.0"
_CA_BUNDLE = "/root/.ccr/ca-bundle.crt"

# Vertical -> list of Overpass tag filters (each entry is a [k=v] selector).
# Multiple selectors are OR'd (one query block each).
VERTICAL_TAGS = {
    "salon": ['["shop"="hairdresser"]', '["shop"="beauty"]'],
    "plumber_hvac": ['["craft"="plumber"]', '["craft"="hvac"]'],
    "dental": ['["amenity"="dentist"]'],
    "med_spa": ['["shop"="beauty"]["beauty"~"spa|skin_care"]', '["leisure"="spa"]'],
    "auto_repair": ['["shop"="car_repair"]'],
    "law_firm": ['["office"="lawyer"]'],
    "restaurant": ['["amenity"="restaurant"]'],
    "fitness_studio": ['["leisure"="fitness_centre"]'],
    "roofing": ['["craft"="roofer"]'],
    "home_cleaning": ['["shop"="cleaning"]', '["craft"="cleaning"]'],
    "veterinary": ['["amenity"="veterinary"]'],
    "real_estate": ['["office"="estate_agent"]'],
}


def build_query(vertical: str, area_name: str, timeout_s: int = 90) -> str:
    """Overpass QL: businesses of `vertical` inside named `area`, website tag required."""
    selectors = VERTICAL_TAGS[vertical]
    blocks = "".join(
        f'nwr{sel}["website"](area.a);' for sel in selectors
    ) + "".join(
        f'nwr{sel}["contact:website"](area.a);' for sel in selectors
    )
    return (
        f"[out:json][timeout:{timeout_s}];"
        f'area["name"="{area_name}"]->.a;'
        f"({blocks});"
        "out tags;"
    )


def element_to_row(element: dict) -> dict | None:
    """Map one Overpass element to {company_name, domain}, or None if unusable."""
    tags = element.get("tags") or {}
    name = (tags.get("name") or "").strip()
    website = (tags.get("website") or tags.get("contact:website") or "").strip()
    if not name or not website:
        return None
    domain = normalize_domain(website)
    # Aggregator/social URLs make useless role emails — skip them.
    if not domain or "." not in domain:
        return None
    skip_hosts = (
        "facebook.com", "instagram.com", "linktr.ee", "google.com",
        "yelp.com", "wixsite.com", "business.site", "squareup.com",
        "booksy.com", "vagaro.com",
    )
    if any(domain == h or domain.endswith("." + h) for h in skip_hosts):
        return None
    return {"company_name": name, "domain": domain}


def dedupe_rows(rows: list) -> list:
    """Drop duplicate domains, keeping first occurrence (stable)."""
    out, seen = [], set()
    for row in rows:
        if row["domain"] in seen:
            continue
        seen.add(row["domain"])
        out.append(row)
    return out


def _ssl_context():
    ctx = ssl.create_default_context()
    if os.path.exists(_CA_BUNDLE):
        try:
            ctx.load_verify_locations(_CA_BUNDLE)
        except Exception:
            pass
    return ctx


def fetch_elements(query: str, timeout: int = 120) -> list:
    """POST the query to Overpass mirrors in order, return element list.

    Raises the last error when every mirror fails.
    """
    data = urllib.parse.urlencode({"data": query}).encode()
    last_exc: Exception = RuntimeError("no Overpass mirror configured")
    for url in OVERPASS_URLS:
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("User-Agent", _UA)
        try:
            with urllib.request.urlopen(
                req, timeout=timeout, context=_ssl_context()
            ) as r:
                payload = json.loads(r.read() or b"{}")
            return payload.get("elements", [])
        except Exception as exc:
            sys.stderr.write(f"mirror failed ({url}): {exc}\n")
            last_exc = exc
    raise last_exc


def run(vertical: str, area: str, out_path: str, limit: int = 0) -> dict:
    query = build_query(vertical, area)
    elements = fetch_elements(query)
    rows = dedupe_rows(
        [row for row in (element_to_row(e) for e in elements) if row]
    )
    if limit:
        rows = rows[:limit]
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["company_name", "domain"])
        writer.writeheader()
        writer.writerows(rows)
    return {
        "vertical": vertical,
        "area": area,
        "elements_returned": len(elements),
        "candidates_written": len(rows),
        "out": out_path,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Keyless OSM candidate source")
    ap.add_argument("--vertical", required=True, choices=sorted(VERTICAL_TAGS))
    ap.add_argument("--area", required=True,
                    help='OSM area name, e.g. "Connecticut" or "Fairfield County"')
    ap.add_argument("--out", required=True, help="Output CSV path")
    ap.add_argument("--limit", type=int, default=0, help="Max candidates (0 = all)")
    args = ap.parse_args(argv)
    try:
        summary = run(args.vertical, args.area, args.out, limit=args.limit)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        sys.stderr.write(f"Overpass fetch failed: {exc}\n")
        return 1
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
