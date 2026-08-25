"""Unit tests for the pure helpers in osm_lead_source.

Run: python -m pytest scripts/outreach/test_osm_lead_source.py
The Overpass-calling path is intentionally not exercised here (no network).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from osm_lead_source import (  # noqa: E402
    VERTICAL_TAGS,
    build_query,
    dedupe_rows,
    element_to_row,
)


def test_build_query_contains_area_and_tags():
    q = build_query("salon", "Connecticut")
    assert '"name"="Connecticut"' in q
    assert '"shop"="hairdresser"' in q
    assert '["website"]' in q
    assert '["contact:website"]' in q
    assert q.startswith("[out:json]")


def test_build_query_plumber_hvac_covers_both_crafts():
    q = build_query("plumber_hvac", "Connecticut")
    assert '"craft"="plumber"' in q
    assert '"craft"="hvac"' in q


def test_element_to_row_happy_path():
    element = {
        "tags": {"name": "Shear Bliss Salon", "website": "https://www.shearbliss.com/book"}
    }
    assert element_to_row(element) == {
        "company_name": "Shear Bliss Salon",
        "domain": "shearbliss.com",
    }


def test_element_to_row_contact_website_fallback():
    element = {
        "tags": {"name": "Ace Plumbing", "contact:website": "http://aceplumbingct.com"}
    }
    row = element_to_row(element)
    assert row["domain"] == "aceplumbingct.com"


def test_element_to_row_drops_missing_name_or_site():
    assert element_to_row({"tags": {"website": "https://x.com"}}) is None
    assert element_to_row({"tags": {"name": "No Site"}}) is None
    assert element_to_row({}) is None


def test_element_to_row_drops_aggregator_hosts():
    for url in (
        "https://www.facebook.com/shearbliss",
        "https://instagram.com/aceplumbing",
        "https://shearbliss.wixsite.com/home",
        "https://shear-bliss.business.site",
        "https://booksy.com/en-us/shearbliss",
    ):
        assert element_to_row({"tags": {"name": "X", "website": url}}) is None


def test_dedupe_rows_keeps_first_per_domain():
    rows = [
        {"company_name": "A", "domain": "a.com"},
        {"company_name": "A2", "domain": "a.com"},
        {"company_name": "B", "domain": "b.com"},
    ]
    out = dedupe_rows(rows)
    assert [r["company_name"] for r in out] == ["A", "B"]


def test_all_13_launched_verticals_have_tag_presets():
    expected = {
        "salon", "plumber_hvac", "dental", "med_spa", "auto_repair",
        "law_firm", "restaurant", "fitness_studio", "roofing",
        "home_cleaning", "veterinary", "real_estate",
    }
    assert expected <= set(VERTICAL_TAGS)
