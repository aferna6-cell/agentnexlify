"""Tenants can hide spam conversations from the shared inbox, with undo.

Spam is the reserved ``spam`` entry in ``conversations.tags`` (prod's
status CHECK forbids a new status). These tests drive the real routes over
a stateful fake Supabase, so tenant scoping and list filtering are checked
against stored rows rather than mocks returning canned data.
"""

import copy
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

import backend.models.database as db_module
from backend.config import settings

TENANT_A = "00000000-0000-0000-0000-0000000000aa"
TENANT_B = "00000000-0000-0000-0000-0000000000bb"
CONV_A1 = "11111111-1111-1111-1111-111111111111"  # real customer
CONV_A2 = "22222222-2222-2222-2222-222222222222"  # spam
CONV_B1 = "33333333-3333-3333-3333-333333333333"  # other tenant


class _Result:
    def __init__(self, data):
        self.data = data
        self.count = len(data)


class _Query:
    def __init__(self, store, table, op, payload=None):
        self.store, self.table, self.op, self.payload = store, table, op, payload
        self.filters = []
        self._limit = None
        self._order = None

    def eq(self, col, val):
        self.filters.append(lambda r, c=col, v=val: r.get(c) == v)
        return self

    def gte(self, col, val):
        self.filters.append(lambda r, c=col, v=val: (r.get(c) or "") >= v)
        return self

    def in_(self, col, vals):
        vals = set(vals)
        self.filters.append(lambda r, c=col: r.get(c) in vals)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def order(self, col, desc=False):
        self._order = (col, desc)
        return self

    def execute(self):
        rows = self.store.setdefault(self.table, [])
        match = [r for r in rows if all(f(r) for f in self.filters)]
        if self.op == "insert":
            new = self.payload if isinstance(self.payload, list) else [self.payload]
            new = [dict(copy.deepcopy(r), id=r.get("id") or f"new-{len(rows)}") for r in new]
            rows.extend(new)
            return _Result(copy.deepcopy(new))
        if self.op == "update":
            for r in match:
                r.update(copy.deepcopy(self.payload))
            return _Result(copy.deepcopy(match))
        if self.op == "delete":
            for r in match:
                rows.remove(r)
            return _Result(copy.deepcopy(match))
        if self._order:
            col, desc = self._order
            match.sort(key=lambda r: r.get(col) or "", reverse=desc)
        if self._limit is not None:
            match = match[: self._limit]
        return _Result(copy.deepcopy(match))


class _Table:
    def __init__(self, store, name):
        self.store, self.name = store, name

    def select(self, *_a, **_k):
        return _Query(self.store, self.name, "select")

    def insert(self, rows):
        return _Query(self.store, self.name, "insert", rows)

    def update(self, vals):
        return _Query(self.store, self.name, "update", vals)

    def delete(self):
        return _Query(self.store, self.name, "delete")


class FakeDB:
    def __init__(self, store):
        self.store = store

    def table(self, name):
        return _Table(self.store, name)


def _msg(tenant, session, content, minutes_ago, role="user"):
    ts = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()
    return {"tenant_id": tenant, "session_id": session, "role": role, "content": content, "created_at": ts}


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from backend.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db():
    fake = FakeDB(
        {
            "conversations": [
                {"id": CONV_A1, "client_id": TENANT_A, "session_id": "web_real", "tags": ["handoff"], "status": "active"},
                {"id": CONV_A2, "client_id": TENANT_A, "session_id": "web_spam", "tags": [], "status": "active"},
                {"id": CONV_B1, "client_id": TENANT_B, "session_id": "web_b", "tags": [], "status": "active"},
            ],
            "chat_messages": [
                _msg(TENANT_A, "web_real", "My text alerts stopped", 30),
                _msg(TENANT_A, "web_spam", "Buy cheap followers", 20),
                _msg(TENANT_A, "web_orphan", "SEO services!!!", 10),  # no conversations row
                _msg(TENANT_B, "web_b", "Hello from B", 5),
            ],
            "leads": [],
            "activity_log": [],
        }
    )
    prev = db_module._service_client
    db_module._service_client = fake
    try:
        yield fake
    finally:
        db_module._service_client = prev


