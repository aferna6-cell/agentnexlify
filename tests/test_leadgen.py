"""
Tests for scripts.leadgen package.

All httpx calls are monkeypatched so the suite runs fully offline.
"""

import argparse
import csv
import io
import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Make the repo root importable regardless of where pytest is invoked from.
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.leadgen.enrich import best_email, extract_emails_from_site
from scripts.leadgen.places import is_usable, place_fields, search_text


@pytest.fixture(autouse=True)
def _allow_urls_offline():
    # _fetch_page now runs an SSRF guard (is_safe_url) that resolves DNS via the
    # network. These tests cover email-extraction logic and must stay fully
    # offline, so stub the guard to allow. SSRF guard behavior itself is covered
    # in backend/tests/test_url_safety.py.
    with patch("scripts.leadgen.enrich.is_safe_url", return_value=True):
        yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """Build a mock httpx response."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.text = ""
    mock.raise_for_status.return_value = None
    return mock


def _make_html_response(html: str, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.text = html
    mock.raise_for_status.return_value = None
    # _fetch_page now follows redirects manually; a non-redirect response must
    # report is_redirect=False so the fetch loop returns the body.
    mock.is_redirect = False
    mock.next_request = None
    return mock


# ---------------------------------------------------------------------------
# enrich.extract_emails_from_site
# ---------------------------------------------------------------------------

class TestExtractEmailsFromSite:
    HTML_WITH_MIXED_EMAILS = """
    <html>
    <body>
      <p>Email us at info@roofmaster.com or contact@roofmaster.com</p>
      <p>For careers: jobs@roofmaster.com</p>
      <img src="design@2x.png" />
      <p>Error tracking: errors@sentry.io noreply@sentry.io</p>
      <p>Template placeholder: your@email.com</p>
      <p>Wix: support@wixpress.com</p>
      <p>Asset: logo@2x.jpg</p>
      <p>GoDaddy: admin@godaddy.com</p>
    </body>
    </html>
    """

    def test_good_emails_kept(self):
        html_resp = _make_html_response(self.HTML_WITH_MIXED_EMAILS)
        with patch("httpx.get", return_value=html_resp):
            emails = extract_emails_from_site("https://roofmaster.com")
        assert "info@roofmaster.com" in emails
        assert "contact@roofmaster.com" in emails
        assert "jobs@roofmaster.com" in emails

    def test_junk_emails_filtered(self):
        html_resp = _make_html_response(self.HTML_WITH_MIXED_EMAILS)
        with patch("httpx.get", return_value=html_resp):
            emails = extract_emails_from_site("https://roofmaster.com")
        # Sentry domains
        assert "errors@sentry.io" not in emails
        assert "noreply@sentry.io" not in emails
        # your@email placeholder
        assert "your@email.com" not in emails
        # wixpress
        assert "support@wixpress.com" not in emails
        # godaddy
        assert "admin@godaddy.com" not in emails

    def test_asset_extension_filtered(self):
        html_resp = _make_html_response('<a href="mailto:icon@2x.png">x</a>')
        with patch("httpx.get", return_value=html_resp):
            emails = extract_emails_from_site("https://example.com")
        # "icon@2x" contains "@2x" so filtered
        for e in emails:
            assert "@2x" not in e

    def test_network_error_returns_empty(self):
        import httpx as _httpx
        with patch("httpx.get", side_effect=_httpx.RequestError("timeout")):
            emails = extract_emails_from_site("https://unreachable.example.com")
        assert emails == []

    def test_empty_url_returns_empty(self):
        emails = extract_emails_from_site("")
        assert emails == []

    def test_deduplication(self):
        html = "<p>info@shop.com and INFO@SHOP.COM and info@shop.com</p>"
        resp = _make_html_response(html)
        with patch("httpx.get", return_value=resp):
            emails = extract_emails_from_site("https://shop.com")
        assert emails.count("info@shop.com") == 1

    def test_contact_page_also_fetched(self):
        """Verifies two GET calls are made (homepage + /contact)."""
        resp = _make_html_response("<p>reach@biz.com</p>")
        with patch("httpx.get", return_value=resp) as mock_get:
            extract_emails_from_site("https://biz.com")
        assert mock_get.call_count == 2
        urls_called = [call.args[0] for call in mock_get.call_args_list]
        assert any("biz.com/contact" in u for u in urls_called)


# ---------------------------------------------------------------------------
# enrich.best_email
# ---------------------------------------------------------------------------

class TestBestEmail:
    def test_prefers_info_prefix(self):
        emails = ["sales@co.com", "info@co.com", "ceo@co.com"]
        assert best_email(emails) == "info@co.com"

    def test_prefers_contact_prefix(self):
        emails = ["billing@co.com", "contact@co.com"]
        assert best_email(emails) == "contact@co.com"

    def test_prefers_hello_prefix(self):
        emails = ["noreply@co.com", "hello@co.com"]
        assert best_email(emails) == "hello@co.com"

    def test_prefers_office_prefix(self):
        emails = ["random@co.com", "office@co.com"]
        assert best_email(emails) == "office@co.com"

    def test_falls_back_to_first(self):
        emails = ["team@co.com", "staff@co.com"]
        assert best_email(emails) == "team@co.com"

    def test_none_on_empty(self):
        assert best_email([]) is None

    def test_single_item(self):
        assert best_email(["ceo@co.com"]) == "ceo@co.com"


# ---------------------------------------------------------------------------
# places.is_usable
# ---------------------------------------------------------------------------

class TestIsUsable:
    def test_operational_with_website_true(self):
        p = {"business_status": "OPERATIONAL", "website": "https://example.com"}
        assert is_usable(p) is True

    def test_closed_permanently_false(self):
        p = {"business_status": "CLOSED_PERMANENTLY", "website": "https://example.com"}
        assert is_usable(p) is False

    def test_no_website_false(self):
        p = {"business_status": "OPERATIONAL", "website": ""}
        assert is_usable(p) is False

    def test_missing_both_false(self):
        assert is_usable({}) is False

    def test_closed_temporarily_false(self):
        p = {"business_status": "CLOSED_TEMPORARILY", "website": "https://example.com"}
        assert is_usable(p) is False


# ---------------------------------------------------------------------------
# places.search_text - pagination + deduplication
# ---------------------------------------------------------------------------

def _make_place(n: int) -> dict:
    """Build a minimal Places API place object."""
    return {
        "id": f"place_{n}",
        "displayName": {"text": f"Business {n}"},
        "formattedAddress": f"{n} Main St",
        "nationalPhoneNumber": f"555-000{n:04d}",
        "websiteUri": f"https://biz{n}.com",
        "businessStatus": "OPERATIONAL",
        "rating": 4.5,
        "userRatingCount": 10,
        "primaryType": "roofing_contractor",
    }


class TestSearchText:
    def test_pagination_two_pages(self):
        """Returns results from both pages when nextPageToken present on page 1."""
        page1_places = [_make_place(i) for i in range(20)]
        page2_places = [_make_place(i) for i in range(20, 35)]

        responses = [
            _make_response({"places": page1_places, "nextPageToken": "tok_abc"}),
            _make_response({"places": page2_places}),
        ]

        with patch("httpx.post", side_effect=responses):
            results = search_text("roofing in Austin TX", api_key="fake_key", max_results=60)

        assert len(results) == 35

    def test_pagination_stops_without_token(self):
        """Stops after first page when no nextPageToken returned."""
        page1_places = [_make_place(i) for i in range(15)]
        resp = _make_response({"places": page1_places})

        with patch("httpx.post", return_value=resp) as mock_post:
            results = search_text("dental in Denver CO", api_key="fake_key", max_results=60)

        assert len(results) == 15
        assert mock_post.call_count == 1

    def test_respects_max_results(self):
        """Stops collecting when max_results is reached mid-page."""
        page1_places = [_make_place(i) for i in range(20)]
        page2_places = [_make_place(i) for i in range(20, 40)]

        responses = [
            _make_response({"places": page1_places, "nextPageToken": "tok_xyz"}),
            _make_response({"places": page2_places}),
        ]

        with patch("httpx.post", side_effect=responses):
            results = search_text("plumbing in Houston TX", api_key="fake_key", max_results=25)

        assert len(results) == 25

    def test_deduplicates_place_ids(self):
        """Duplicate place IDs across pages appear only once."""
        dup_place = _make_place(1)
        page1_places = [_make_place(i) for i in range(5)] + [dup_place]
        page2_places = [dup_place, _make_place(99)]  # dup_place repeated

        responses = [
            _make_response({"places": page1_places, "nextPageToken": "tok_dup"}),
            _make_response({"places": page2_places}),
        ]

        with patch("httpx.post", side_effect=responses):
            results = search_text("roofing in Miami FL", api_key="fake_key", max_results=60)

        ids = [r["place_id"] for r in results]
        assert len(ids) == len(set(ids)), "Duplicate place_ids found"

    def test_http_error_returns_partial(self):
        """Returns whatever was collected before the error, does not raise."""
        import httpx as _httpx

        page1_places = [_make_place(i) for i in range(10)]
        responses = [
            _make_response({"places": page1_places, "nextPageToken": "tok_err"}),
        ]
        error_resp = MagicMock()
        error_resp.raise_for_status.side_effect = _httpx.HTTPStatusError(
            "403", request=MagicMock(), response=MagicMock()
        )
        responses.append(error_resp)

        with patch("httpx.post", side_effect=responses):
            results = search_text("roofing in Seattle WA", api_key="fake_key", max_results=60)

        assert len(results) == 10


# ---------------------------------------------------------------------------
# build_leads.run - integration (all external calls monkeypatched)
# ---------------------------------------------------------------------------

class TestBuildLeadsRun:
    def _make_args(self, tmp_path, max_results=10):
        ns = argparse.Namespace(
            vertical="roofing",
            city="Austin, TX",
            out=str(tmp_path / "leads.csv"),
            max=max_results,
            api_key="fake_key_xyz",
            source="auto",  # api_key present -> resolves to google (existing behavior)
        )
        return ns

    def _fake_places(self, n=5):
        return [
            {
                "place_id": f"pid_{i}",
                "name": f"Roofer {i}",
                "category": "roofing_contractor",
                "phone": f"512-000-{i:04d}",
                "website": f"https://roofer{i}.com",
                "address": f"{i} Oak Lane, Austin, TX",
                "rating": 4.2,
                "rating_count": 8,
                "business_status": "OPERATIONAL",
            }
            for i in range(n)
        ]

    def test_csv_written_with_correct_header(self, tmp_path):
        from scripts.leadgen.build_leads import run

        args = self._make_args(tmp_path)
        fake_places = self._fake_places(3)

        with patch("scripts.leadgen.build_leads.search_text", return_value=fake_places), \
             patch("scripts.leadgen.build_leads.enrich_site",
                   return_value={"email": "info@roofer.com", "owner_name": "", "contact_form": ""}):
            run(args)

        with open(str(tmp_path / "leads.csv"), newline="") as fh:
            reader = csv.DictReader(fh)
            # Header expanded 2026-06-18: owner_name + contact_form added by the
            # enrichment upgrade (capture owner + form so the no-email 60% are reachable).
            assert reader.fieldnames == [
                "name", "category", "phone", "website", "email",
                "owner_name", "contact_form",
                "address", "city", "rating", "place_id", "demo_url",
            ]
            rows = list(reader)

        assert len(rows) == 3

    def test_dedup_by_place_id(self, tmp_path):
        """Duplicate place_ids in search results appear only once in CSV."""
        from scripts.leadgen.build_leads import run

        dup = {
            "place_id": "dup_id",
            "name": "Roofer Dup",
            "category": "roofing_contractor",
            "phone": "512-999-0000",
            "website": "https://dupbiz.com",
            "address": "1 Dup St",
            "rating": 4.0,
            "rating_count": 5,
            "business_status": "OPERATIONAL",
        }
        fake_places = [dup, dup]

        args = self._make_args(tmp_path)
        with patch("scripts.leadgen.build_leads.search_text", return_value=fake_places), \
             patch("scripts.leadgen.build_leads.enrich_site",
                   return_value={"email": "", "owner_name": "", "contact_form": ""}):
            run(args)

        with open(str(tmp_path / "leads.csv"), newline="") as fh:
            rows = list(csv.DictReader(fh))

        assert len(rows) == 1
        assert rows[0]["place_id"] == "dup_id"

    def test_demo_url_templated(self, tmp_path):
        """demo_url uses place_id as template param."""
        from scripts.leadgen.build_leads import run

        args = self._make_args(tmp_path)
        fake_places = self._fake_places(1)

        with patch("scripts.leadgen.build_leads.search_text", return_value=fake_places), \
             patch("scripts.leadgen.build_leads.enrich_site",
                   return_value={"email": "", "owner_name": "", "contact_form": ""}):
            run(args)

        with open(str(tmp_path / "leads.csv"), newline="") as fh:
            rows = list(csv.DictReader(fh))

        assert "pid_0" in rows[0]["demo_url"]

    def test_custom_demo_url_template(self, tmp_path, monkeypatch):
        """DEMO_URL_TEMPLATE env var is respected."""
        from scripts.leadgen.build_leads import run

        monkeypatch.setenv(
            "DEMO_URL_TEMPLATE", "https://custom.example.com/demo?id={place_id}"
        )
        args = self._make_args(tmp_path)
        fake_places = self._fake_places(1)

        with patch("scripts.leadgen.build_leads.search_text", return_value=fake_places), \
             patch("scripts.leadgen.build_leads.enrich_site",
                   return_value={"email": "", "owner_name": "", "contact_form": ""}):
            run(args)

        with open(str(tmp_path / "leads.csv"), newline="") as fh:
            rows = list(csv.DictReader(fh))

        assert rows[0]["demo_url"].startswith("https://custom.example.com/demo")

    def test_city_column_set(self, tmp_path):
        from scripts.leadgen.build_leads import run

        args = self._make_args(tmp_path)
        fake_places = self._fake_places(2)

        with patch("scripts.leadgen.build_leads.search_text", return_value=fake_places), \
             patch("scripts.leadgen.build_leads.enrich_site",
                   return_value={"email": "", "owner_name": "", "contact_form": ""}):
            run(args)

        with open(str(tmp_path / "leads.csv"), newline="") as fh:
            rows = list(csv.DictReader(fh))

        for row in rows:
            assert row["city"] == "Austin, TX"

    def test_email_count_in_summary(self, tmp_path, capsys):
        from scripts.leadgen.build_leads import run

        args = self._make_args(tmp_path)
        fake_places = self._fake_places(3)
        enrich_by_call = [
            {"email": "info@a.com", "owner_name": "", "contact_form": ""},
            {"email": "", "owner_name": "", "contact_form": ""},
            {"email": "contact@b.com", "owner_name": "", "contact_form": ""},
        ]

        with patch("scripts.leadgen.build_leads.search_text", return_value=fake_places), \
             patch("scripts.leadgen.build_leads.enrich_site",
                   side_effect=enrich_by_call):
            count = run(args)

        captured = capsys.readouterr()
        assert "2 with email" in captured.out
        assert count == 3

    def test_missing_api_key_exits_when_google_forced(self, tmp_path, monkeypatch):
        # Contract changed (2026-06-18, OSM source added): a missing key only
        # exits when Google is explicitly forced. `--source auto` falls back to
        # the keyless OSM source instead (covered separately below).
        from scripts.leadgen.build_leads import run

        monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
        args = argparse.Namespace(
            vertical="roofing",
            city="Austin, TX",
            out=str(tmp_path / "leads.csv"),
            max=10,
            api_key=None,
            source="google",
        )

        with pytest.raises(SystemExit) as exc_info:
            run(args)

        assert exc_info.value.code == 2

    def test_auto_without_key_falls_back_to_osm(self, tmp_path, monkeypatch):
        from scripts.leadgen.build_leads import run

        monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
        args = argparse.Namespace(
            vertical="roofing",
            city="Austin, TX",
            out=str(tmp_path / "leads.csv"),
            max=10,
            api_key=None,
            source="auto",
        )
        # No key -> auto picks OSM. Stub the OSM source so the run stays offline.
        with patch("scripts.leadgen.build_leads.search_osm", return_value=[]) as mock_osm:
            count = run(args)
        mock_osm.assert_called_once()
        assert count == 0
