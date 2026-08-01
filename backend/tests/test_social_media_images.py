"""Tests for backend/services/social_media_images.py and the
POST /api/v1/social/{tenant_id}/generate-image router endpoint.

Covers: platform image size presets, generation + storage upload, clean
error surfacing (never a 500) for unconfigured/provider/storage failures,
and the media_urls append when post_id is given. All OpenAI HTTP is mocked
via patching generate_image_png (image_gen.py's own provider HTTP is
already covered by its module).
"""

from unittest.mock import AsyncMock, MagicMock, patch

from backend.dependencies import _get_current_tenant
from backend.main import app
from backend.services import image_gen
from backend.services import social_media_images as images
from backend.services.image_gen import ImageGenError, ImageGenNotConfigured
from backend.services.plan_gate import require_marketing_access
from backend.tests.conftest import SyncASGITestClient
from backend.tests.fake_supabase import db as fake_db
from backend.tests.fake_supabase import run

_TENANT = "11111111-1111-1111-1111-111111111111"
CLAIMS = {"tenant_id": _TENANT}


def _fake_storage_db():
    db = MagicMock()
    bucket = MagicMock()
    db.storage.from_.return_value = bucket
    return db, bucket


# ---------------------------------------------------------------------------
# Platform size presets
# ---------------------------------------------------------------------------


def test_platform_image_sizes_instagram_is_square():
    preset = images.PLATFORM_IMAGE_SIZES["instagram"]
    assert preset["width"] == preset["height"]


def test_platform_image_sizes_instagram_portrait_is_taller_than_wide():
    preset = images.PLATFORM_IMAGE_SIZES["instagram_portrait"]
    assert preset["height"] > preset["width"]


def test_platform_image_sizes_facebook_is_landscape():
    preset = images.PLATFORM_IMAGE_SIZES["facebook"]
    assert preset["width"] > preset["height"]


def test_unknown_platform_falls_back_to_default_size():
    assert "not_a_real_platform" not in images.PLATFORM_IMAGE_SIZES


# ---------------------------------------------------------------------------
# image_gen.generate_image_png — provider dispatch (size parameter branch)
# ---------------------------------------------------------------------------


def test_generate_image_png_openai_provider_passes_size_through():
    """generate_image_png's openai-provider dispatch branch -- covers the
    size kwarg being forwarded to _generate_openai untouched."""
    with patch.object(image_gen.settings, "image_gen_provider", "openai"), patch.object(
        image_gen.settings, "image_gen_api_key", "sk-test"
    ), patch.object(
        image_gen, "_generate_openai", return_value=b"PNGDATA"
    ) as gen_openai:
        result = image_gen.generate_image_png("a cat", size="1024x1536")

    assert result == b"PNGDATA"
    gen_openai.assert_called_once_with("a cat", "sk-test", size="1024x1536")


# ---------------------------------------------------------------------------
# generate_post_image — service layer
# ---------------------------------------------------------------------------


def test_generate_post_image_uploads_and_returns_dimensions():
    db, bucket = _fake_storage_db()
    with patch.object(images, "generate_image_png", return_value=b"PNGDATA") as gen:
        result = run(
            images.generate_post_image(
                db, tenant_id=_TENANT, prompt="a cat drinking coffee", platform="instagram"
            )
        )

    gen.assert_called_once()
    assert gen.call_args.kwargs["size"] == images.PLATFORM_IMAGE_SIZES["instagram"]["size"]

    bucket.upload.assert_called_once()
    upload_call = bucket.upload.call_args
    assert upload_call.args[0].startswith(f"{_TENANT}/")
    assert upload_call.args[1] == b"PNGDATA"
    assert upload_call.kwargs["file_options"]["content-type"] == "image/png"

    assert result["width"] == images.PLATFORM_IMAGE_SIZES["instagram"]["width"]
    assert result["height"] == images.PLATFORM_IMAGE_SIZES["instagram"]["height"]
    assert result["url"].endswith(".png")
    assert _TENANT in result["url"]


def test_generate_post_image_uses_default_size_for_unknown_platform():
    db, bucket = _fake_storage_db()
    with patch.object(images, "generate_image_png", return_value=b"PNGDATA") as gen:
        result = run(
            images.generate_post_image(
                db, tenant_id=_TENANT, prompt="x", platform="twitter"
            )
        )
    assert gen.call_args.kwargs["size"] == images._DEFAULT_SIZE["size"]
    assert result["width"] == images._DEFAULT_SIZE["width"]
    assert result["height"] == images._DEFAULT_SIZE["height"]


def test_generate_post_image_unconfigured_raises_clean_error():
    db, _bucket = _fake_storage_db()
    with patch.object(
        images, "generate_image_png", side_effect=ImageGenNotConfigured("nope")
    ):
        try:
            run(
                images.generate_post_image(
                    db, tenant_id=_TENANT, prompt="x", platform="facebook"
                )
            )
            assert False, "expected SocialImageGenError"
        except images.SocialImageGenError:
            pass


def test_generate_post_image_provider_error_raises_clean_error():
    db, _bucket = _fake_storage_db()
    with patch.object(images, "generate_image_png", side_effect=ImageGenError("boom")):
        try:
            run(
                images.generate_post_image(
                    db, tenant_id=_TENANT, prompt="x", platform="google_business"
                )
            )
            assert False, "expected SocialImageGenError"
        except images.SocialImageGenError:
            pass


