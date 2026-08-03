"""Tests for backend/services/prospecting.py and backend/routers/prospecting.py.

Uses a purpose-built in-memory fake Supabase client (real per-table filtering,
insert/update/upsert semantics) rather than the trivial fake_supabase.Query
helper — dedup and idempotency assertions need filters to actually filter.
"""

import asyncio
import uuid
from datetime import datetime, timezone

import httpx
import pytest

import backend.models.database as _db_module
from backend.routers import prospecting as prospecting_router
from backend.services import prospecting
from backend.tests.conftest import SyncASGITestClient


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Fake Supabase client — real filtering/insert/update/upsert semantics
# ---------------------------------------------------------------------------


class _Result:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class _FakeQuery:
    def __init__(self, store, table):
        self._store = store
        self._table = table
        self._mode = None
        self._pending = None
        self._on_conflict = None
        self._filters = []
        self._order = None
        self._order_desc = False
        self._range = None
        self._limit = None
        self._count = None

    # --- verb entrypoints ---
    def select(self, columns="*", count=None, **_kw):
        self._mode = "select"
        self._count = count
        return self

    def insert(self, rows):
        self._mode = "insert"
        self._pending = rows
        return self

    def update(self, values):
        self._mode = "update"
        self._pending = values
        return self

    def upsert(self, rows, on_conflict=None, **_kw):
        self._mode = "upsert"
        self._pending = rows
        self._on_conflict = on_conflict
        return self

    def delete(self):
        self._mode = "delete"
        return self

    # --- filters/chain ---
    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def in_(self, col, vals):
        self._filters.append((col, set(vals)))
        return self

    def order(self, col, desc=False):
        self._order = col
        self._order_desc = desc
        return self

    def range(self, start, end):
        self._range = (start, end)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def is_(self, col, _val):
        return self

    # --- execution ---
    def _matches(self, row):
        for col, val in self._filters:
            if isinstance(val, set):
                if row.get(col) not in val:
                    return False
            elif row.get(col) != val:
                return False
        return True

    def _rows(self):
        return self._store.setdefault(self._table, [])

    def execute(self):
        rows = self._rows()

        if self._mode == "select":
            matched = [r for r in rows if self._matches(r)]
            total = len(matched)
            if self._order:
                matched = sorted(
                    matched, key=lambda r: r.get(self._order) or "", reverse=self._order_desc
                )
            if self._range:
                start, end = self._range
                matched = matched[start : end + 1]
            elif self._limit is not None:
                matched = matched[: self._limit]
            count = total if self._count else None
            return _Result([dict(r) for r in matched], count=count)

        if self._mode == "insert":
            pending = self._pending if isinstance(self._pending, list) else [self._pending]
            inserted = []
            now = datetime.now(timezone.utc).isoformat()
            for row in pending:
                new_row = dict(row)
                new_row.setdefault("id", str(uuid.uuid4()))
                new_row.setdefault("created_at", now)
                new_row.setdefault("updated_at", now)
                rows.append(new_row)
                inserted.append(dict(new_row))
            return _Result(inserted)

        if self._mode == "update":
            matched = [r for r in rows if self._matches(r)]
            for row in matched:
                row.update(self._pending)
                row["updated_at"] = datetime.now(timezone.utc).isoformat()
            return _Result([dict(r) for r in matched])

        if self._mode == "upsert":
            pending = self._pending if isinstance(self._pending, list) else [self._pending]
            conflict_cols = (self._on_conflict or "").split(",") if self._on_conflict else []
            result_rows = []
            now = datetime.now(timezone.utc).isoformat()
            for row in pending:
                existing = None
                if conflict_cols:
                    for r in rows:
                        if all(r.get(c) == row.get(c) for c in conflict_cols):
                            existing = r
                            break
                if existing is not None:
                    existing.update(row)
                    existing["updated_at"] = now
                    result_rows.append(dict(existing))
                else:
                    new_row = dict(row)
                    new_row.setdefault("id", str(uuid.uuid4()))
                    new_row.setdefault("created_at", now)
                    new_row.setdefault("updated_at", now)
                    rows.append(new_row)
                    result_rows.append(dict(new_row))
            return _Result(result_rows)

        if self._mode == "delete":
            matched = [r for r in rows if self._matches(r)]
            for r in matched:
                rows.remove(r)
            return _Result([dict(r) for r in matched])

        raise AssertionError(f"Unsupported query mode: {self._mode}")


class FakeDB:
    """Minimal Supabase-client stand-in: db.table(name) -> chainable query."""

    def __init__(self):
        self._store: dict[str, list[dict]] = {}

    def table(self, name):
        return _FakeQuery(self._store, name)

    def seed(self, table, rows):
        self._store.setdefault(table, []).extend(dict(r) for r in rows)


@pytest.fixture()
def fake_db():
    return FakeDB()


_CLIENT_ID = "11111111-1111-1111-1111-111111111111"


def _make_place(place_id="place-1", name="Ace Plumbing", website="https://ace-plumbing.example.com"):
    return {
        "id": place_id,
        "displayName": {"text": name},
        "formattedAddress": "123 Main St, Austin, TX",
        "nationalPhoneNumber": "(512) 555-0100",
        "websiteUri": website,
        "businessStatus": "OPERATIONAL",
        "rating": 4.6,
        "userRatingCount": 120,
        "primaryType": "plumber",
    }


