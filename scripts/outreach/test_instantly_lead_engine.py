"""Unit tests for the pure helpers in instantly_lead_engine.

Run: python -m pytest scripts/outreach/test_instantly_lead_engine.py
The API-calling paths are intentionally not exercised here (no network).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from instantly_lead_engine import (  # noqa: E402
    normalize_domain,
    build_email,
    build_candidates,
    select_new,
)


def test_normalize_domain_strips_scheme_www_path():
    assert normalize_domain("https://www.Example.com/contact") == "example.com"
    assert normalize_domain("http://foo.org") == "foo.org"
    assert normalize_domain("BAR.NET") == "bar.net"
    assert normalize_domain("") == ""


def test_build_email_prefers_explicit_then_role():
    assert build_email({"email": "owner@x.com"}) == "owner@x.com"
    assert build_email({"domain": "x.com"}) == "info@x.com"
    assert build_email({"website": "https://www.y.io/"}) == "info@y.io"
    assert build_email({"company_name": "No Domain"}) == ""


def test_build_candidates_drops_blank_and_dupes():
    rows = [
        {"company_name": "A", "domain": "a.com"},
        {"company_name": "A dup", "domain": "www.a.com"},   # same email -> dropped
        {"company_name": "B", "email": "b@b.com"},
        {"company_name": "No email", "domain": ""},          # dropped
    ]
    out = build_candidates(rows)
    emails = [c["email"] for c in out]
    assert emails == ["info@a.com", "b@b.com"]


def test_select_new_is_case_insensitive():
    cands = [{"email": "info@a.com", "company_name": "A"},
             {"email": "info@b.com", "company_name": "B"}]
    existing = {"INFO@A.COM"}
    new = select_new(cands, existing)
    assert [c["email"] for c in new] == ["info@b.com"]
