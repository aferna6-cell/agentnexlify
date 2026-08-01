"""Tests for backend/services/social_publisher.py and
backend/services/social_engagement.py.

Publisher: dispatches due scheduled posts to the platform's connected
integration, sets external_post_id + status='published' on success,
status='failed' with a reason on failure, and never silently publishes an
unsupported platform (twitter/linkedin) or a platform with no connected
integration. All platform calls are mocked directly (no real Graph/OpenAI
HTTP) — the HTTP-level Graph API contract for these functions is already
covered by backend/tests/test_os_actions.py.

Engagement: merges fetched metrics into engagement_data with a fetched_at
stamp, isolates per-post failures. All Graph HTTP is mocked via a stub
httpx.AsyncClient (same pattern test_os_actions.py already uses).
"""

from unittest.mock import AsyncMock, MagicMock, patch

from backend.services import social_engagement, social_publisher
from backend.tests.fake_supabase import Query, Result
from backend.tests.fake_supabase import db as fake_db
from backend.tests.fake_supabase import run

_TENANT = "22222222-2222-2222-2222-222222222222"


def _due_post(**overrides) -> dict:
    row = {
        "id": "post-1",
        "tenant_id": _TENANT,
        "platform": "instagram",
        "content": "Check out our new menu!",
        "media_urls": ["https://cdn.test/photo.png"],
    }
    row.update(overrides)
    return row


class _RaisingQuery:
    """Same chainable shape as fake_supabase.Query, but .execute() raises
    once the last verb call (select/insert/update/delete) matches one of
    raise_ops -- exercises the except-Exception branches around DB calls
    without a full fake-postgrest client."""

    def __init__(self, rows, sink, table, raise_ops):
        self._rows = rows
        self._sink = sink
        self._table = table
        self._raise_ops = raise_ops
        self._op = None

    def __getattr__(self, name):
        if name in ("select", "insert", "update", "delete"):
            def _verb(*args, **kwargs):
                self._op = name
                self._sink.append((self._table, name, args))
                return self

            return _verb
        if name == "execute":
            def _execute(*args, **kwargs):
                self._sink.append((self._table, "execute", args))
                if self._op in self._raise_ops:
                    raise RuntimeError(f"{self._table}.{self._op} boom")
                return Result(self._rows)

            return _execute

        def _chain(*args, **kwargs):
            self._sink.append((self._table, name, args))
            return self

        return _chain


def _raising_db(rows_by_table, sink, raise_table, raise_ops):
    """fake_db() lookalike where one table's chosen verb(s) raise on
    .execute() instead of returning rows -- every other table behaves like
    the normal fake_supabase.Query."""
    client = MagicMock()

    def _table(name):
        if name == raise_table:
            return _RaisingQuery(rows_by_table.get(name, []), sink, name, raise_ops)
        return Query(rows_by_table.get(name, []), sink, name)

    client.table.side_effect = _table
    client._sink = sink
    return client


# ---------------------------------------------------------------------------
# publish_due_posts / process_scheduled_posts
# ---------------------------------------------------------------------------


def test_publish_due_posts_returns_zero_when_none_due():
    sink = []
    db = fake_db({"social_posts": []}, sink=sink)
    with patch.object(social_publisher, "get_service_supabase", return_value=db):
        count = run(social_publisher.publish_due_posts())
    assert count == 0


def test_publish_due_posts_instagram_success_sets_external_id_and_published():
    sink = []
    db = fake_db({"social_posts": [_due_post(platform="instagram")]}, sink=sink)
    publish_mock = AsyncMock(return_value=("ig_media_123", {"id": "ig_media_123"}))
    with patch.object(social_publisher, "get_service_supabase", return_value=db), patch.object(
        social_publisher.social_instagram, "publish_image_post", publish_mock
    ):
        count = run(social_publisher.publish_due_posts())

    assert count == 1
    publish_mock.assert_awaited_once_with(
        _TENANT, "https://cdn.test/photo.png", "Check out our new menu!"
    )
    update_calls = [c for c in sink if c[0] == "social_posts" and c[1] == "update"]
    assert update_calls, "expected an update call"
    payload = update_calls[-1][2][0]
    assert payload["status"] == "published"
    assert payload["external_post_id"] == "ig_media_123"
    assert "published_at" in payload