# ---------------------------------------------------------------------------
# discover() — upsert + dedup
# ---------------------------------------------------------------------------


def test_discover_raises_not_configured_when_no_api_key(fake_db, monkeypatch):
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "")
    with pytest.raises(prospecting.ProspectingNotConfigured):
        run(prospecting.discover(fake_db, client_id=_CLIENT_ID, query="plumber", location="Austin, TX"))


def test_discover_upserts_places_into_prospects(fake_db, monkeypatch):
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "test-key")

    async def fake_search(text_query, api_key, page_size):
        assert api_key == "test-key"
        return [_make_place()]

    monkeypatch.setattr(prospecting, "_search_places_text", fake_search)

    rows = run(
        prospecting.discover(fake_db, client_id=_CLIENT_ID, query="plumber", location="Austin, TX", limit=10)
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["client_id"] == _CLIENT_ID
    assert row["source"] == "places_api"
    assert row["external_ref"] == "place-1"
    assert row["business_name"] == "Ace Plumbing"
    assert row["status"] == "new"
    assert row["city"] == "Austin"
    assert row["region"] == "TX"
    assert row["enrichment"]["rating"] == 4.6


def test_discover_dedups_on_second_call(fake_db, monkeypatch):
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "test-key")

    async def fake_search(text_query, api_key, page_size):
        return [_make_place()]

    monkeypatch.setattr(prospecting, "_search_places_text", fake_search)

    run(prospecting.discover(fake_db, client_id=_CLIENT_ID, query="plumber", location="Austin, TX"))
    run(prospecting.discover(fake_db, client_id=_CLIENT_ID, query="plumber", location="Austin, TX"))

    all_rows = fake_db._store.get("prospects", [])
    assert len(all_rows) == 1


def test_discover_skips_places_without_id(fake_db, monkeypatch):
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "test-key")

    async def fake_search(text_query, api_key, page_size):
        broken = _make_place()
        broken["id"] = ""
        return [broken]

    monkeypatch.setattr(prospecting, "_search_places_text", fake_search)

    rows = run(prospecting.discover(fake_db, client_id=_CLIENT_ID, query="plumber", location="Austin, TX"))
    assert rows == []


def test_discover_search_places_http_error_propagates(fake_db, monkeypatch):
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "test-key")

    async def boom(text_query, api_key, page_size):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(prospecting, "_search_places_text", boom)

    with pytest.raises(httpx.HTTPError):
        run(prospecting.discover(fake_db, client_id=_CLIENT_ID, query="plumber", location="Austin, TX"))


def test_discover_upsert_failure_propagates(fake_db, monkeypatch):
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "test-key")

    async def fake_search(text_query, api_key, page_size):
        return [_make_place()]

    monkeypatch.setattr(prospecting, "_search_places_text", fake_search)

    def boom(*a, **k):
        raise RuntimeError("upsert boom")

    monkeypatch.setattr(prospecting, "tenant_upsert", boom)

    with pytest.raises(RuntimeError):
        run(prospecting.discover(fake_db, client_id=_CLIENT_ID, query="plumber", location="Austin, TX"))


class _FakePlacesAsyncClient:
    """Fake httpx.AsyncClient for direct _search_places_text() coverage."""

    def __init__(self, response, timeout=None):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, headers=None, json=None):
        self.last_call = (url, headers, json)
        return self._response


class _FakePlacesResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_search_places_text_returns_places_list(monkeypatch):
    fake_response = _FakePlacesResponse({"places": [{"id": "raw-place-1"}]})
    monkeypatch.setattr(
        prospecting.httpx,
        "AsyncClient",
        lambda timeout=None: _FakePlacesAsyncClient(fake_response),
    )
    result = run(prospecting._search_places_text("plumber Austin, TX", "key-123", 10))
    assert result == [{"id": "raw-place-1"}]


# ---------------------------------------------------------------------------
# enrich_prospect() — regex extraction from fixture HTML
# ---------------------------------------------------------------------------

_FIXTURE_HTML = """
<html><body>
<p>Call us at (512) 555-0199 or email info@ace-plumbing.example.com</p>
<p>Error tracking: errors@sentry.io</p>
</body></html>
"""


def test_enrich_prospect_extracts_email_and_phone(fake_db, monkeypatch):
    fake_db.seed(
        "prospects",
        [
            {
                "id": "p1",
                "client_id": _CLIENT_ID,
                "website": "https://ace-plumbing.example.com",
                "email": None,
                "phone": None,
                "enrichment": {},
                "status": "new",
            }
        ],
    )

    async def fake_fetch(url):
        assert url == "https://ace-plumbing.example.com"
        return _FIXTURE_HTML

    monkeypatch.setattr(prospecting, "_fetch_page_text", fake_fetch)

    updated = run(prospecting.enrich_prospect(fake_db, client_id=_CLIENT_ID, prospect_id="p1"))
    assert updated["email"] == "info@ace-plumbing.example.com"
    assert updated["phone"] == "(512) 555-0199"
    assert updated["status"] == "enriched"
    assert updated["enrichment"]["page_fetched"] is True