def test_generate_post_image_storage_failure_raises_clean_error():
    db, bucket = _fake_storage_db()
    bucket.upload.side_effect = RuntimeError("storage down")
    with patch.object(images, "generate_image_png", return_value=b"PNGDATA"):
        try:
            run(
                images.generate_post_image(
                    db, tenant_id=_TENANT, prompt="x", platform="instagram"
                )
            )
            assert False, "expected SocialImageGenError"
        except images.SocialImageGenError:
            pass


# ---------------------------------------------------------------------------
# Router endpoint
# ---------------------------------------------------------------------------


def _client():
    app.dependency_overrides[_get_current_tenant] = lambda: CLAIMS
    app.dependency_overrides[require_marketing_access] = lambda: CLAIMS
    return SyncASGITestClient(app)


def _teardown():
    app.dependency_overrides.pop(_get_current_tenant, None)
    app.dependency_overrides.pop(require_marketing_access, None)


class TestGenerateImageEndpoint:
    def teardown_method(self):
        _teardown()

    def test_generate_image_returns_url_and_dimensions(self):
        client = _client()
        fake_result = {"url": "https://x.test/social.png", "width": 1024, "height": 1024}
        with patch(
            "backend.routers.social_media.generate_post_image",
            AsyncMock(return_value=fake_result),
        ):
            resp = client.post(
                f"/api/v1/social/{_TENANT}/generate-image",
                json={"prompt": "a coffee cup", "platform": "instagram"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["url"] == fake_result["url"]
        assert body["width"] == 1024
        assert body["height"] == 1024

    def test_generate_image_appends_to_post_media_urls(self):
        client = _client()
        sink = []
        db = fake_db(
            {"social_posts": [{"id": "post-1", "media_urls": ["https://existing.png"]}]},
            sink=sink,
        )
        fake_result = {"url": "https://x.test/social.png", "width": 1024, "height": 1024}
        with patch(
            "backend.routers.social_media.generate_post_image",
            AsyncMock(return_value=fake_result),
        ), patch(
            "backend.routers.social_media.get_service_supabase", return_value=db
        ):
            resp = client.post(
                f"/api/v1/social/{_TENANT}/generate-image",
                json={
                    "prompt": "a coffee cup",
                    "platform": "instagram",
                    "post_id": "post-1",
                },
            )
        assert resp.status_code == 200
        update_calls = [c for c in sink if c[0] == "social_posts" and c[1] == "update"]
        assert update_calls, "expected a media_urls update call"
        updated_media = update_calls[0][2][0]["media_urls"]
        assert fake_result["url"] in updated_media
        assert "https://existing.png" in updated_media

    def test_generate_image_unconfigured_returns_422(self):
        client = _client()
        with patch(
            "backend.routers.social_media.generate_post_image",
            AsyncMock(side_effect=images.SocialImageGenError("not configured")),
        ):
            resp = client.post(
                f"/api/v1/social/{_TENANT}/generate-image",
                json={"prompt": "a coffee cup", "platform": "instagram"},
            )
        assert resp.status_code == 422

    def test_generate_image_invalid_platform_returns_400(self):
        client = _client()
        resp = client.post(
            f"/api/v1/social/{_TENANT}/generate-image",
            json={"prompt": "a coffee cup", "platform": "not_a_real_platform"},
        )
        assert resp.status_code == 400

    def test_generate_image_unexpected_error_returns_500(self):
        """A non-SocialImageGenError exception must be caught and turned
        into a clean 500, not bubble up as an unhandled error."""
        client = _client()
        with patch(
            "backend.routers.social_media.generate_post_image",
            AsyncMock(side_effect=RuntimeError("storage exploded")),
        ):
            resp = client.post(
                f"/api/v1/social/{_TENANT}/generate-image",
                json={"prompt": "a coffee cup", "platform": "instagram"},
            )
        assert resp.status_code == 500

    def test_generate_image_post_id_not_found_still_returns_200(self):
        """The image is already generated + stored -- a post_id that
        doesn't match any row must log a warning and still return the
        generated image, never fail the whole request."""
        client = _client()
        sink = []
        db = fake_db({"social_posts": []}, sink=sink)
        fake_result = {"url": "https://x.test/social.png", "width": 1024, "height": 1024}
        with patch(
            "backend.routers.social_media.generate_post_image",
            AsyncMock(return_value=fake_result),
        ), patch(
            "backend.routers.social_media.get_service_supabase", return_value=db
        ):
            resp = client.post(
                f"/api/v1/social/{_TENANT}/generate-image",
                json={
                    "prompt": "a coffee cup",
                    "platform": "instagram",
                    "post_id": "post-does-not-exist",
                },
            )
        assert resp.status_code == 200
        assert resp.json()["url"] == fake_result["url"]
        update_calls = [c for c in sink if c[0] == "social_posts" and c[1] == "update"]
        assert not update_calls

    def test_generate_image_post_append_exception_still_returns_200(self):
        """A DB failure while appending the generated URL to the post's
        media_urls must be swallowed -- the image itself already succeeded
        and was returned to the caller."""
        client = _client()
        db = MagicMock()
        db.table.side_effect = RuntimeError("db down")
        fake_result = {"url": "https://x.test/social.png", "width": 1024, "height": 1024}
        with patch(
            "backend.routers.social_media.generate_post_image",
            AsyncMock(return_value=fake_result),
        ), patch(
            "backend.routers.social_media.get_service_supabase", return_value=db
        ):
            resp = client.post(
                f"/api/v1/social/{_TENANT}/generate-image",
                json={
                    "prompt": "a coffee cup",
                    "platform": "instagram",
                    "post_id": "post-1",
                },
            )
        assert resp.status_code == 200
        assert resp.json()["url"] == fake_result["url"]
