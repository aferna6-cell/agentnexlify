"""Tests for enrich.py owner-name + contact-form + enrich_site upgrades. Offline."""

import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.leadgen.enrich import (
    enrich_site,
    extract_owner_name,
    find_contact_form_url,
)


# --------------------------------------------------------------------------
# extract_owner_name — high precision, returns "" unless confident
# --------------------------------------------------------------------------

def test_owner_from_label():
    assert extract_owner_name("<p>Owner: Jane Doe</p>") == "Jane Doe"
    assert extract_owner_name("Founded by John Smith in 1998") == "John Smith"


def test_owner_name_then_role():
    assert extract_owner_name("<h3>Maria Lopez, Owner</h3>") == "Maria Lopez"


def test_owner_from_jsonld():
    html = '<script>{"@type":"Organization","founder":{"name":"Carlos Reyes"}}</script>'
    assert extract_owner_name(html) == "Carlos Reyes"


def test_owner_rejects_company_string():
    # "Acme Roofing LLC" matches the shape but is a company, not a person.
    assert extract_owner_name("<p>Owner: Acme Roofing LLC</p>") == ""


def test_owner_empty_when_absent():
    assert extract_owner_name("<p>We do great roofs.</p>") == ""
    assert extract_owner_name("") == ""


def test_owner_rejects_single_word():
    assert extract_owner_name("Owner: Bob") == ""


# --------------------------------------------------------------------------
# find_contact_form_url
# --------------------------------------------------------------------------

def test_finds_contact_link():
    html = '<a href="/contact-us">Contact</a>'
    assert find_contact_form_url(html, "https://acme.com") == "https://acme.com/contact-us"


def test_finds_quote_link_absolute():
    html = '<a href="https://acme.com/get-a-quote">Free Quote</a>'
    assert find_contact_form_url(html, "https://acme.com") == "https://acme.com/get-a-quote"


def test_skips_mailto_and_anchors():
    html = '<a href="mailto:x@a.com">Email</a><a href="#top">Top</a>'
    assert find_contact_form_url(html, "https://acme.com") == ""


def test_no_contact_link():
    assert find_contact_form_url('<a href="/about">About</a>', "https://acme.com") == ""


# --------------------------------------------------------------------------
# enrich_site — single orchestrator (mock _fetch_page)
# --------------------------------------------------------------------------

def test_enrich_site_homepage_has_everything():
    home = '<p>Owner: Jane Doe</p><a href="/contact">Contact</a> info@acme.com'
    with patch("scripts.leadgen.enrich._fetch_page", return_value=home):
        out = enrich_site("https://acme.com")
    assert out["email"] == "info@acme.com"
    assert out["owner_name"] == "Jane Doe"
    assert out["contact_form"] == "https://acme.com/contact"


def test_enrich_site_falls_back_to_contact_page():
    # Homepage thin; /contact carries the email. _fetch_page called twice.
    pages = ["<p>roofs</p>", "reach us at hello@acme.com"]
    with patch("scripts.leadgen.enrich._fetch_page", side_effect=pages):
        out = enrich_site("https://acme.com")
    assert out["email"] == "hello@acme.com"
    # /contact existed -> usable as a form target even without an explicit link
    assert out["contact_form"] == "https://acme.com/contact"


def test_enrich_site_empty_on_dead_site():
    with patch("scripts.leadgen.enrich._fetch_page", return_value=""):
        out = enrich_site("https://dead.com")
    assert out == {"email": "", "owner_name": "", "contact_form": ""}


def test_enrich_site_blank_url():
    assert enrich_site("") == {"email": "", "owner_name": "", "contact_form": ""}