def test_publish_due_posts_facebook_success_sets_external_id():
    sink = []
    db = fake_db({"social_posts": [_due_post(platform="facebook", media_urls=[])]}, sink=sink)
    publish_mock = AsyncMock(return_value=("1234_5678", {"id": "1234_5678"}))
    with patch.object(social_publisher, "get_service_supabase", return_value=db), patch.object(
        social_publisher.social_facebook, "publish_text_post", publish_mock
    ):
        count = run(social_publisher.publish_due_posts())

    assert count == 1
    publish_mock.assert_awaited_once_with(
        _TENANT, "Check out our new menu!", link=None
    )
    update_calls = [c for c in sink if c[0] == "social_posts" and c[1] == "update"]
    payload = update_calls[-1][2][0]
    assert payload["status"] == "published"
    assert payload["external_post_id"] == "1234_5678"


def test_publish_due_posts_gbp_success_sets_external_id():
    sink = []
    db = fake_db({"social_posts": [_due_post(platform="google_business", media_urls=[])]}, sink=sink)
    publish_mock = AsyncMock(return_value=("accounts/1/locations/2/localPosts/3", {}))
    with patch.object(social_publisher, "get_service_supabase", return_value=db), patch.object(
        social_publisher.gbp, "publish_post", publish_mock
    ):
        count = run(social_publisher.publish_due_posts())

    assert count == 1
    publish_mock.assert_awaited_once_with(_TENANT, "Check out our new menu!")
    update_calls = [c for c in sink if c[0] == "social_posts" and c[1] == "update"]
    payload = update_calls[-1][2][0]
    assert payload["status"] == "published"
    assert payload["external_post_id"] == "accounts/1/locations/2/localPosts/3"


def test_publish_due_posts_failure_marks_failed_not_published():
    sink = []
    db = fake_db({"social_posts": [_due_post(platform="instagram")]}, sink=sink)
    publish_mock = AsyncMock(
        return_value=(None, {"stage": "ig_api", "message": "graph 500"})
    )
    with patch.object(social_publisher, "get_service_supabase", return_value=db), patch.object(
        social_publisher.social_instagram, "publish_image_post", publish_mock
    ):
        count = run(social_publisher.publish_due_posts())

    assert count == 0
    update_calls = [c for c in sink if c[0] == "social_posts" and c[1] == "update"]
    payload = update_calls[-1][2][0]
    assert payload["status"] == "failed"
    assert "published_at" not in payload
    assert "external_post_id" not in payload
    assert payload["engagement_data"]["publish_error"]["reason"] == "publish_failed"


def test_publish_due_posts_not_connected_marks_failed_not_connected():
    sink = []
    db = fake_db({"social_posts": [_due_post(platform="facebook", media_urls=[])]}, sink=sink)
    publish_mock = AsyncMock(
        return_value=(
            None,
            {"stage": "connector", "message": "facebook page not connected for this tenant"},
        )
    )
    with patch.object(social_publisher, "get_service_supabase", return_value=db), patch.object(
        social_publisher.social_facebook, "publish_text_post", publish_mock
    ):
        count = run(social_publisher.publish_due_posts())

    assert count == 0
    update_calls = [c for c in sink if c[0] == "social_posts" and c[1] == "update"]
    payload = update_calls[-1][2][0]
    assert payload["status"] == "failed"
    assert payload["engagement_data"]["publish_error"]["reason"] == "not_connected"


def test_publish_due_posts_unsupported_platform_never_published():
    """twitter and linkedin have no publish integration — must fail cleanly,
    never silently flip to published (CLAUDE.md: X/Twitter is deferred)."""
    sink = []
    db = fake_db(
        {
            "social_posts": [
                _due_post(id="post-tw", platform="twitter"),
                _due_post(id="post-li", platform="linkedin"),
            ]
        },
        sink=sink,
    )
    with patch.object(social_publisher, "get_service_supabase", return_value=db):
        count = run(social_publisher.publish_due_posts())

    assert count == 0
    update_calls = [c for c in sink if c[0] == "social_posts" and c[1] == "update"]
    assert len(update_calls) == 2
    for call in update_calls:
        payload = call[2][0]
        assert payload["status"] == "failed"
        assert payload["engagement_data"]["publish_error"]["reason"] == "platform_not_supported"


