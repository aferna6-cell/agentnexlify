"""FastAPI surface — exercised with Starlette's TestClient.

Skipped entirely when FastAPI/httpx aren't installed so the core suite still
runs in a bare environment. The app module deliberately omits
``from __future__ import annotations`` (PEP 563 would break Pydantic body
resolution); this suite is the guard that the endpoints actually resolve.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from agent_os.api.app import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health(client: TestClient):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["agent_count"] == 18
    assert body["bucket_count"] == 8
    assert "provider" in body


def test_list_agents_grouped_by_bucket(client: TestClient):
    r = client.get("/api/agents")
    assert r.status_code == 200
    groups = r.json()
    assert len(groups) == 8
    total = sum(len(g["agents"]) for g in groups)
    assert total == 18
    sample = groups[0]["agents"][0]
    assert {"agent_id", "display_name", "channel", "is_customer_facing"} <= sample.keys()


def test_buckets_listing(client: TestClient):
    r = client.get("/api/buckets")
    assert r.status_code == 200
    assert r.json()["listing"]


def test_samples(client: TestClient):
    r = client.get("/api/samples")
    assert r.status_code == 200
    samples = r.json()
    assert len(samples) == 8
    assert all("text" in s for s in samples)


def test_route_specialty_quote(client: TestClient):
    r = client.post(
        "/api/route",
        json={
            "text": "Follow up with Mike on the $1,100 brake job quote I sent.",
            "params": {"customer_name": "Mike", "quote_amount": 1100},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["decision"]["agent_id"] == "quote_follow_up"
    assert body["decision"]["used_specialty_rule"] is True
    assert body["result"] is not None
    assert body["result"]["body"].strip()
    # Trace shape round-trips through the API.
    assert body["result"]["trace"][0]["name"] == "Business profile"


def test_route_complaint_flagged(client: TestClient):
    r = client.post(
        "/api/route",
        json={
            "text": "A customer is furious our tech scratched their bumper.",
            "params": {"customer_name": "Greg"},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["decision"]["agent_id"] == "complaint_handler"
    assert body["decision"]["short_circuited"] is True


def test_route_bucket_query_has_no_result(client: TestClient):
    r = client.post("/api/route", json={"text": "What marketing agents do you have?"})
    assert r.status_code == 200
    body = r.json()
    assert body["decision"]["is_bucket_query"] is True
    assert body["result"] is None


def test_route_bad_channel_422(client: TestClient):
    r = client.post(
        "/api/route", json={"text": "Text Mike", "channel": "carrier-pigeon"}
    )
    assert r.status_code == 422


def test_route_empty_text_422(client: TestClient):
    r = client.post("/api/route", json={"text": ""})
    assert r.status_code == 422


def test_explicit_channel_override(client: TestClient):
    r = client.post(
        "/api/route",
        json={
            "text": "Ask Carlos for a Google review.",
            "channel": "sms",
            "params": {"customer_name": "Carlos"},
        },
    )
    assert r.status_code == 200
    assert r.json()["result"]["channel"] == "sms"


def test_wishlist_grows_after_out_of_scope(client: TestClient):
    client.post(
        "/api/route",
        json={"text": "Help me decide whether to hire a second technician."},
    )
    r = client.get("/api/wishlist")
    assert r.status_code == 200
    items = r.json()
    assert any("technician" in i["ask_text"].lower() for i in items)


def test_log_accumulates(client: TestClient):
    client.post("/api/route", json={"text": "What can you do?"})
    r = client.get("/api/log")
    assert r.status_code == 200
    assert len(r.json()) >= 1