def test_enrich_prospect_skips_junk_email(fake_db, monkeypatch):
    fake_db.seed(
        "prospects",
        [
            {
                "id": "p2",
                "client_id": _CLIENT_ID,
                "website": "https://sentry-only.example.com",
                "email": None,
                "phone": None,
                "enrichment": {},
                "status": "new",
            }
        ],
    )

    async def fake_fetch(url):
        return "<p>Only contact: errors@sentry.io</p>"

    monkeypatch.setattr(prospecting, "_fetch_page_text", fake_fetch)

    updated = run(prospecting.enrich_prospect(fake_db, client_id=_CLIENT_ID, prospect_id="p2"))
    assert updated["email"] is None
    assert updated["status"] == "enriched"


def test_enrich_prospect_returns_none_for_missing_prospect(fake_db, monkeypatch):
    result = run(prospecting.enrich_prospect(fake_db, client_id=_CLIENT_ID, prospect_id="ghost"))
    assert result is None


def test_enrich_prospect_never_crashes_on_fetch_failure(fake_db, monkeypatch):
    fake_db.seed(
        "prospects",
        [
            {
                "id": "p3",
                "client_id": _CLIENT_ID,
                "website": "https://down.example.com",
                "email": None,
                "phone": None,
                "enrichment": {},
                "status": "new",
            }
        ],
    )

    async def fake_fetch(url):
        return ""  # _fetch_page_text degrades to "" on any failure

    monkeypatch.setattr(prospecting, "_fetch_page_text", fake_fetch)

    updated = run(prospecting.enrich_prospect(fake_db, client_id=_CLIENT_ID, prospect_id="p3"))
    assert updated["status"] == "enriched"
    assert updated["email"] is None


def test_enrich_prospect_update_failure_propagates(fake_db, monkeypatch):
    fake_db.seed(
        "prospects",
        [
            {
                "id": "p9",
                "client_id": _CLIENT_ID,
                "website": "",
                "email": None,
                "phone": None,
                "enrichment": {},
                "status": "new",
            }
        ],
    )

    def boom(*a, **k):
        raise RuntimeError("update boom")

    monkeypatch.setattr(prospecting, "tenant_update", boom)

    with pytest.raises(RuntimeError):
        run(prospecting.enrich_prospect(fake_db, client_id=_CLIENT_ID, prospect_id="p9"))


# ---------------------------------------------------------------------------
# _fetch_page_text() — direct coverage of the graceful-degrade fetch helper
# ---------------------------------------------------------------------------


class _FakeFetchAsyncClient:
    def __init__(self, response=None, raises=None, timeout=None, follow_redirects=None):
        self._response = response
        self._raises = raises

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, headers=None):
        if self._raises:
            raise self._raises
        return self._response


class _FakeFetchResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text


def test_fetch_page_text_empty_url_returns_empty_string():
    assert run(prospecting._fetch_page_text("")) == ""


def test_fetch_page_text_unsafe_url_skipped(monkeypatch):
    monkeypatch.setattr(prospecting, "is_safe_url", lambda u: False)
    assert run(prospecting._fetch_page_text("http://169.254.169.254/secret")) == ""


def test_fetch_page_text_adds_https_prefix_and_returns_body(monkeypatch):
    monkeypatch.setattr(prospecting, "is_safe_url", lambda u: True)
    fake_response = _FakeFetchResponse(200, "hello from ace plumbing")

    monkeypatch.setattr(
        prospecting.httpx,
        "AsyncClient",
        lambda timeout=None, follow_redirects=None: _FakeFetchAsyncClient(response=fake_response),
    )
    text = run(prospecting._fetch_page_text("ace-plumbing.example.com"))
    assert text == "hello from ace plumbing"


def test_fetch_page_text_non_200_returns_empty(monkeypatch):
    monkeypatch.setattr(prospecting, "is_safe_url", lambda u: True)
    fake_response = _FakeFetchResponse(404, "")
    monkeypatch.setattr(
        prospecting.httpx,
        "AsyncClient",
        lambda timeout=None, follow_redirects=None: _FakeFetchAsyncClient(response=fake_response),
    )
    assert run(prospecting._fetch_page_text("https://down.example.com")) == ""


def test_fetch_page_text_http_error_returns_empty(monkeypatch):
    monkeypatch.setattr(prospecting, "is_safe_url", lambda u: True)
    monkeypatch.setattr(
        prospecting.httpx,
        "AsyncClient",
        lambda timeout=None, follow_redirects=None: _FakeFetchAsyncClient(raises=httpx.ConnectError("boom")),
    )
    assert run(prospecting._fetch_page_text("https://unreachable.example.com")) == ""


def test_is_junk_email_flags_image_suffix():
    assert prospecting._is_junk_email("logo@cdn.example.png") is True


def test_extract_phone_normalizes_11_digit_leading_country_code():
    phone = prospecting._extract_phone("Call 1-512-555-0199 for a quote")
    assert phone == "(512) 555-0199"


# ---------------------------------------------------------------------------
# verify_email() — fail-open provider abstraction
# ---------------------------------------------------------------------------


def test_verify_email_syntax_only_accepts_valid(monkeypatch):
    monkeypatch.setattr(prospecting.settings, "email_verify_provider", "none")
    assert prospecting.verify_email("owner@example.com") is True


def test_verify_email_syntax_only_rejects_invalid(monkeypatch):
    monkeypatch.setattr(prospecting.settings, "email_verify_provider", "none")
    assert prospecting.verify_email("not-an-email") is False


def test_verify_email_empty_string_is_false(monkeypatch):
    assert prospecting.verify_email("") is False


