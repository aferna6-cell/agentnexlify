"""
OpenStreetMap / Overpass lead source for leadgen (keyless, free).

Mirrors the place-dict shape that places.py emits (see place_fields) so
build_leads.py, is_usable, and the email enricher all work unchanged. No API
key required: resolves a city to an OSM area via Nominatim, then queries
Overpass for businesses tagged for the requested vertical.

Coverage is patchier than Google Places (not every SMB is in OSM), strongest
for trades (craft=roofer/plumber/electrician) and retail (shop=*). Free and
ODbL-licensed; attribution required only when displaying OSM data in a product
UI, not for an internal outreach list.
"""

import logging
import re
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

_USER_AGENT = (
    "AgentNexLiFy-LeadGen/1.0 (+https://agentnexlify.com; internal outreach)"
)

# vertical -> list of (key, value) OSM tag filters. value "*" means key present
# with any value. Unknown verticals fall back to a craft/shop/office guess.
_VERTICAL_TAGS: dict[str, list[tuple[str, str]]] = {
    "roofing": [("craft", "roofer")],
    "roofer": [("craft", "roofer")],
    "plumbing": [("craft", "plumber")],
    "plumber": [("craft", "plumber")],
    "hvac": [("craft", "hvac")],
    "electrician": [("craft", "electrician")],
    "electrical": [("craft", "electrician")],
    "dentist": [("amenity", "dentist"), ("healthcare", "dentist")],
    "dental": [("amenity", "dentist"), ("healthcare", "dentist")],
    "lawyer": [("office", "lawyer")],
    "law": [("office", "lawyer")],
    "salon": [("shop", "hairdresser"), ("shop", "beauty")],
    "hair": [("shop", "hairdresser")],
    "hairdresser": [("shop", "hairdresser")],
    "restaurant": [("amenity", "restaurant")],
    "landscaping": [("craft", "gardener"), ("shop", "garden_centre")],
    "landscaper": [("craft", "gardener")],
    "painter": [("craft", "painter")],
    "painting": [("craft", "painter")],
    "carpenter": [("craft", "carpenter")],
    "hvac_contractor": [("craft", "hvac")],
}


def tags_for_vertical(vertical: str) -> list[tuple[str, str]]:
    """Resolve a vertical string to OSM tag filters. Unknown -> craft/shop/office
    guess on a slugified token."""
    key = (vertical or "").strip().lower()
    if key in _VERTICAL_TAGS:
        return _VERTICAL_TAGS[key]
    slug = re.sub(r"[^a-z0-9_]", "_", key)
    return [("craft", slug), ("shop", slug), ("office", slug)]


def resolve_area_id(city: str, *, client: Optional[httpx.Client] = None) -> Optional[int]:
    """Resolve a city name to an Overpass area id via Nominatim. Returns None if
    unresolvable or if the match is a node (no area)."""
    owns_client = client is None
    client = client or httpx.Client(timeout=20.0)
    try:
        resp = client.get(
            NOMINATIM_URL,
            params={"q": city, "format": "json", "limit": 1},
            headers={"User-Agent": _USER_AGENT},
        )
        resp.raise_for_status()
        results = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("Nominatim lookup failed for %s: %s", city, exc)
        return None
    finally:
        if owns_client:
            client.close()

    if not results:
        logger.warning("Nominatim found no match for city: %s", city)
        return None

    first = results[0]
    osm_type = first.get("osm_type")
    osm_id = first.get("osm_id")
    if not osm_id:
        return None
    # Overpass area ids: relations + 3.6e9, ways + 2.4e9. Nodes have no area.
    if osm_type == "relation":
        return 3600000000 + int(osm_id)
    if osm_type == "way":
        return 2400000000 + int(osm_id)
    return None


def _build_query(area_id: int, tags: list[tuple[str, str]], limit: int) -> str:
    clauses = []
    for key, value in tags:
        sel = f'"{key}"' if value == "*" else f'"{key}"="{value}"'
        clauses.append(f"  nwr[{sel}](area.a);")
    body = "\n".join(clauses)
    return (
        f"[out:json][timeout:25];\n"
        f"area({area_id})->.a;\n"
        f"(\n{body}\n);\n"
        f"out tags center {limit};"
    )


def _compose_address(tags: dict) -> str:
    parts = [
        " ".join(p for p in [tags.get("addr:housenumber"), tags.get("addr:street")] if p),
        tags.get("addr:city"),
        tags.get("addr:state"),
        tags.get("addr:postcode"),
    ]
    return ", ".join(p for p in parts if p)


def element_to_place(el: dict) -> Optional[dict]:
    """Normalize one Overpass element to the places.py dict shape. Returns None
    if it has no name."""
    tags = el.get("tags") or {}
    name = tags.get("name")
    if not name:
        return None
    website = tags.get("website") or tags.get("contact:website") or ""
    phone = tags.get("phone") or tags.get("contact:phone") or ""
    category = (
        tags.get("craft")
        or tags.get("shop")
        or tags.get("office")
        or tags.get("amenity")
        or tags.get("healthcare")
        or ""
    )
    return {
        "place_id": f"osm:{el.get('type', 'node')}:{el.get('id', '')}",
        "name": name,
        "category": category,
        "phone": phone,
        "website": website,
        "address": _compose_address(tags),
        "rating": "",
        "rating_count": "",
        # OSM has no business-status field; treat tagged businesses as
        # operational so is_usable (status OPERATIONAL + website) passes.
        "business_status": "OPERATIONAL",
    }


def search_osm(vertical: str, city: str, max_results: int = 60) -> list:
    """Search OSM for businesses of `vertical` in `city`. Returns normalized
    dicts (places.py shape), deduplicated by place_id. Returns [] on any
    failure so callers degrade gracefully."""
    client = httpx.Client(timeout=30.0)
    try:
        area_id = resolve_area_id(city, client=client)
        if area_id is None:
            return []
        # Nominatim asks for <=1 req/sec; we made one call, so a tiny pause
        # before hitting Overpass is courteous and harmless.
        time.sleep(1.0)
        query = _build_query(area_id, tags_for_vertical(vertical), max_results)
        try:
            resp = client.post(
                OVERPASS_URL, data={"data": query}, headers={"User-Agent": _USER_AGENT}
            )
            resp.raise_for_status()
            elements = resp.json().get("elements", [])
        except (httpx.HTTPError, ValueError) as exc:
            logger.error("Overpass query failed for %s in %s: %s", vertical, city, exc)
            return []
    finally:
        client.close()

    results = []
    seen: set = set()
    for el in elements:
        if len(results) >= max_results:
            break
        place = element_to_place(el)
        if place is None:
            continue
        pid = place["place_id"]
        if pid not in seen:
            seen.add(pid)
            results.append(place)

    logger.info("search_osm('%s', '%s') returned %d places", vertical, city, len(results))
    return results