def test_publish_due_posts_instagram_without_media_fails_cleanly():
    sink = []
    db = fake_db({"social_posts": [_due_post(platform="instagram", media_urls=[])]}, sink=sink)
    with patch.object(social_publisher, "get_service_supabase", return_value=db):
        count = run(social_publisher.publish_due_posts())

    assert count == 0
    update_calls = [c for c in sink if c[0] == "social_posts" and c[1] == "update"]
    payload = update_calls[-1][2][0]
    assert payload["status"] == "failed"
    assert payload["engagement_data"]["publish_error"]["reason"] == "missing_image"


def test_publish_due_posts_isolates_per_post_failures():
    """One post raising an exception must not stop the rest of the batch."""
    sink = []
    db = fake_db(
        {
            "social_posts": [
                _due_post(id="post-ok", platform="facebook", media_urls=[]),
                _due_post(id="post-boom", platform="instagram"),
            ]
        },
        sink=sink,
    )
    fb_mock = AsyncMock(return_value=("111", {"id": "111"}))
    ig_mock = AsyncMock(side_effect=RuntimeError("network exploded"))
    with patch.object(social_publisher, "get_service_supabase", return_value=db), patch.object(
        social_publisher.social_facebook, "publish_text_post", fb_mock
    ), patch.object(social_publisher.social_instagram, "publish_image_post", ig_mock):
        count = run(social_publisher.publish_due_posts())

    assert count == 1
    update_calls = [c for c in sink if c[0] == "social_posts" and c[1] == "update"]
    statuses = {call[2][0]["status"] for call in update_calls}
    assert statuses == {"published", "failed"}


def test_process_scheduled_posts_same_semantics_as_publish_due_posts():
    sink = []
    db = fake_db({"social_posts": [_due_post(platform="instagram")]}, sink=sink)
    publish_mock = AsyncMock(return_value=("ig_media_1", {}))
    with patch.object(social_publisher, "get_service_supabase", return_value=db), patch.object(
        social_publisher.social_instagram, "publish_image_post", publish_mock
    ):
        count = run(social_publisher.process_scheduled_posts())
    assert count == 1


def test_publish_due_posts_query_exception_returns_zero():
    sink = []
    db = _raising_db(
        {"social_posts": []}, sink, raise_table="social_posts", raise_ops={"select"}
    )
    with patch.object(social_publisher, "get_service_supabase", return_value=db):
        count = run(social_publisher.publish_due_posts())
    assert count == 0


def test_publish_due_posts_mark_failed_persist_exception_still_returns_zero():
    """_mark_failed's own DB update raising must not crash the batch -- the
    failure is logged and the batch result is still 0 published."""
    sink = []
    db = _raising_db(
        {"social_posts": [_due_post(id="post-tw", platform="twitter")]},
        sink,
        raise_table="social_posts",
        raise_ops={"update"},
    )
    with patch.object(social_publisher, "get_service_supabase", return_value=db):
        count = run(social_publisher.publish_due_posts())
    assert count == 0


def test_publish_due_posts_mark_published_persist_exception_returns_false():
    """A successful platform publish whose status='published' write then
    fails must not be counted as published."""
    sink = []
    db = _raising_db(
        {"social_posts": [_due_post(platform="facebook", media_urls=[])]},
        sink,
        raise_table="social_posts",
        raise_ops={"update"},
    )
    publish_mock = AsyncMock(return_value=("111", {"id": "111"}))
    with patch.object(social_publisher, "get_service_supabase", return_value=db), patch.object(
        social_publisher.social_facebook, "publish_text_post", publish_mock
    ):
        count = run(social_publisher.publish_due_posts())
    assert count == 0


def test_publish_due_posts_isolates_post_missing_id_key():
    """A malformed row missing 'id' raises KeyError inside _publish_one
    before its own try/except -- the batch-level loop must catch it and
    keep processing the rest."""
    sink = []
    bad_post = {
        "tenant_id": _TENANT,
        "platform": "instagram",
        "content": "x",
        "media_urls": [],
    }
    good_post = _due_post(id="post-ok", platform="facebook", media_urls=[])
    db = fake_db({"social_posts": [bad_post, good_post]}, sink=sink)
    fb_mock = AsyncMock(return_value=("111", {"id": "111"}))
    with patch.object(social_publisher, "get_service_supabase", return_value=db), patch.object(
        social_publisher.social_facebook, "publish_text_post", fb_mock
    ):
        count = run(social_publisher.publish_due_posts())
    assert count == 1