def test_verify_email_zerobounce_fails_open_on_network_error(monkeypatch):
    monkeypatch.setattr(prospecting.settings, "email_verify_provider", "zerobounce")
    monkeypatch.setattr(prospecting.settings, "email_verify_api_key", "zb-key")

    def boom(*a, **k):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(prospecting.httpx, "get", boom)

    assert prospecting.verify_email("owner@example.com") is False


def test_verify_email_zerobounce_missing_key_falls_back_to_syntax(monkeypatch):
    monkeypatch.setattr(prospecting.settings, "email_verify_provider", "zerobounce")
    monkeypatch.setattr(prospecting.settings, "email_verify_api_key", "")
    assert prospecting.verify_email("owner@example.com") is True
    assert prospecting.verify_email("not-an-email") is False


class _FakeZeroBounceResponse:
    def __init__(self, status):
        self._status = status

    def raise_for_status(self):
        return None

    def json(self):
        return {"status": self._status}


def test_verify_email_zerobounce_valid_status_returns_true(monkeypatch):
    monkeypatch.setattr(prospecting.settings, "email_verify_provider", "zerobounce")
    monkeypatch.setattr(prospecting.settings, "email_verify_api_key", "zb-key")
    monkeypatch.setattr(
        prospecting.httpx, "get", lambda *a, **k: _FakeZeroBounceResponse("valid")
    )
    assert prospecting.verify_email("owner@example.com") is True


def test_verify_email_zerobounce_invalid_status_returns_false(monkeypatch):
    monkeypatch.setattr(prospecting.settings, "email_verify_provider", "zerobounce")
    monkeypatch.setattr(prospecting.settings, "email_verify_api_key", "zb-key")
    monkeypatch.setattr(
        prospecting.httpx, "get", lambda *a, **k: _FakeZeroBounceResponse("invalid")
    )
    assert prospecting.verify_email("owner@example.com") is False


def test_verify_email_syntax_only_generic_error_fails_open(monkeypatch):
    import email_validator

    def boom(*a, **k):
        raise RuntimeError("unexpected validator crash")

    monkeypatch.setattr(email_validator, "validate_email", boom)
    assert prospecting._verify_email_syntax_only("owner@example.com") is False


# ---------------------------------------------------------------------------
# score_prospect() — deterministic rubric
# ---------------------------------------------------------------------------


def test_score_prospect_full_marks():
    row = {
        "website": "https://example.com",
        "phone": "(512) 555-0100",
        "email": "owner@example.com",
        "email_verified": True,
        "category": "plumber",
        "enrichment": {"rating": 4.8},
    }
    # Rubric max: website 20 + phone 15 + verified email 30 + category 10 + high rating 15 = 90
    assert prospecting.score_prospect(row) == 90.0


def test_score_prospect_bare_row_scores_zero():
    assert prospecting.score_prospect({}) == 0.0


def test_score_prospect_unverified_email_scores_lower_than_verified():
    base = {"website": "https://x.com", "phone": "555", "category": "hvac", "enrichment": {}}
    unverified = prospecting.score_prospect({**base, "email": "a@b.com", "email_verified": False})
    verified = prospecting.score_prospect({**base, "email": "a@b.com", "email_verified": True})
    assert verified > unverified


def test_score_prospect_is_deterministic():
    row = {"website": "https://x.com", "phone": "555", "category": "hvac", "enrichment": {"rating": 3.5}}
    assert prospecting.score_prospect(row) == prospecting.score_prospect(row)


def test_score_prospect_mid_rating_scores_less_than_high_rating():
    base = {"website": "https://x.com"}
    mid = prospecting.score_prospect({**base, "enrichment": {"rating": 3.2}})
    high = prospecting.score_prospect({**base, "enrichment": {"rating": 4.5}})
    assert high > mid


def test_score_prospect_unparseable_rating_ignored_not_crashed():
    row = {"website": "https://x.com", "enrichment": {"rating": "not-a-number"}}
    # website(20) counted, rating ignored (unparseable) -> no rating bonus.
    assert prospecting.score_prospect(row) == 20.0


# ---------------------------------------------------------------------------
# promote_to_lead() — creates lead, idempotent
# ---------------------------------------------------------------------------


def test_promote_to_lead_creates_lead_with_prospecting_source(fake_db):
    fake_db.seed(
        "prospects",
        [
            {
                "id": "p10",
                "client_id": _CLIENT_ID,
                "business_name": "Ace Plumbing",
                "email": "owner@ace-plumbing.example.com",
                "phone": "(512) 555-0100",
                "category": "plumber",
                "status": "qualified",
                "promoted_lead_id": None,
            }
        ],
    )

    lead = run(prospecting.promote_to_lead(fake_db, client_id=_CLIENT_ID, prospect_id="p10"))
    assert lead is not None
    assert lead["client_id"] == _CLIENT_ID
    assert lead["source"] == "prospecting"
    assert lead["name"] == "Ace Plumbing"
    assert lead["email"] == "owner@ace-plumbing.example.com"
    assert lead["status"] == "new"

    prospect_rows = [r for r in fake_db._store["prospects"] if r["id"] == "p10"]
    assert prospect_rows[0]["status"] == "promoted"
    assert prospect_rows[0]["promoted_lead_id"] == lead["id"]