def _headers(tenant_id, role=None):
    payload = {
        "tenant_id": tenant_id,
        "email": "owner@test.com",
        "plan": "growth",
        "business_name": "Test Business",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    if role:
        payload["role"] = role
    return {"Authorization": f"Bearer {jwt.encode(payload, settings.api_secret_key, algorithm='HS256')}"}


def _row(db, conv_id):
    return next(r for r in db.store["conversations"] if r["id"] == conv_id)


def _sessions(client, tenant, view=None, role=None):
    url = f"/api/v1/auth/conversations/{tenant}" + (f"?view={view}" if view else "")
    res = client.get(url, headers=_headers(tenant, role))
    assert res.status_code == 200, res.text
    body = res.json()
    return [c["session_id"] for c in body["conversations"]], body


def test_mark_spam_hides_from_inbox_and_restore_brings_it_back(client, db):
    res = client.put(
        f"/api/v1/inbox/{TENANT_A}/conversations/web_spam/spam",
        json={"spam": True},
        headers=_headers(TENANT_A),
    )
    assert res.status_code == 200, res.text
    assert res.json()["spam"] is True
    assert "spam" in _row(db, CONV_A2)["tags"]
    assert _row(db, CONV_A2)["status"] == "active"  # status untouched (CHECK constraint)

    inbox, body = _sessions(client, TENANT_A)
    assert "web_spam" not in inbox and "web_real" in inbox
    assert body["spam_count"] == 1
    spam, _ = _sessions(client, TENANT_A, view="spam")
    assert spam == ["web_spam"]

    res = client.put(
        f"/api/v1/inbox/{TENANT_A}/conversations/{CONV_A2}/spam",
        json={"spam": False},
        headers=_headers(TENANT_A),
    )
    assert res.status_code == 200, res.text
    assert _row(db, CONV_A2)["tags"] == []
    inbox, body = _sessions(client, TENANT_A)
    assert "web_spam" in inbox and body["spam_count"] == 0
    assert _sessions(client, TENANT_A, view="spam")[0] == []


def test_marking_spam_keeps_other_tags(client, db):
    client.put(
        f"/api/v1/inbox/{TENANT_A}/conversations/web_real/spam",
        json={"spam": True},
        headers=_headers(TENANT_A),
    )
    assert _row(db, CONV_A1)["tags"] == ["handoff", "spam"]
    client.put(
        f"/api/v1/inbox/{TENANT_A}/conversations/web_real/spam",
        json={"spam": False},
        headers=_headers(TENANT_A),
    )
    assert _row(db, CONV_A1)["tags"] == ["handoff"]


def test_bulk_marks_own_ids_and_reports_foreign_ids_untouched(client, db):
    before_b = copy.deepcopy(_row(db, CONV_B1))
    res = client.post(
        f"/api/v1/inbox/{TENANT_A}/conversations/spam",
        json={"conversation_ids": ["web_spam", "web_orphan", "web_b", CONV_B1], "spam": True},
        headers=_headers(TENANT_A),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert sorted(body["updated"]) == ["web_orphan", "web_spam"]
    assert sorted(body["not_found"]) == sorted(["web_b", CONV_B1])
    assert _row(db, CONV_B1) == before_b

    # A chat with no conversations row gets one, owned by tenant A, to hold the mark.
    orphan = [r for r in db.store["conversations"] if r["session_id"] == "web_orphan"]
    assert len(orphan) == 1 and orphan[0]["client_id"] == TENANT_A and orphan[0]["tags"] == ["spam"]

    assert _sessions(client, TENANT_A)[0] == ["web_real"]
    assert sorted(_sessions(client, TENANT_A, view="spam")[0]) == ["web_orphan", "web_spam"]
    assert any(a["activity_type"] == "conversation_spam" for a in db.store["activity_log"])


def test_cross_tenant_single_mark_is_404_and_changes_nothing(client, db):
    before = copy.deepcopy(db.store["conversations"])
    for conv in ("web_b", CONV_B1):
        res = client.put(
            f"/api/v1/inbox/{TENANT_A}/conversations/{conv}/spam",
            json={"spam": True},
            headers=_headers(TENANT_A),
        )
        assert res.status_code == 404
    assert db.store["conversations"] == before


def test_other_tenants_token_is_rejected(client, db):
    before = copy.deepcopy(db.store["conversations"])
    res = client.put(
        f"/api/v1/inbox/{TENANT_B}/conversations/web_b/spam",
        json={"spam": True},
        headers=_headers(TENANT_A),
    )
    assert res.status_code == 403
    assert db.store["conversations"] == before


def test_spam_does_not_leak_across_tenants(client, db):
    client.put(
        f"/api/v1/inbox/{TENANT_A}/conversations/web_spam/spam",
        json={"spam": True},
        headers=_headers(TENANT_A),
    )
    inbox_b, body_b = _sessions(client, TENANT_B)
    assert inbox_b == ["web_b"] and body_b["spam_count"] == 0
    assert _sessions(client, TENANT_B, view="spam")[0] == []


def test_members_cannot_manage_or_view_spam(client, db):
    client.put(
        f"/api/v1/inbox/{TENANT_A}/conversations/web_spam/spam",
        json={"spam": True},
        headers=_headers(TENANT_A),
    )
    member = _headers(TENANT_A, role="member")
    res = client.put(
        f"/api/v1/inbox/{TENANT_A}/conversations/web_spam/spam", json={"spam": False}, headers=member
    )
    assert res.status_code == 403
    res = client.get(f"/api/v1/auth/conversations/{TENANT_A}?view=spam", headers=member)
    assert res.status_code == 403
    res = client.get(f"/api/v1/auth/conversations/{TENANT_A}/web_spam", headers=member)
    assert res.status_code == 404
    inbox, _ = _sessions(client, TENANT_A, role="member")
    assert "web_spam" not in inbox
    # Owners can still open it from the Spam view.
    res = client.get(f"/api/v1/auth/conversations/{TENANT_A}/web_spam", headers=_headers(TENANT_A))
    assert res.status_code == 200 and res.json()["messages"]


def test_invalid_view_is_rejected(client, db):
    res = client.get(f"/api/v1/auth/conversations/{TENANT_A}?view=deleted", headers=_headers(TENANT_A))
    assert res.status_code == 422


def test_notification_badge_skips_spam(client, db):
    route = f"/api/v1/notifications/{TENANT_A}"
    before = client.get(route, headers=_headers(TENANT_A))
    assert before.status_code == 200, before.text
    count_before = before.json()["new_conversations_count"]
    client.put(
        f"/api/v1/inbox/{TENANT_A}/conversations/web_spam/spam",
        json={"spam": True},
        headers=_headers(TENANT_A),
    )
    after = client.get(route, headers=_headers(TENANT_A)).json()
    assert after["new_conversations_count"] == count_before - 1


def test_tag_editor_cannot_add_or_drop_the_spam_marker(client, db):
    res = client.put(
        f"/api/v1/auth/conversations/{TENANT_A}/web_real/tags",
        json={"tags": ["handoff", "spam", "VIP"]},
        headers=_headers(TENANT_A),
    )
    assert res.status_code == 200, res.text
    assert _row(db, CONV_A1)["tags"] == ["handoff", "VIP"]

    client.put(
        f"/api/v1/inbox/{TENANT_A}/conversations/web_spam/spam",
        json={"spam": True},
        headers=_headers(TENANT_A),
    )
    client.put(
        f"/api/v1/auth/conversations/{TENANT_A}/web_spam/tags",
        json={"tags": ["Follow-up Needed"]},
        headers=_headers(TENANT_A),
    )
    assert _row(db, CONV_A2)["tags"] == ["Follow-up Needed", "spam"]
