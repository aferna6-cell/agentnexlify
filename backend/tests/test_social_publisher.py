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

from unittest.mock import AsyncMock, patch

from backend.services import social_engagement, social_publisher
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