def test_promote_to_lead_is_idempotent(fake_db):
    fake_db.seed(
        "prospects",
        [
            {
                "id": "p11",
                "client_id": _CLIENT_ID,
                "business_name": "Beta HVAC",
                "email": "owner@beta-hvac.example.com",
                "phone": "555",
                "category": "hvac",
                "status": "qualified",
                "promoted_lead_id": None,
            }
        ],
    )

    first = run(prospecting.promote_to_lead(fake_db, client_id=_CLIENT_ID, prospect_id="p11"))
    second = run(prospecting.promote_to_lead(fake_db, client_id=_CLIENT_ID, prospect_id="p11"))

    assert first["id"] == second["id"]
    leads = [r for r in fake_db._store["leads"] if r["client_id"] == _CLIENT_ID]
    assert len(leads) == 1


def test_promote_to_lead_dedupes_against_existing_lead_by_email(fake_db):
    fake_db.seed(
        "leads",
        [
            {
                "id": "existing-lead",
                "client_id": _CLIENT_ID,
                "email": "shared@example.com",
                "name": "Already A Lead",
                "status": "new",
            }
        ],
    )
    fake_db.seed(
        "prospects",
        [
            {
                "id": "p12",
                "client_id": _CLIENT_ID,
                "business_name": "Gamma Roofing",
                "email": "shared@example.com",
                "phone": "555",
                "category": "roofing",
                "status": "qualified",
                "promoted_lead_id": None,
            }
        ],
    )

    lead = run(prospecting.promote_to_lead(fake_db, client_id=_CLIENT_ID, prospect_id="p12"))
    assert lead["id"] == "existing-lead"
    leads = [r for r in fake_db._store["leads"] if r["client_id"] == _CLIENT_ID]
    assert len(leads) == 1


def test_promote_to_lead_returns_none_for_missing_prospect(fake_db):
    result = run(prospecting.promote_to_lead(fake_db, client_id=_CLIENT_ID, prospect_id="ghost"))
    assert result is None


def test_promote_to_lead_insert_failure_propagates(fake_db, monkeypatch):
    fake_db.seed(
        "prospects",
        [
            {
                "id": "p20",
                "client_id": _CLIENT_ID,
                "business_name": "Insert Boom Co",
                "email": None,
                "phone": None,
                "category": None,
                "status": "qualified",
                "promoted_lead_id": None,
            }
        ],
    )

    def boom(*a, **k):
        raise RuntimeError("insert boom")

    monkeypatch.setattr(prospecting, "tenant_insert", boom)

    with pytest.raises(RuntimeError):
        run(prospecting.promote_to_lead(fake_db, client_id=_CLIENT_ID, prospect_id="p20"))


def test_promote_to_lead_insert_returns_no_rows_returns_none(fake_db, monkeypatch):
    fake_db.seed(
        "prospects",
        [
            {
                "id": "p21",
                "client_id": _CLIENT_ID,
                "business_name": "Empty Insert Co",
                "email": None,
                "phone": None,
                "category": None,
                "status": "qualified",
                "promoted_lead_id": None,
            }
        ],
    )

    class _EmptyResult:
        data = []

    class _EmptyInsertQuery:
        def execute(self):
            return _EmptyResult()

    monkeypatch.setattr(
        prospecting, "tenant_insert", lambda db, table, client_id, rows: _EmptyInsertQuery()
    )

    result = run(prospecting.promote_to_lead(fake_db, client_id=_CLIENT_ID, prospect_id="p21"))
    assert result is None


def test_promote_to_lead_status_update_failure_propagates(fake_db, monkeypatch):
    fake_db.seed(
        "prospects",
        [
            {
                "id": "p22",
                "client_id": _CLIENT_ID,
                "business_name": "Status Update Boom Co",
                "email": "p22@example.com",
                "phone": None,
                "category": None,
                "status": "qualified",
                "promoted_lead_id": None,
            }
        ],
    )

    def boom(*a, **k):
        raise RuntimeError("status update boom")

    monkeypatch.setattr(prospecting, "tenant_update", boom)

    with pytest.raises(RuntimeError):
        run(prospecting.promote_to_lead(fake_db, client_id=_CLIENT_ID, prospect_id="p22"))


# ---------------------------------------------------------------------------
# run_pipeline() — orchestration + auto-promote
# ---------------------------------------------------------------------------


def test_run_pipeline_discovers_enriches_and_scores(fake_db, monkeypatch):
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "test-key")
    monkeypatch.setattr(prospecting.settings, "email_verify_provider", "none")

    async def fake_search(text_query, api_key, page_size):
        return [_make_place()]

    async def fake_fetch(url):
        return "<p>info@ace-plumbing.example.com (512) 555-0199</p>"

    monkeypatch.setattr(prospecting, "_search_places_text", fake_search)
    monkeypatch.setattr(prospecting, "_fetch_page_text", fake_fetch)

    summary = run(
        prospecting.run_pipeline(
            fake_db, client_id=_CLIENT_ID, query="plumber", location="Austin, TX", limit=5
        )
    )
    assert summary["discovered"] == 1
    assert summary["enriched"] == 1
    assert summary["scored"] == 1
    assert summary["promoted"] == 0
    assert summary["prospects"][0]["score"] > 0