def test_dispatch_unsupported_platform_returns_platform_not_supported():
    """_dispatch's own fallback branch -- unreachable via publish_due_posts
    (unsupported platforms are filtered before _dispatch is called), so
    call it directly."""
    external_id, response = run(
        social_publisher._dispatch(_due_post(platform="pinterest", media_urls=[]))
    )
    assert external_id is None
    assert response["reason"] == "platform_not_supported"


# ---------------------------------------------------------------------------
# ingest_engagement
# ---------------------------------------------------------------------------


class _StubClient:
    """Mimics httpx.AsyncClient for a single canned GET response."""

    def __init__(self, response):
        self._response = response

    def __call__(self, *args, **kwargs):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, params=None):
        return self._response


class _FakeResponse:
    def __init__(self, status_code: int, json_body: dict):
        self.status_code = status_code
        self._json_body = json_body
        self.content = b"1" if json_body is not None else b""

    def json(self):
        return self._json_body


def test_ingest_engagement_merges_instagram_metrics():
    sink = []
    db = fake_db(
        {
            "social_posts": [
                {
                    "id": "post-1",
                    "tenant_id": _TENANT,
                    "platform": "instagram",
                    "external_post_id": "ig_media_123",
                    "engagement_data": {},
                }
            ]
        },
        sink=sink,
    )
    ig_account_loader = lambda client_id: {"access_token": "tok"}  # noqa: E731
    response = _FakeResponse(200, {"like_count": 42, "comments_count": 3})
    with patch.object(social_engagement, "get_service_supabase", return_value=db), patch.object(
        social_engagement, "_load_ig_account", ig_account_loader
    ), patch.object(social_engagement.httpx, "AsyncClient", _StubClient(response)):
        count = run(social_engagement.ingest_engagement())

    assert count == 1
    update_calls = [c for c in sink if c[0] == "social_posts" and c[1] == "update"]
    assert update_calls, "expected an engagement_data update"
    payload = update_calls[-1][2][0]["engagement_data"]
    assert payload["likes"] == 42
    assert payload["comments"] == 3
    assert "fetched_at" in payload


def test_ingest_engagement_merges_facebook_metrics_preserving_existing_keys():
    sink = []
    db = fake_db(
        {
            "social_posts": [
                {
                    "id": "post-2",
                    "tenant_id": _TENANT,
                    "platform": "facebook",
                    "external_post_id": "1234_5678",
                    "engagement_data": {"note": "kept"},
                }
            ]
        },
        sink=sink,
    )
    fb_page_loader = lambda client_id: {"page_id": "1234", "page_access_token": "tok"}  # noqa: E731
    response = _FakeResponse(
        200,
        {
            "likes": {"summary": {"total_count": 10}},
            "comments": {"summary": {"total_count": 2}},
            "shares": {"count": 1},
        },
    )
    with patch.object(social_engagement, "get_service_supabase", return_value=db), patch.object(
        social_engagement, "_load_fb_page", fb_page_loader
    ), patch.object(social_engagement.httpx, "AsyncClient", _StubClient(response)):
        count = run(social_engagement.ingest_engagement())

    assert count == 1
    update_calls = [c for c in sink if c[0] == "social_posts" and c[1] == "update"]
    payload = update_calls[-1][2][0]["engagement_data"]
    assert payload["likes"] == 10
    assert payload["comments"] == 2
    assert payload["shares"] == 1
    assert payload["note"] == "kept"
    assert "fetched_at" in payload


def test_ingest_engagement_skips_posts_without_external_id():
    sink = []
    db = fake_db(
        {
            "social_posts": [
                {
                    "id": "post-3",
                    "tenant_id": _TENANT,
                    "platform": "instagram",
                    "external_post_id": None,
                    "engagement_data": {},
                }
            ]
        },
        sink=sink,
    )
    with patch.object(social_engagement, "get_service_supabase", return_value=db):
        count = run(social_engagement.ingest_engagement())
    assert count == 0
    assert not [c for c in sink if c[0] == "social_posts" and c[1] == "update"]


