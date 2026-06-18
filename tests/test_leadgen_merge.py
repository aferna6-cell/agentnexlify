"""Tests for scripts.leadgen.merge_leads — fully offline."""

import csv
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.leadgen.merge_leads import (
    INSTANTLY_HEADER,
    merge_rows,
    read_csvs,
    to_instantly,
    write_csv,
)
from scripts.leadgen.build_leads import CSV_HEADER


def _row(**kw):
    base = {h: "" for h in CSV_HEADER}
    base.update(kw)
    return base


# --------------------------------------------------------------------------
# merge_rows
# --------------------------------------------------------------------------

def test_dedups_by_place_id():
    rows = [
        _row(place_id="A", name="Acme", email="a@acme.com"),
        _row(place_id="A", name="Acme dup", email="a@acme.com"),
        _row(place_id="B", name="Bravo", email="b@bravo.com"),
    ]
    out = merge_rows(rows)
    assert len(out) == 2
    assert {r["place_id"] for r in out} == {"A", "B"}


def test_drops_emailless_rows_by_default():
    rows = [
        _row(place_id="A", name="Acme", email="a@acme.com"),
        _row(place_id="B", name="NoEmail", email=""),
    ]
    out = merge_rows(rows)
    assert len(out) == 1
    assert out[0]["place_id"] == "A"


def test_keep_no_email_flag():
    rows = [
        _row(place_id="A", email="a@acme.com"),
        _row(place_id="B", email=""),
    ]
    out = merge_rows(rows, require_email=False)
    assert len(out) == 2


def test_duplicate_prefers_row_with_email():
    # First occurrence has no email, a later run enriched the same place_id.
    rows = [
        _row(place_id="A", name="Acme", email=""),
        _row(place_id="A", name="Acme", email="found@acme.com"),
    ]
    out = merge_rows(rows)
    assert len(out) == 1
    assert out[0]["email"] == "found@acme.com"


def test_falls_back_to_website_when_no_place_id():
    rows = [
        _row(place_id="", website="https://acme.com/", email="a@acme.com"),
        _row(place_id="", website="https://acme.com", email="a@acme.com"),
    ]
    out = merge_rows(rows)
    assert len(out) == 1  # same site, trailing slash + case normalized


def test_preserves_first_seen_order():
    rows = [
        _row(place_id="B", email="b@x.com"),
        _row(place_id="A", email="a@x.com"),
    ]
    out = merge_rows(rows)
    assert [r["place_id"] for r in out] == ["B", "A"]


# --------------------------------------------------------------------------
# to_instantly
# --------------------------------------------------------------------------

def test_instantly_maps_name_to_company():
    row = _row(name="Acme Roofing", email="a@acme.com", website="https://acme.com",
               demo_url="https://agentnexlify.com/demo?business=Acme")
    out = to_instantly(row)
    assert out["company_name"] == "Acme Roofing"
    assert out["email"] == "a@acme.com"
    assert out["website"] == "https://acme.com"
    assert out["demo_url"].startswith("https://agentnexlify.com/demo")
    assert set(out.keys()) == set(INSTANTLY_HEADER)


# --------------------------------------------------------------------------
# read/write round-trip
# --------------------------------------------------------------------------

def test_write_standard_and_instantly(tmp_path):
    rows = [_row(place_id="A", name="Acme", email="a@acme.com",
                 website="https://acme.com", phone="555", city="Austin, TX",
                 category="roofing", demo_url="https://d/x")]

    std = tmp_path / "std.csv"
    write_csv(str(std), rows, instantly=False)
    with open(std, newline="", encoding="utf-8") as fh:
        r = list(csv.DictReader(fh))
    assert list(r[0].keys()) == CSV_HEADER
    assert r[0]["name"] == "Acme"

    inst = tmp_path / "inst.csv"
    write_csv(str(inst), rows, instantly=True)
    with open(inst, newline="", encoding="utf-8") as fh:
        r = list(csv.DictReader(fh))
    assert list(r[0].keys()) == INSTANTLY_HEADER
    assert r[0]["company_name"] == "Acme"


def test_write_empty_still_has_header(tmp_path):
    out = tmp_path / "empty.csv"
    write_csv(str(out), [], instantly=False)
    with open(out, newline="", encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    assert lines and lines[0].split(",") == CSV_HEADER


def test_read_csvs_skips_missing(tmp_path):
    real = tmp_path / "real.csv"
    write_csv(str(real), [_row(place_id="A", email="a@x.com")], instantly=False)
    rows = read_csvs([str(real), str(tmp_path / "missing.csv")])
    assert len(rows) == 1


def test_end_to_end_merge_two_files(tmp_path):
    f1 = tmp_path / "city1.csv"
    f2 = tmp_path / "city2.csv"
    write_csv(str(f1), [
        _row(place_id="A", name="Acme", email="a@acme.com"),
        _row(place_id="B", name="Bravo", email="b@bravo.com"),
    ], instantly=False)
    write_csv(str(f2), [
        _row(place_id="B", name="Bravo", email="b@bravo.com"),  # dup across files
        _row(place_id="C", name="Cara", email="c@cara.com"),
    ], instantly=False)

    merged = merge_rows(read_csvs([str(f1), str(f2)]))
    assert {r["place_id"] for r in merged} == {"A", "B", "C"}
    assert len(merged) == 3