def test_run_pipeline_auto_promotes_above_threshold(fake_db, monkeypatch):
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "test-key")
    monkeypatch.setattr(prospecting.settings, "email_verify_provider", "none")

    async def fake_search(text_query, api_key, page_size):
        return [_make_place()]

    async def fake_fetch(url):
        return "<p>info@ace-plumbing.example.com (512) 555-0199</p>"

    monkeypatch.setattr(prospecting, "_search_places_text", fake_search)
    monkeypatch.setattr(prospecting, "_fetch_page_text", fake_fetch)

    summary = run(
        prospecting.run_pipeline(
            fake_db,
            client_id=_CLIENT_ID,
            query="plumber",
            location="Austin, TX",
            limit=5,
            auto_promote_threshold=0.0,
        )
    )
    assert summary["promoted"] == 1
    leads = [r for r in fake_db._store.get("leads", []) if r["client_id"] == _CLIENT_ID]
    assert len(leads) == 1
    assert leads[0]["source"] == "prospecting"


def test_run_pipeline_continues_when_enrichment_step_raises(fake_db, monkeypatch):
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "test-key")
    monkeypatch.setattr(prospecting.settings, "email_verify_provider", "none")

    async def fake_search(text_query, api_key, page_size):
        return [_make_place()]

    monkeypatch.setattr(prospecting, "_search_places_text", fake_search)

    async def boom_enrich(db, *, client_id, prospect_id):
        raise RuntimeError("enrich boom")

    monkeypatch.setattr(prospecting, "enrich_prospect", boom_enrich)

    summary = run(
        prospecting.run_pipeline(
            fake_db, client_id=_CLIENT_ID, query="plumber", location="Austin, TX", limit=5
        )
    )
    assert summary["discovered"] == 1
    assert summary["enriched"] == 1
    assert summary["scored"] == 1


def test_run_pipeline_continues_when_score_persist_raises(fake_db, monkeypatch):
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "test-key")
    monkeypatch.setattr(prospecting.settings, "email_verify_provider", "none")

    async def fake_search(text_query, api_key, page_size):
        return [_make_place()]

    async def fake_fetch(url):
        return ""

    monkeypatch.setattr(prospecting, "_search_places_text", fake_search)
    monkeypatch.setattr(prospecting, "_fetch_page_text", fake_fetch)

    real_tenant_update = prospecting.tenant_update

    def flaky_tenant_update(db, table, client_id, values):
        if "score" in values:
            raise RuntimeError("score persist boom")
        return real_tenant_update(db, table, client_id, values)

    monkeypatch.setattr(prospecting, "tenant_update", flaky_tenant_update)

    summary = run(
        prospecting.run_pipeline(
            fake_db, client_id=_CLIENT_ID, query="plumber", location="Austin, TX", limit=5
        )
    )
    assert summary["scored"] == 1
    assert "score" in summary["prospects"][0]


def test_run_pipeline_continues_when_auto_promote_raises(fake_db, monkeypatch):
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "test-key")
    monkeypatch.setattr(prospecting.settings, "email_verify_provider", "none")

    async def fake_search(text_query, api_key, page_size):
        return [_make_place()]

    async def fake_fetch(url):
        return "<p>info@ace-plumbing.example.com (512) 555-0199</p>"

    monkeypatch.setattr(prospecting, "_search_places_text", fake_search)
    monkeypatch.setattr(prospecting, "_fetch_page_text", fake_fetch)

    async def boom_promote(db, *, client_id, prospect_id):
        raise RuntimeError("promote boom")

    monkeypatch.setattr(prospecting, "promote_to_lead", boom_promote)

    summary = run(
        prospecting.run_pipeline(
            fake_db,
            client_id=_CLIENT_ID,
            query="plumber",
            location="Austin, TX",
            limit=5,
            auto_promote_threshold=0.0,
        )
    )
    assert summary["promoted"] == 0


# ---------------------------------------------------------------------------
# Router — auth, plan gate, not-configured 422 (never 500)
# ---------------------------------------------------------------------------


@pytest.fixture()
def prospecting_app():
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(prospecting_router.router)
    return app


@pytest.fixture()
def prospecting_client(prospecting_app):
    test_client = SyncASGITestClient(prospecting_app)
    try:
        yield test_client
    finally:
        test_client.close()


def _wire_fake_db(monkeypatch, fake_db):
    monkeypatch.setattr(_db_module, "_service_client", fake_db)


def test_status_endpoint_requires_auth(prospecting_client):
    resp = prospecting_client.get("/api/v1/prospecting/status")
    # No Authorization header at all -> FastAPI's own required-Header
    # validation fires before get_current_tenant's body runs (422, not 401).
    assert resp.status_code == 422


def test_search_blocked_for_non_agent_os_plan(
    prospecting_client, fake_db, monkeypatch, auth_headers_for
):
    fake_db.seed("tenants", [{"id": _CLIENT_ID, "plan": "chatbot"}])
    _wire_fake_db(monkeypatch, fake_db)

    resp = prospecting_client.post(
        f"/api/v1/prospecting/search?tenant_id={_CLIENT_ID}",
        json={"query": "plumber", "location": "Austin, TX"},
        headers=auth_headers_for(_CLIENT_ID),
    )
    assert resp.status_code == 402


