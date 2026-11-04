"""GET /api/v1/widget/unsubscribe must treat a bad lid as a client error."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.limiter import limiter
from backend.routers import widget_config


def _client() -> TestClient:
    app = FastAPI()
    app.state.limiter = limiter
    app.include_router(widget_config.router)
    return TestClient(app)


def test_non_uuid_lid_returns_400_without_querying(monkeypatch):
    def forbidden():
        raise AssertionError("invalid lid must not hit the database")

    monkeypatch.setattr(widget_config, "get_service_supabase", forbidden)
    response = _client().get(
        "/api/v1/widget/unsubscribe",
        params={"lid": "not-a-uuid", "sig": "abc"},
    )
    assert response.status_code == 400
    assert "Invalid unsubscribe link" in response.text


def test_postgrest_uuid_error_returns_400(monkeypatch):
    class _Boom:
        def table(self, _name):
            return self

        def select(self, *_a, **_k):
            return self

        def eq(self, *_a, **_k):
            return self

        def limit(self, *_a, **_k):
            return self

        def execute(self):
            raise RuntimeError(
                "{'code': '22P02', 'message': 'invalid input syntax for type uuid'}"
            )

    monkeypatch.setattr(widget_config, "get_service_supabase", lambda: _Boom())
    response = _client().get(
        "/api/v1/widget/unsubscribe",
        params={
            "lid": "00000000-0000-0000-0000-000000000001",
            "sig": "abc",
        },
    )
    assert response.status_code == 400
    assert "Invalid unsubscribe link" in response.text