def test_ingest_engagement_isolates_per_post_failure():
    sink = []
    db = fake_db(
        {
            "social_posts": [
                {
                    "id": "post-fail",
                    "tenant_id": _TENANT,
                    "platform": "instagram",
                    "external_post_id": "ig_media_bad",
                    "engagement_data": {},
                },
                {
                    "id": "post-ok",
                    "tenant_id": _TENANT,
                    "platform": "facebook",
                    "external_post_id": "1234_ok",
                    "engagement_data": {},
                },
            ]
        },
        sink=sink,
    )
    ig_account_loader = lambda client_id: {"access_token": "tok"}  # noqa: E731
    fb_page_loader = lambda client_id: {"page_id": "1234", "page_access_token": "tok"}  # noqa: E731

    async def _boom(*args, **kwargs):
        raise RuntimeError("graph exploded")

    fb_response = _FakeResponse(
        200,
        {
            "likes": {"summary": {"total_count": 5}},
            "comments": {"summary": {"total_count": 1}},
            "shares": {"count": 0},
        },
    )

    call_state = {"n": 0}

    class _MixedClient:
        def __call__(self, *args, **kwargs):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, params=None):
            call_state["n"] += 1
            if call_state["n"] == 1:
                raise RuntimeError("graph exploded")
            return fb_response

    with patch.object(social_engagement, "get_service_supabase", return_value=db), patch.object(
        social_engagement, "_load_ig_account", ig_account_loader
    ), patch.object(social_engagement, "_load_fb_page", fb_page_loader), patch.object(
        social_engagement.httpx, "AsyncClient", _MixedClient()
    ):
        count = run(social_engagement.ingest_engagement())

    assert count == 1
    update_calls = [c for c in sink if c[0] == "social_posts" and c[1] == "update"]
    assert len(update_calls) == 1
    assert update_calls[0][2][0]["engagement_data"]["likes"] == 5


# ---------------------------------------------------------------------------
# ingest_engagement -- remaining fetch/merge/error branches
# ---------------------------------------------------------------------------


def test_fetch_instagram_insights_account_not_connected_returns_none():
    with patch.object(social_engagement, "_load_ig_account", return_value=None):
        result = run(social_engagement._fetch_instagram_insights(_TENANT, "media-1"))
    assert result is None


def test_fetch_instagram_insights_4xx_returns_none():
    ig_account_loader = lambda client_id: {"access_token": "tok"}  # noqa: E731
    response = _FakeResponse(403, {"error": "forbidden"})
    with patch.object(social_engagement, "_load_ig_account", ig_account_loader), patch.object(
        social_engagement.httpx, "AsyncClient", _StubClient(response)
    ):
        result = run(social_engagement._fetch_instagram_insights(_TENANT, "media-1"))
    assert result is None


def test_fetch_facebook_insights_page_not_connected_returns_none():
    with patch.object(social_engagement, "_load_fb_page", return_value=None):
        result = run(social_engagement._fetch_facebook_insights(_TENANT, "post-1"))
    assert result is None


def test_fetch_facebook_insights_request_exception_returns_none():
    fb_page_loader = lambda client_id: {"page_id": "1234", "page_access_token": "tok"}  # noqa: E731

    class _BoomClient:
        def __call__(self, *a, **kw):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, params=None):
            raise RuntimeError("network exploded")

    with patch.object(social_engagement, "_load_fb_page", fb_page_loader), patch.object(
        social_engagement.httpx, "AsyncClient", _BoomClient()
    ):
        result = run(social_engagement._fetch_facebook_insights(_TENANT, "post-1"))
    assert result is None


def test_fetch_facebook_insights_4xx_returns_none():
    fb_page_loader = lambda client_id: {"page_id": "1234", "page_access_token": "tok"}  # noqa: E731
    response = _FakeResponse(500, {"error": "boom"})
    with patch.object(social_engagement, "_load_fb_page", fb_page_loader), patch.object(
        social_engagement.httpx, "AsyncClient", _StubClient(response)
    ):
        result = run(social_engagement._fetch_facebook_insights(_TENANT, "post-1"))
    assert result is None


def test_ingest_one_missing_external_id_returns_false_direct_call():
    """_ingest_one's own defensive check -- ingest_engagement filters these
    out before ever calling _ingest_one, so exercise it directly."""
    db = fake_db({})
    post = {
        "id": "post-x",
        "tenant_id": _TENANT,
        "platform": "instagram",
        "external_post_id": None,
    }
    result = run(social_engagement._ingest_one(db, post))
    assert result is False


def test_ingest_one_unsupported_platform_returns_false():
    db = fake_db({})
    post = {
        "id": "post-x",
        "tenant_id": _TENANT,
        "platform": "twitter",
        "external_post_id": "abc",
    }
    result = run(social_engagement._ingest_one(db, post))
    assert result is False