def test_search_returns_422_not_500_when_not_configured(
    prospecting_client, fake_db, monkeypatch, auth_headers_for
):
    fake_db.seed("tenants", [{"id": _CLIENT_ID, "plan": "agent_os"}])
    _wire_fake_db(monkeypatch, fake_db)
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "")

    resp = prospecting_client.post(
        f"/api/v1/prospecting/search?tenant_id={_CLIENT_ID}",
        json={"query": "plumber", "location": "Austin, TX"},
        headers=auth_headers_for(_CLIENT_ID),
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["error"] == "prospecting_not_configured"


def test_search_succeeds_for_agent_os_plan(
    prospecting_client, fake_db, monkeypatch, auth_headers_for
):
    fake_db.seed("tenants", [{"id": _CLIENT_ID, "plan": "agent_os"}])
    _wire_fake_db(monkeypatch, fake_db)
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "test-key")

    async def fake_search(text_query, api_key, page_size):
        return [_make_place()]

    async def fake_fetch(url):
        return ""

    monkeypatch.setattr(prospecting, "_search_places_text", fake_search)
    monkeypatch.setattr(prospecting, "_fetch_page_text", fake_fetch)

    resp = prospecting_client.post(
        f"/api/v1/prospecting/search?tenant_id={_CLIENT_ID}",
        json={"query": "plumber", "location": "Austin, TX", "limit": 5},
        headers=auth_headers_for(_CLIENT_ID),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["discovered"] == 1


def test_search_returns_503_on_unexpected_error(
    prospecting_client, fake_db, monkeypatch, auth_headers_for
):
    fake_db.seed("tenants", [{"id": _CLIENT_ID, "plan": "agent_os"}])
    _wire_fake_db(monkeypatch, fake_db)

    async def boom(*a, **k):
        raise RuntimeError("pipeline boom")

    monkeypatch.setattr(prospecting_router, "run_pipeline", boom)

    resp = prospecting_client.post(
        f"/api/v1/prospecting/search?tenant_id={_CLIENT_ID}",
        json={"query": "plumber", "location": "Austin, TX"},
        headers=auth_headers_for(_CLIENT_ID),
    )
    assert resp.status_code == 503


def test_list_prospects_uses_claims_tenant_id_when_omitted(
    prospecting_client, fake_db, monkeypatch, auth_headers_for
):
    fake_db.seed("tenants", [{"id": _CLIENT_ID, "plan": "agent_os"}])
    fake_db.seed(
        "prospects",
        [{"id": "p40", "client_id": _CLIENT_ID, "status": "new", "business_name": "Ace"}],
    )
    _wire_fake_db(monkeypatch, fake_db)

    resp = prospecting_client.get(
        "/api/v1/prospecting/prospects",
        headers=auth_headers_for(_CLIENT_ID),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["prospects"][0]["id"] == "p40"
    assert body["page"] == 1
    assert body["per_page"] == 50


def test_list_prospects_status_filter_with_explicit_tenant_id(
    prospecting_client, fake_db, monkeypatch, auth_headers_for
):
    fake_db.seed("tenants", [{"id": _CLIENT_ID, "plan": "agent_os"}])
    fake_db.seed(
        "prospects",
        [
            {"id": "p41", "client_id": _CLIENT_ID, "status": "new"},
            {"id": "p42", "client_id": _CLIENT_ID, "status": "qualified"},
        ],
    )
    _wire_fake_db(monkeypatch, fake_db)

    resp = prospecting_client.get(
        f"/api/v1/prospecting/prospects?tenant_id={_CLIENT_ID}&status=qualified",
        headers=auth_headers_for(_CLIENT_ID),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["prospects"][0]["id"] == "p42"


def test_list_prospects_db_failure_returns_503(
    prospecting_client, fake_db, monkeypatch, auth_headers_for
):
    fake_db.seed("tenants", [{"id": _CLIENT_ID, "plan": "agent_os"}])
    _wire_fake_db(monkeypatch, fake_db)

    def boom(*a, **k):
        raise RuntimeError("select boom")

    monkeypatch.setattr(prospecting_router, "tenant_select", boom)

    resp = prospecting_client.get(
        f"/api/v1/prospecting/prospects?tenant_id={_CLIENT_ID}",
        headers=auth_headers_for(_CLIENT_ID),
    )
    assert resp.status_code == 503


def test_enrich_prospect_endpoint_happy_path(
    prospecting_client, fake_db, monkeypatch, auth_headers_for
):
    fake_db.seed("tenants", [{"id": _CLIENT_ID, "plan": "agent_os"}])
    fake_db.seed(
        "prospects",
        [
            {
                "id": "p43",
                "client_id": _CLIENT_ID,
                "website": "",
                "email": None,
                "phone": None,
                "enrichment": {},
                "status": "new",
            }
        ],
    )
    _wire_fake_db(monkeypatch, fake_db)

    resp = prospecting_client.post(
        f"/api/v1/prospecting/prospects/p43/enrich?tenant_id={_CLIENT_ID}",
        headers=auth_headers_for(_CLIENT_ID),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "enriched"


def test_enrich_prospect_endpoint_not_found_404(
    prospecting_client, fake_db, monkeypatch, auth_headers_for
):
    fake_db.seed("tenants", [{"id": _CLIENT_ID, "plan": "agent_os"}])
    _wire_fake_db(monkeypatch, fake_db)

    resp = prospecting_client.post(
        f"/api/v1/prospecting/prospects/ghost/enrich?tenant_id={_CLIENT_ID}",
        headers=auth_headers_for(_CLIENT_ID),
    )
    assert resp.status_code == 404


def test_enrich_prospect_endpoint_failure_returns_503(
    prospecting_client, fake_db, monkeypatch, auth_headers_for
):
    fake_db.seed("tenants", [{"id": _CLIENT_ID, "plan": "agent_os"}])
    _wire_fake_db(monkeypatch, fake_db)

    async def boom(*a, **k):
        raise RuntimeError("enrich boom")

    monkeypatch.setattr(prospecting_router, "enrich_prospect", boom)

    resp = prospecting_client.post(
        f"/api/v1/prospecting/prospects/p1/enrich?tenant_id={_CLIENT_ID}",
        headers=auth_headers_for(_CLIENT_ID),
    )
    assert resp.status_code == 503


def test_promote_prospect_endpoint_happy_path_omitted_tenant_id(
    prospecting_client, fake_db, monkeypatch, auth_headers_for
):
    fake_db.seed("tenants", [{"id": _CLIENT_ID, "plan": "agent_os"}])
    fake_db.seed(
        "prospects",
        [
            {
                "id": "p44",
                "client_id": _CLIENT_ID,
                "business_name": "Delta Roofing",
                "email": "p44@example.com",
                "phone": None,
                "category": None,
                "status": "qualified",
                "promoted_lead_id": None,
            }
        ],
    )
    _wire_fake_db(monkeypatch, fake_db)

    resp = prospecting_client.post(
        "/api/v1/prospecting/prospects/p44/promote",
        headers=auth_headers_for(_CLIENT_ID),
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "p44@example.com"


def test_promote_prospect_endpoint_not_found_404(
    prospecting_client, fake_db, monkeypatch, auth_headers_for
):
    fake_db.seed("tenants", [{"id": _CLIENT_ID, "plan": "agent_os"}])
    _wire_fake_db(monkeypatch, fake_db)

    resp = prospecting_client.post(
        f"/api/v1/prospecting/prospects/ghost/promote?tenant_id={_CLIENT_ID}",
        headers=auth_headers_for(_CLIENT_ID),
    )
    assert resp.status_code == 404


def test_promote_prospect_endpoint_failure_returns_503(
    prospecting_client, fake_db, monkeypatch, auth_headers_for
):
    fake_db.seed("tenants", [{"id": _CLIENT_ID, "plan": "agent_os"}])
    _wire_fake_db(monkeypatch, fake_db)

    async def boom(*a, **k):
        raise RuntimeError("promote boom")

    monkeypatch.setattr(prospecting_router, "promote_to_lead", boom)

    resp = prospecting_client.post(
        f"/api/v1/prospecting/prospects/p1/promote?tenant_id={_CLIENT_ID}",
        headers=auth_headers_for(_CLIENT_ID),
    )
    assert resp.status_code == 503


def test_reject_prospect_success_omitted_tenant_id(
    prospecting_client, fake_db, monkeypatch, auth_headers_for
):
    fake_db.seed("tenants", [{"id": _CLIENT_ID, "plan": "agent_os"}])
    fake_db.seed("prospects", [{"id": "p45", "client_id": _CLIENT_ID, "status": "new"}])
    _wire_fake_db(monkeypatch, fake_db)

    resp = prospecting_client.post(
        "/api/v1/prospecting/prospects/p45/reject",
        headers=auth_headers_for(_CLIENT_ID),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


def test_reject_prospect_failure_returns_503(
    prospecting_client, fake_db, monkeypatch, auth_headers_for
):
    fake_db.seed("tenants", [{"id": _CLIENT_ID, "plan": "agent_os"}])
    _wire_fake_db(monkeypatch, fake_db)

    def boom(*a, **k):
        raise RuntimeError("reject boom")

    monkeypatch.setattr(prospecting_router, "tenant_update", boom)

    resp = prospecting_client.post(
        f"/api/v1/prospecting/prospects/p1/reject?tenant_id={_CLIENT_ID}",
        headers=auth_headers_for(_CLIENT_ID),
    )
    assert resp.status_code == 503


def test_status_endpoint_reports_configured_flag(
    prospecting_client, fake_db, monkeypatch, auth_headers_for
):
    fake_db.seed("tenants", [{"id": _CLIENT_ID, "plan": "agent_os"}])
    _wire_fake_db(monkeypatch, fake_db)
    monkeypatch.setattr(prospecting.settings, "google_places_api_key", "test-key")

    resp = prospecting_client.get(
        "/api/v1/prospecting/status", headers=auth_headers_for(_CLIENT_ID)
    )
    assert resp.status_code == 200
    assert resp.json() == {"configured": True}


def test_reject_prospect_not_found_returns_404(
    prospecting_client, fake_db, monkeypatch, auth_headers_for
):
    fake_db.seed("tenants", [{"id": _CLIENT_ID, "plan": "agent_os"}])
    _wire_fake_db(monkeypatch, fake_db)

    resp = prospecting_client.post(
        f"/api/v1/prospecting/prospects/ghost/reject?tenant_id={_CLIENT_ID}",
        headers=auth_headers_for(_CLIENT_ID),
    )
    assert resp.status_code == 404


def test_prospecting_router_registered_in_main_app():
    """The build lane kept this router unregistered; the integration pass
    (same PR) registered it in main.py alongside migration 191 being applied.
    Contract flipped from not-registered to registered at integration time —
    see plans/nexlify-capabilities-roadmap_plan.md Phase 5."""
    from backend.main import app as main_app

    paths = {route.path for route in main_app.routes}
    assert "/api/v1/prospecting/status" in paths
