"""Tests for scripts.leadgen.osm — fully offline (httpx mocked)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.leadgen import osm
from scripts.leadgen.osm import (
    element_to_place,
    resolve_area_id,
    search_osm,
    tags_for_vertical,
)
from scripts.leadgen.places import is_usable


# --------------------------------------------------------------------------
# tags_for_vertical
# --------------------------------------------------------------------------

def test_known_vertical_maps_to_tags():
    assert ("craft", "roofer") in tags_for_vertical("roofing")
    assert ("craft", "plumber") in tags_for_vertical("Plumber")  # case-insensitive


def test_unknown_vertical_falls_back_to_guess():
    tags = tags_for_vertical("yoga studio")
    keys = {k for k, _ in tags}
    assert keys == {"craft", "shop", "office"}
    # slugified value, spaces -> underscores
    assert all(v == "yoga_studio" for _, v in tags)


# --------------------------------------------------------------------------
# element_to_place — matches places.py shape + is_usable contract
# --------------------------------------------------------------------------

def test_element_to_place_full():
    el = {
        "type": "node",
        "id": 123,
        "tags": {
            "name": "Acme Roofing",
            "craft": "roofer",
            "website": "https://acme.com",
            "phone": "555-1212",
            "addr:housenumber": "10",
            "addr:street": "Main St",
            "addr:city": "Austin",
            "addr:state": "TX",
            "addr:postcode": "78701",
        },
    }
    place = element_to_place(el)
    assert place["place_id"] == "osm:node:123"
    assert place["name"] == "Acme Roofing"
    assert place["category"] == "roofer"
    assert place["website"] == "https://acme.com"
    assert place["phone"] == "555-1212"
    assert place["address"] == "10 Main St, Austin, TX, 78701"
    assert place["business_status"] == "OPERATIONAL"
    # Critical: the dict must satisfy is_usable from places.py
    assert is_usable(place) is True


def test_element_contact_website_fallback():
    el = {"type": "way", "id": 5, "tags": {"name": "X", "shop": "hairdresser",
          "contact:website": "https://x.com", "contact:phone": "9"}}
    place = element_to_place(el)
    assert place["website"] == "https://x.com"
    assert place["phone"] == "9"
    assert place["category"] == "hairdresser"


def test_element_without_name_is_skipped():
    assert element_to_place({"type": "node", "id": 1, "tags": {"craft": "roofer"}}) is None


def test_element_without_website_not_usable():
    place = element_to_place({"type": "node", "id": 2, "tags": {"name": "NoSite", "craft": "roofer"}})
    assert place is not None
    assert is_usable(place) is False  # no website


# --------------------------------------------------------------------------
# resolve_area_id
# --------------------------------------------------------------------------

def _client_returning(json_payload):
    client = MagicMock()
    resp = MagicMock()
    resp.json.return_value = json_payload
    resp.raise_for_status.return_value = None
    client.get.return_value = resp
    return client


def test_resolve_area_id_relation():
    client = _client_returning([{"osm_type": "relation", "osm_id": 113314}])
    assert resolve_area_id("Austin, TX", client=client) == 3600113314


def test_resolve_area_id_way():
    client = _client_returning([{"osm_type": "way", "osm_id": 42}])
    assert resolve_area_id("Tiny Town", client=client) == 2400000042


def test_resolve_area_id_node_returns_none():
    client = _client_returning([{"osm_type": "node", "osm_id": 7}])
    assert resolve_area_id("Some Node", client=client) is None


def test_resolve_area_id_no_match():
    client = _client_returning([])
    assert resolve_area_id("Nowhere", client=client) is None


# --------------------------------------------------------------------------
# search_osm — end to end with mocked Nominatim + Overpass
# --------------------------------------------------------------------------

def test_search_osm_happy_path():
    overpass_json = {
        "elements": [
            {"type": "node", "id": 1, "tags": {"name": "A Roof", "craft": "roofer",
             "website": "https://a.com"}},
            {"type": "node", "id": 1, "tags": {"name": "A Roof dup", "craft": "roofer",
             "website": "https://a.com"}},  # dup id -> deduped
            {"type": "way", "id": 2, "tags": {"name": "B Roof", "craft": "roofer",
             "website": "https://b.com"}},
        ]
    }
    post_resp = MagicMock()
    post_resp.json.return_value = overpass_json
    post_resp.raise_for_status.return_value = None
    fake_client = MagicMock()
    fake_client.post.return_value = post_resp

    with patch("scripts.leadgen.osm.httpx.Client", return_value=fake_client), patch(
        "scripts.leadgen.osm.resolve_area_id", return_value=3600000001
    ), patch("scripts.leadgen.osm.time.sleep"):
        results = search_osm("roofing", "Austin, TX", max_results=60)

    assert [r["place_id"] for r in results] == ["osm:node:1", "osm:way:2"]
    assert all(is_usable(r) for r in results)


def test_search_osm_unresolvable_city_returns_empty():
    with patch("scripts.leadgen.osm.httpx.Client", return_value=MagicMock()), patch(
        "scripts.leadgen.osm.resolve_area_id", return_value=None
    ):
        assert search_osm("roofing", "Nowhere", max_results=60) == []


def test_search_osm_overpass_error_returns_empty():
    import httpx as _httpx

    fake_client = MagicMock()
    fake_client.post.side_effect = _httpx.RequestError("overpass down")
    with patch("scripts.leadgen.osm.httpx.Client", return_value=fake_client), patch(
        "scripts.leadgen.osm.resolve_area_id", return_value=3600000001
    ), patch("scripts.leadgen.osm.time.sleep"):
        assert search_osm("roofing", "Austin", max_results=60) == []