def test_ingest_engagement_fetch_unexpected_error_marks_post_not_updated():
    """An unexpected exception escaping the fetch call (not the internal
    per-request try/except) must be caught by _ingest_one's outer handler
    and counted as a non-update, not raised."""
    sink = []
    db = fake_db(
        {
            "social_posts": [
                {
                    "id": "post-1",
                    "tenant_id": _TENANT,
                    "platform": "instagram",
                    "external_post_id": "ig_media_123",
                    "engagement_data": {},
                }
            ]
        },
        sink=sink,
    )

    def _boom_loader(client_id):
        raise RuntimeError("account lookup exploded")

    with patch.object(social_engagement, "get_service_supabase", return_value=db), patch.object(
        social_engagement, "_load_ig_account", _boom_loader
    ):
        count = run(social_engagement.ingest_engagement())
    assert count == 0
    assert not [c for c in sink if c[0] == "social_posts" and c[1] == "update"]


def test_ingest_one_non_dict_engagement_data_replaced_with_empty():
    sink = []
    db = fake_db({}, sink=sink)
    ig_account_loader = lambda client_id: {"access_token": "tok"}  # noqa: E731
    response = _FakeResponse(200, {"like_count": 5, "comments_count": 1})
    post = {
        "id": "post-1",
        "tenant_id": _TENANT,
        "platform": "instagram",
        "external_post_id": "ig_media_1",
        "engagement_data": ["not", "a", "dict"],
    }
    with patch.object(social_engagement, "_load_ig_account", ig_account_loader), patch.object(
        social_engagement.httpx, "AsyncClient", _StubClient(response)
    ):
        result = run(social_engagement._ingest_one(db, post))
    assert result is True
    update_calls = [c for c in sink if c[0] == "social_posts" and c[1] == "update"]
    payload = update_calls[-1][2][0]["engagement_data"]
    assert payload["likes"] == 5


def test_ingest_one_persist_exception_returns_false():
    sink = []
    db = _raising_db({}, sink, raise_table="social_posts", raise_ops={"update"})
    ig_account_loader = lambda client_id: {"access_token": "tok"}  # noqa: E731
    response = _FakeResponse(200, {"like_count": 5, "comments_count": 1})
    post = {
        "id": "post-1",
        "tenant_id": _TENANT,
        "platform": "instagram",
        "external_post_id": "ig_media_1",
        "engagement_data": {},
    }
    with patch.object(social_engagement, "_load_ig_account", ig_account_loader), patch.object(
        social_engagement.httpx, "AsyncClient", _StubClient(response)
    ):
        result = run(social_engagement._ingest_one(db, post))
    assert result is False


def test_ingest_engagement_query_exception_returns_zero():
    sink = []
    db = _raising_db(
        {"social_posts": []}, sink, raise_table="social_posts", raise_ops={"select"}
    )
    with patch.object(social_engagement, "get_service_supabase", return_value=db):
        count = run(social_engagement.ingest_engagement())
    assert count == 0


def test_ingest_engagement_isolates_post_missing_tenant_id_key():
    """A malformed row missing 'tenant_id' raises KeyError inside
    _ingest_one before its own try/except -- ingest_engagement's batch loop
    must catch it and keep processing the rest."""
    sink = []
    bad_post = {"id": "post-bad", "platform": "instagram", "external_post_id": "ig_x"}
    good_post = {
        "id": "post-good",
        "tenant_id": _TENANT,
        "platform": "facebook",
        "external_post_id": "1234_ok",
        "engagement_data": {},
    }
    db = fake_db({"social_posts": [bad_post, good_post]}, sink=sink)
    fb_page_loader = lambda client_id: {"page_id": "1234", "page_access_token": "tok"}  # noqa: E731
    response = _FakeResponse(
        200,
        {
            "likes": {"summary": {"total_count": 1}},
            "comments": {"summary": {"total_count": 0}},
            "shares": {"count": 0},
        },
    )
    with patch.object(social_engagement, "get_service_supabase", return_value=db), patch.object(
        social_engagement, "_load_fb_page", fb_page_loader
    ), patch.object(social_engagement.httpx, "AsyncClient", _StubClient(response)):
        count = run(social_engagement.ingest_engagement())
    assert count == 1
