"""Agent OS P0 test suite.

Covers the chat-first orchestrator foundation: usage metering, semantic
memory, the routing orchestrator + stub worker, and all six os_* routers.

Service functions take ``db`` as their first argument, so service tests pass
an in-memory FakeSupabase directly. Routers call ``get_service_supabase()``
internally, so router tests patch that per module and authenticate with a
real HS256 JWT (secret seeded by conftest via the JWT_SECRET_KEY env var).
"""

import os

os.environ["TESTING"] = "1"

import uuid
from contextlib import ExitStack, contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services import orchestrator, os_memory, os_workers, usage_meter
from backend.services.tenant_scope import (
    TenantScopeError,
    tenant_scope_column,
    tenant_table,
)

client = TestClient(app)

_JWT_SECRET = "test-secret-key-for-jwt"
_TENANT = "tenant-001"
_ROUTER_MODS = (
    "os_threads",
    "os_agent_runs",
    "os_deliverables",
    "os_memory",
    "os_backlog",
    "os_usage",
)


# ---------------------------------------------------------------------------
# In-memory Supabase fake
# ---------------------------------------------------------------------------


class FakeResponse:
    def __init__(self, data=None, count=None):
        self.data = data or []
        self.count = count


class FakeQuery:
    """Chainable query that runs against a shared in-memory store."""

    def __init__(self, sb, table):
        self.sb = sb
        self.table = table
        self._op = "select"
        self._payload = None
        self._filters = []
        self._order = []
        self._limit = None

    def select(self, columns="*", **kwargs):
        self._op = "select"
        return self

    def insert(self, data):
        self._op = "insert"
        self._payload = data
        return self

    def update(self, data):
        self._op = "update"
        self._payload = data
        return self

    def delete(self):
        self._op = "delete"
        return self

    def eq(self, col, val):
        self._filters.append(("eq", col, val))
        return self

    def neq(self, col, val):
        self._filters.append(("neq", col, val))
        return self

    def gte(self, col, val):
        self._filters.append(("gte", col, val))
        return self

    def lte(self, col, val):
        self._filters.append(("lte", col, val))
        return self

    def order(self, col, desc=False):
        self._order.append((col, desc))
        return self

    def limit(self, n):
        self._limit = n
        return self

    def range(self, *args):
        return self

    def _match(self, row):
        for op, col, val in self._filters:
            cur = row.get(col)
            if op == "eq" and cur != val:
                return False
            if op == "neq" and cur == val:
                return False
            if op == "gte" and not (cur is not None and cur >= val):
                return False
            if op == "lte" and not (cur is not None and cur <= val):
                return False
        return True

    def execute(self):
        if (self.table, self._op) in self.sb.raise_on:
            raise RuntimeError(f"forced failure on {self.table}.{self._op}")
        rows = self.sb.store.setdefault(self.table, [])

        if self._op == "insert":
            items = (
                self._payload if isinstance(self._payload, list) else [self._payload]
            )
            now = datetime.now(timezone.utc).isoformat()
            inserted = []
            for item in items:
                rec = dict(item)
                rec.setdefault("id", str(uuid.uuid4()))
                rec.setdefault("created_at", now)
                rec.setdefault("updated_at", now)
                rows.append(rec)
                inserted.append(dict(rec))
            return FakeResponse(inserted)

        matched = [r for r in rows if self._match(r)]
        for col, desc in reversed(self._order):
            matched.sort(key=lambda r: (r.get(col) is None, r.get(col)), reverse=desc)

        if self._op == "select":
            result = matched[: self._limit] if self._limit is not None else matched
            return FakeResponse([dict(r) for r in result], count=len(matched))
        if self._op == "update":
            for r in matched:
                r.update(self._payload)
            return FakeResponse([dict(r) for r in matched])
        if self._op == "delete":
            deleted = [dict(r) for r in matched]
            self.sb.store[self.table] = [r for r in rows if not self._match(r)]
            return FakeResponse(deleted)
        return FakeResponse([])


class FakeRpc:
    def __init__(self, sb, name):
        self.sb = sb
        self.name = name

    def execute(self):
        if self.name in self.sb.rpc_raises:
            raise RuntimeError(f"forced rpc failure: {self.name}")
        return FakeResponse(self.sb.rpc_results.get(self.name, []))


class FakeSupabase:
    """Minimal in-memory stand-in for the Supabase client."""

    def __init__(self):
        self.store = {}
        self.rpc_results = {}
        self.rpc_raises = set()
        self.raise_on = set()

    def table(self, name):
        return FakeQuery(self, name)

    def rpc(self, name, params=None):
        return FakeRpc(self, name)

    def seed(self, table, *rows):
        bucket = self.store.setdefault(table, [])
        for row in rows:
            bucket.append(dict(row))
        return self


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _token(tenant_id=_TENANT, role="owner"):
    from jose import jwt

    payload = {
        "tenant_id": tenant_id,
        "sub": tenant_id,
        "email": "owner@example.com",
        "role": role,
        "plan": "professional",
        "business_name": "Test Biz",
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm="HS256")


def _auth(tenant_id=_TENANT, role="owner"):
    return {"Authorization": f"Bearer {_token(tenant_id, role)}"}


@contextmanager
def patched_db(fake):
    """Patch get_service_supabase in every os_* router module."""
    with ExitStack() as stack:
        for mod in _ROUTER_MODS:
            stack.enter_context(
                patch(
                    f"backend.routers.{mod}.get_service_supabase",
                    return_value=fake,
                )
            )
        yield fake


@contextmanager
def patched_orchestrator(llm_json=None, raise_llm=False):
    """Stub the orchestrator's LLM + memory dependencies."""
    call = AsyncMock()
    if raise_llm:
        call.side_effect = RuntimeError("llm unavailable")
    else:
        call.return_value = SimpleNamespace(text=llm_json or "")
    with patch("backend.services.orchestrator.call_claude_messages", call), patch(
        "backend.services.orchestrator.search_memory", AsyncMock(return_value=[])
    ), patch(
        "backend.services.os_memory.embed_text", AsyncMock(return_value=[0.0] * 512)
    ):
        yield


def _seed_thread(fake, thread_id="thread-001", tenant=_TENANT):
    fake.seed(
        "os_threads",
        {
            "id": thread_id,
            "client_id": tenant,
            "title": "Existing thread",
            "updated_at": "2026-05-01T00:00:00+00:00",
        },
    )
    return thread_id


def _seed_run(fake, run_id="run-001", tenant=_TENANT, **extra):
    row = {
        "id": run_id,
        "client_id": tenant,
        "thread_id": "thread-001",
        "agent_name": "generalist",
        "status": "queued",
        "thought_process": [],
    }
    row.update(extra)
    fake.seed("os_agent_runs", row)
    return run_id


# ===========================================================================
# usage_meter service
# ===========================================================================


class TestUsageMeter:
    def test_current_cycle_start_is_first_of_month(self):
        cycle = usage_meter.current_cycle_start()
        assert cycle.endswith("-01")
        datetime.fromisoformat(cycle)

    def test_get_usage_creates_row_when_missing(self):
        fake = FakeSupabase()
        snap = usage_meter.get_usage(fake, _TENANT)
        assert snap.agent_runs == 0
        assert snap.messages == 0
        assert snap.cap == usage_meter.DEFAULT_AGENT_RUN_CAP
        assert snap.cap_reached is False
        assert len(fake.store["os_tenant_usage"]) == 1

    def test_get_usage_reads_existing_row(self):
        fake = FakeSupabase()
        fake.seed(
            "os_tenant_usage",
            {
                "client_id": _TENANT,
                "cycle_start": usage_meter.current_cycle_start(),
                "agent_runs": 7,
                "messages": 20,
                "input_tokens": 100,
                "output_tokens": 200,
            },
        )
        snap = usage_meter.get_usage(fake, _TENANT)
        assert snap.agent_runs == 7
        assert snap.messages == 20
        assert snap.input_tokens == 100
        assert snap.output_tokens == 200

    def test_cap_reached_true_at_cap(self):
        fake = FakeSupabase()
        fake.seed(
            "os_tenant_usage",
            {
                "client_id": _TENANT,
                "cycle_start": usage_meter.current_cycle_start(),
                "agent_runs": usage_meter.DEFAULT_AGENT_RUN_CAP,
            },
        )
        assert usage_meter.cap_reached(fake, _TENANT) is True

    def test_record_message_increments(self):
        fake = FakeSupabase()
        usage_meter.record_message(fake, _TENANT)
        usage_meter.record_message(fake, _TENANT)
        assert usage_meter.get_usage(fake, _TENANT).messages == 2

    def test_record_agent_run_increments_runs_and_tokens(self):
        fake = FakeSupabase()
        usage_meter.record_agent_run(fake, _TENANT, input_tokens=10, output_tokens=5)
        snap = usage_meter.get_usage(fake, _TENANT)
        assert snap.agent_runs == 1
        assert snap.input_tokens == 10
        assert snap.output_tokens == 5

    def test_usage_snapshot_cap_reached_property(self):
        snap = usage_meter.UsageSnapshot(
            cycle_start="2026-05-01",
            agent_runs=100,
            messages=0,
            input_tokens=0,
            output_tokens=0,
            cap=100,
        )
        assert snap.cap_reached is True


# ===========================================================================
# os_memory service
# ===========================================================================


class TestOsMemoryService:
    async def test_write_memory_embeds_and_stores(self):
        fake = FakeSupabase()
        with patch(
            "backend.services.os_memory.embed_text",
            AsyncMock(return_value=[0.1] * 512),
        ):
            row = await os_memory.write_memory(
                fake, _TENANT, "Owner prefers morning calls", kind="preference"
            )
        assert row["content"] == "Owner prefers morning calls"
        assert row["kind"] == "preference"
        assert row["client_id"] == _TENANT
        assert fake.store["os_memory_entries"][0]["embedding"] == [0.1] * 512

    async def test_write_memory_coerces_invalid_kind_to_fact(self):
        fake = FakeSupabase()
        with patch(
            "backend.services.os_memory.embed_text", AsyncMock(return_value=[0.0])
        ):
            row = await os_memory.write_memory(fake, _TENANT, "x", kind="bogus")
        assert row["kind"] == "fact"

    async def test_write_memory_stores_without_vector_on_embed_failure(self):
        fake = FakeSupabase()
        with patch(
            "backend.services.os_memory.embed_text",
            AsyncMock(side_effect=RuntimeError("voyage down")),
        ):
            row = await os_memory.write_memory(fake, _TENANT, "still saved")
        assert row["content"] == "still saved"
        assert row["embedding"] is None

    async def test_search_memory_returns_rpc_hits(self):
        fake = FakeSupabase()
        fake.rpc_results["match_os_memory"] = [{"content": "hit", "kind": "fact"}]
        with patch(
            "backend.services.os_memory.embed_query",
            AsyncMock(return_value=[0.2] * 512),
        ):
            hits = await os_memory.search_memory(fake, _TENANT, "query")
        assert hits == [{"content": "hit", "kind": "fact"}]

    async def test_search_memory_returns_empty_on_embed_failure(self):
        fake = FakeSupabase()
        with patch(
            "backend.services.os_memory.embed_query",
            AsyncMock(side_effect=RuntimeError("voyage down")),
        ):
            assert await os_memory.search_memory(fake, _TENANT, "query") == []

    async def test_search_memory_returns_empty_on_rpc_failure(self):
        fake = FakeSupabase()
        fake.rpc_raises.add("match_os_memory")
        with patch(
            "backend.services.os_memory.embed_query",
            AsyncMock(return_value=[0.0] * 512),
        ):
            assert await os_memory.search_memory(fake, _TENANT, "query") == []

    def test_list_memory_orders_pinned_first(self):
        fake = FakeSupabase()
        fake.seed(
            "os_memory_entries",
            {
                "id": "m1",
                "client_id": _TENANT,
                "content": "a",
                "is_pinned": False,
                "created_at": "2026-05-01",
            },
            {
                "id": "m2",
                "client_id": _TENANT,
                "content": "b",
                "is_pinned": True,
                "created_at": "2026-04-01",
            },
        )
        rows = os_memory.list_memory(fake, _TENANT)
        assert [r["id"] for r in rows] == ["m2", "m1"]

    async def test_update_memory_patches_content_and_reembeds(self):
        fake = FakeSupabase()
        fake.seed(
            "os_memory_entries",
            {"id": "m1", "client_id": _TENANT, "content": "old", "kind": "fact"},
        )
        with patch(
            "backend.services.os_memory.embed_text",
            AsyncMock(return_value=[0.9] * 512),
        ):
            updated = await os_memory.update_memory(
                fake, _TENANT, "m1", content="new", kind="decision", is_pinned=True
            )
        assert updated["content"] == "new"
        assert updated["kind"] == "decision"
        assert updated["is_pinned"] is True

    async def test_update_memory_returns_none_with_no_patch(self):
        fake = FakeSupabase()
        assert await os_memory.update_memory(fake, _TENANT, "m1") is None

    async def test_update_memory_returns_none_when_row_missing(self):
        fake = FakeSupabase()
        result = await os_memory.update_memory(fake, _TENANT, "missing", is_pinned=True)
        assert result is None

    def test_delete_memory_returns_true_when_removed(self):
        fake = FakeSupabase()
        fake.seed(
            "os_memory_entries",
            {"id": "m1", "client_id": _TENANT, "content": "a"},
        )
        assert os_memory.delete_memory(fake, _TENANT, "m1") is True
        assert fake.store["os_memory_entries"] == []

    def test_delete_memory_returns_false_when_missing(self):
        fake = FakeSupabase()
        assert os_memory.delete_memory(fake, _TENANT, "missing") is False


# ===========================================================================
# orchestrator service
# ===========================================================================


class TestOrchestratorParsing:
    def test_available_agents_includes_generalist(self):
        assert "generalist" in orchestrator.available_agents()

    def test_parse_decision_plain_json(self):
        parsed = orchestrator._parse_decision('{"action": "answer"}')
        assert parsed == {"action": "answer"}

    def test_parse_decision_strips_code_fence(self):
        parsed = orchestrator._parse_decision('```json\n{"action": "answer"}\n```')
        assert parsed == {"action": "answer"}

    def test_parse_decision_returns_none_without_braces(self):
        assert orchestrator._parse_decision("not json at all") is None

    def test_parse_decision_returns_none_on_invalid_json(self):
        assert orchestrator._parse_decision("{bad json}") is None

    def test_fallback_decision_delegates_to_generalist(self):
        decision = orchestrator._fallback_decision("do a thing")
        assert decision.action == "delegate"
        assert decision.agent_name == "generalist"
        assert decision.thought_process


class TestOrchestrate:
    async def test_orchestrate_answer(self):
        fake = FakeSupabase()
        with patched_orchestrator('{"action": "answer", "reply": "Hello"}'):
            decision = await orchestrator.orchestrate(fake, _TENANT, "hi")
        assert decision.action == "answer"
        assert decision.reply == "Hello"
        assert decision.agent_name is None

    async def test_orchestrate_delegate(self):
        fake = FakeSupabase()
        llm = (
            '{"action": "delegate", "reply": "On it", '
            '"agent_name": "generalist", "deliverable_title": "Report"}'
        )
        with patched_orchestrator(llm):
            decision = await orchestrator.orchestrate(fake, _TENANT, "write a report")
        assert decision.action == "delegate"
        assert decision.agent_name == "generalist"
        assert decision.deliverable_title == "Report"
        assert decision.thought_process

    async def test_orchestrate_unknown_agent_becomes_backlog(self):
        fake = FakeSupabase()
        llm = (
            '{"action": "delegate", "reply": "Hmm", '
            '"agent_name": "tax_specialist", "reason": "needs a specialist"}'
        )
        with patched_orchestrator(llm):
            decision = await orchestrator.orchestrate(fake, _TENANT, "do my taxes")
        assert decision.action == "backlog"
        assert decision.agent_name is None

    async def test_orchestrate_backlog(self):
        fake = FakeSupabase()
        llm = '{"action": "backlog", "reply": "No fit", "reason": "nothing fits"}'
        with patched_orchestrator(llm):
            decision = await orchestrator.orchestrate(fake, _TENANT, "weird ask")
        assert decision.action == "backlog"
        assert decision.reason == "nothing fits"

    async def test_orchestrate_captures_memory_writes(self):
        fake = FakeSupabase()
        llm = (
            '{"action": "answer", "reply": "Noted", '
            '"memory": [{"kind": "fact", "content": "Open on Sundays"}]}'
        )
        with patched_orchestrator(llm):
            decision = await orchestrator.orchestrate(fake, _TENANT, "we open Sundays")
        assert decision.memory_writes == [
            {"kind": "fact", "content": "Open on Sundays"}
        ]

    async def test_orchestrate_falls_back_on_llm_error(self):
        fake = FakeSupabase()
        with patched_orchestrator(raise_llm=True):
            decision = await orchestrator.orchestrate(fake, _TENANT, "anything")
        assert decision.action == "delegate"
        assert decision.agent_name == "generalist"

    async def test_orchestrate_falls_back_on_unparseable_output(self):
        fake = FakeSupabase()
        with patched_orchestrator("this is not json"):
            decision = await orchestrator.orchestrate(fake, _TENANT, "anything")
        assert decision.action == "delegate"

    async def test_orchestrate_falls_back_on_invalid_action(self):
        fake = FakeSupabase()
        with patched_orchestrator('{"action": "explode", "reply": "x"}'):
            decision = await orchestrator.orchestrate(fake, _TENANT, "anything")
        assert decision.action == "delegate"

    async def test_orchestrate_passes_history(self):
        fake = FakeSupabase()
        history = [
            {"role": "user", "content": "earlier"},
            {"role": "assistant", "content": "reply"},
        ]
        with patched_orchestrator('{"action": "answer", "reply": "ok"}'):
            decision = await orchestrator.orchestrate(
                fake, _TENANT, "now", history=history
            )
        assert decision.action == "answer"


class TestRunWorker:
    async def test_run_worker_completes_and_meters(self):
        fake = FakeSupabase()
        _seed_run(fake, "run-001")
        with patch(
            "backend.services.os_workers.get_service_supabase", return_value=fake
        ):
            await os_workers.run_worker(
                "run-001", _TENANT, "thread-001", "generalist", "do it", "My Draft"
            )
        run = fake.store["os_agent_runs"][0]
        assert run["status"] == "succeeded"
        assert run["deliverable_status"] == "pending_approval"
        assert run["deliverable"]["title"] == "My Draft"
        assert any(m["role"] == "agent" for m in fake.store["os_messages"])
        assert usage_meter.get_usage(fake, _TENANT).agent_runs == 1

    async def test_run_worker_records_failure(self):
        fake = FakeSupabase()
        _seed_run(fake, "run-001")
        fake.raise_on.add(("os_agent_runs", "select"))
        with patch(
            "backend.services.os_workers.get_service_supabase", return_value=fake
        ):
            await os_workers.run_worker(
                "run-001", _TENANT, "thread-001", "generalist", "do it", "Draft"
            )
        assert fake.store["os_agent_runs"][0]["status"] == "failed"

    async def test_record_memory_writes_persists_entries(self):
        fake = FakeSupabase()
        with patch(
            "backend.services.os_memory.embed_text", AsyncMock(return_value=[0.0])
        ):
            await orchestrator.record_memory_writes(
                fake,
                _TENANT,
                [{"kind": "fact", "content": "fact one"}],
                source="thread:t1",
            )
        assert fake.store["os_memory_entries"][0]["content"] == "fact one"


# ===========================================================================
# tenant_scope (os_* additions)
# ===========================================================================


class TestTenantScope:
    @pytest.mark.parametrize(
        "table",
        [
            "os_threads",
            "os_messages",
            "os_agent_runs",
            "os_memory_entries",
            "os_backlog_requests",
            "os_tenant_usage",
        ],
    )
    def test_os_tables_scope_on_client_id(self, table):
        assert tenant_scope_column(table) == "client_id"

    def test_tenant_table_insert_injects_scope(self):
        fake = FakeSupabase()
        tenant_table(fake, "os_threads", _TENANT).insert({"title": "T"}).execute()
        assert fake.store["os_threads"][0]["client_id"] == _TENANT

    def test_tenant_insert_rejects_cross_tenant_row(self):
        fake = FakeSupabase()
        with pytest.raises(TenantScopeError):
            tenant_table(fake, "os_threads", _TENANT).insert(
                {"title": "T", "client_id": "other-tenant"}
            ).execute()


# ===========================================================================
# os_usage router
# ===========================================================================


class TestUsageRouter:
    def test_get_usage_returns_snapshot(self):
        fake = FakeSupabase()
        with patched_db(fake):
            resp = client.get("/api/v1/os/usage", headers=_auth())
        assert resp.status_code == 200
        body = resp.json()
        assert body["agent_runs"] == 0
        assert body["cap"] == usage_meter.DEFAULT_AGENT_RUN_CAP
        assert body["cap_reached"] is False

    def test_get_usage_requires_auth(self):
        resp = client.get("/api/v1/os/usage")
        assert resp.status_code == 422


# ===========================================================================
# os_threads router
# ===========================================================================


class TestThreadsRouter:
    def test_create_thread(self):
        fake = FakeSupabase()
        with patched_db(fake):
            resp = client.post(
                "/api/v1/os/threads", json={"title": "Plan launch"}, headers=_auth()
            )
        assert resp.status_code == 201
        assert resp.json()["title"] == "Plan launch"

    def test_create_thread_blank_title_defaults(self):
        fake = FakeSupabase()
        with patched_db(fake):
            resp = client.post(
                "/api/v1/os/threads", json={"title": "   "}, headers=_auth()
            )
        assert resp.status_code == 201
        assert resp.json()["title"] == "New conversation"

    def test_list_threads(self):
        fake = FakeSupabase()
        _seed_thread(fake)
        with patched_db(fake):
            resp = client.get("/api/v1/os/threads", headers=_auth())
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_messages(self):
        fake = FakeSupabase()
        _seed_thread(fake)
        fake.seed(
            "os_messages",
            {
                "id": "msg-1",
                "client_id": _TENANT,
                "thread_id": "thread-001",
                "role": "user",
                "content": "hi",
                "created_at": "2026-05-01",
            },
        )
        with patched_db(fake):
            resp = client.get("/api/v1/os/threads/thread-001/messages", headers=_auth())
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["messages"]) == 1
        assert body["agent_runs"] == []

    def test_list_messages_unknown_thread_404(self):
        fake = FakeSupabase()
        with patched_db(fake):
            resp = client.get("/api/v1/os/threads/missing/messages", headers=_auth())
        assert resp.status_code == 404

    def test_post_message_answer(self):
        fake = FakeSupabase()
        _seed_thread(fake)
        with patched_db(fake), patched_orchestrator(
            '{"action": "answer", "reply": "Hello there"}'
        ):
            resp = client.post(
                "/api/v1/os/threads/thread-001/messages",
                json={"content": "hi"},
                headers=_auth(),
            )
        assert resp.status_code == 201
        body = resp.json()
        assert body["action"] == "answer"
        assert body["assistant_message"]["content"] == "Hello there"
        assert body["agent_runs"] == []

    def test_post_message_delegate_creates_run(self):
        fake = FakeSupabase()
        _seed_thread(fake)
        llm = (
            '{"action": "delegate", "reply": "On it", '
            '"agent_name": "generalist", "deliverable_title": "Draft"}'
        )
        with patched_db(fake), patched_orchestrator(llm):
            resp = client.post(
                "/api/v1/os/threads/thread-001/messages",
                json={"content": "write a plan"},
                headers=_auth(),
            )
        assert resp.status_code == 201
        body = resp.json()
        assert body["action"] == "delegate"
        assert len(body["agent_runs"]) == 1
        assert body["agent_runs"][0]["status"] == "queued"

    def test_post_message_backlog_without_owner_email(self):
        fake = FakeSupabase()
        _seed_thread(fake)
        llm = '{"action": "backlog", "reply": "No fit", "reason": "no agent"}'
        with patched_db(fake), patched_orchestrator(llm):
            resp = client.post(
                "/api/v1/os/threads/thread-001/messages",
                json={"content": "weird request"},
                headers=_auth(),
            )
        assert resp.status_code == 201
        assert resp.json()["action"] == "backlog"
        assert len(fake.store["os_backlog_requests"]) == 1

    def test_post_message_backlog_emails_owner(self):
        fake = FakeSupabase()
        _seed_thread(fake)
        fake.seed(
            "tenants",
            {
                "id": _TENANT,
                "owner_email": "owner@example.com",
                "business_name": "Test Biz",
            },
        )
        llm = '{"action": "backlog", "reply": "No fit", "reason": "no agent"}'
        sender = AsyncMock()
        with patched_db(fake), patched_orchestrator(llm), patch(
            "backend.routers.os_threads.send_email", sender
        ):
            resp = client.post(
                "/api/v1/os/threads/thread-001/messages",
                json={"content": "weird request"},
                headers=_auth(),
            )
        assert resp.status_code == 201
        sender.assert_awaited_once()

    def test_post_message_persists_memory_writes(self):
        fake = FakeSupabase()
        _seed_thread(fake)
        llm = (
            '{"action": "answer", "reply": "Noted", '
            '"memory": [{"kind": "fact", "content": "Closed Mondays"}]}'
        )
        with patched_db(fake), patched_orchestrator(llm):
            resp = client.post(
                "/api/v1/os/threads/thread-001/messages",
                json={"content": "we close Mondays"},
                headers=_auth(),
            )
        assert resp.status_code == 201
        assert fake.store["os_memory_entries"][0]["content"] == "Closed Mondays"

    def test_post_message_cap_reached_429(self):
        fake = FakeSupabase()
        _seed_thread(fake)
        fake.seed(
            "os_tenant_usage",
            {
                "client_id": _TENANT,
                "cycle_start": usage_meter.current_cycle_start(),
                "agent_runs": usage_meter.DEFAULT_AGENT_RUN_CAP,
            },
        )
        with patched_db(fake), patched_orchestrator(
            '{"action": "answer", "reply": "x"}'
        ):
            resp = client.post(
                "/api/v1/os/threads/thread-001/messages",
                json={"content": "hi"},
                headers=_auth(),
            )
        assert resp.status_code == 429

    def test_post_message_unknown_thread_404(self):
        fake = FakeSupabase()
        with patched_db(fake), patched_orchestrator(
            '{"action": "answer", "reply": "x"}'
        ):
            resp = client.post(
                "/api/v1/os/threads/missing/messages",
                json={"content": "hi"},
                headers=_auth(),
            )
        assert resp.status_code == 404

    def test_post_message_rejects_empty_content(self):
        fake = FakeSupabase()
        _seed_thread(fake)
        with patched_db(fake):
            resp = client.post(
                "/api/v1/os/threads/thread-001/messages",
                json={"content": ""},
                headers=_auth(),
            )
        assert resp.status_code == 422


# ===========================================================================
# os_agent_runs router
# ===========================================================================


class TestAgentRunsRouter:
    def test_get_agent_run(self):
        fake = FakeSupabase()
        _seed_run(fake, "run-001", status="running")
        with patched_db(fake):
            resp = client.get("/api/v1/os/agent-runs/run-001", headers=_auth())
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    def test_get_agent_run_missing_404(self):
        fake = FakeSupabase()
        with patched_db(fake):
            resp = client.get("/api/v1/os/agent-runs/missing", headers=_auth())
        assert resp.status_code == 404

    def test_report_bug_sets_timestamp(self):
        fake = FakeSupabase()
        _seed_run(fake, "run-001")
        with patched_db(fake):
            resp = client.post(
                "/api/v1/os/agent-runs/run-001/report-bug", headers=_auth()
            )
        assert resp.status_code == 200
        assert resp.json()["bug_reported_at"] is not None

    def test_report_bug_missing_404(self):
        fake = FakeSupabase()
        with patched_db(fake):
            resp = client.post(
                "/api/v1/os/agent-runs/missing/report-bug", headers=_auth()
            )
        assert resp.status_code == 404


# ===========================================================================
# os_deliverables router
# ===========================================================================


def _seed_deliverable_run(fake, run_id="run-001", status="pending_approval"):
    _seed_run(
        fake,
        run_id,
        status="succeeded",
        deliverable={"title": "Draft", "format": "markdown", "body": "old body"},
        deliverable_status=status,
    )
    return run_id


class TestDeliverablesRouter:
    def test_edit_deliverable(self):
        fake = FakeSupabase()
        _seed_deliverable_run(fake)
        with patched_db(fake):
            resp = client.patch(
                "/api/v1/os/deliverables/run-001",
                json={"title": "New Title", "body": "new body"},
                headers=_auth(),
            )
        assert resp.status_code == 200
        deliverable = resp.json()["deliverable"]
        assert deliverable["title"] == "New Title"
        assert deliverable["body"] == "new body"

    def test_edit_deliverable_missing_run_404(self):
        fake = FakeSupabase()
        with patched_db(fake):
            resp = client.patch(
                "/api/v1/os/deliverables/missing",
                json={"title": "x"},
                headers=_auth(),
            )
        assert resp.status_code == 404

    def test_edit_deliverable_no_deliverable_404(self):
        fake = FakeSupabase()
        _seed_run(fake, "run-001")
        with patched_db(fake):
            resp = client.patch(
                "/api/v1/os/deliverables/run-001",
                json={"title": "x"},
                headers=_auth(),
            )
        assert resp.status_code == 404

    def test_edit_deliverable_already_approved_409(self):
        fake = FakeSupabase()
        _seed_deliverable_run(fake, status="approved")
        with patched_db(fake):
            resp = client.patch(
                "/api/v1/os/deliverables/run-001",
                json={"title": "x"},
                headers=_auth(),
            )
        assert resp.status_code == 409

    def test_approve_deliverable(self):
        fake = FakeSupabase()
        _seed_deliverable_run(fake)
        with patched_db(fake):
            resp = client.post(
                "/api/v1/os/deliverables/run-001/approve", headers=_auth()
            )
        assert resp.status_code == 200
        assert resp.json()["deliverable_status"] == "approved"

    def test_reject_deliverable(self):
        fake = FakeSupabase()
        _seed_deliverable_run(fake)
        with patched_db(fake):
            resp = client.post(
                "/api/v1/os/deliverables/run-001/reject", headers=_auth()
            )
        assert resp.status_code == 200
        assert resp.json()["deliverable_status"] == "rejected"

    def test_approve_already_decided_409(self):
        fake = FakeSupabase()
        _seed_deliverable_run(fake, status="rejected")
        with patched_db(fake):
            resp = client.post(
                "/api/v1/os/deliverables/run-001/approve", headers=_auth()
            )
        assert resp.status_code == 409


# ===========================================================================
# os_memory router
# ===========================================================================


class TestMemoryRouter:
    def test_list_memory(self):
        fake = FakeSupabase()
        fake.seed(
            "os_memory_entries",
            {
                "id": "m1",
                "client_id": _TENANT,
                "content": "a",
                "kind": "fact",
                "is_pinned": False,
                "created_at": "2026-05-01",
            },
        )
        with patched_db(fake):
            resp = client.get("/api/v1/os/memory", headers=_auth())
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_create_memory(self):
        fake = FakeSupabase()
        with patched_db(fake), patch(
            "backend.services.os_memory.embed_text",
            AsyncMock(return_value=[0.0] * 512),
        ):
            resp = client.post(
                "/api/v1/os/memory",
                json={"content": "We bill net-30", "kind": "fact"},
                headers=_auth(),
            )
        assert resp.status_code == 201
        assert resp.json()["content"] == "We bill net-30"

    def test_create_memory_invalid_kind_422(self):
        fake = FakeSupabase()
        with patched_db(fake):
            resp = client.post(
                "/api/v1/os/memory",
                json={"content": "x", "kind": "nonsense"},
                headers=_auth(),
            )
        assert resp.status_code == 422

    def test_remember_endpoint(self):
        fake = FakeSupabase()
        with patched_db(fake), patch(
            "backend.services.os_memory.embed_text",
            AsyncMock(return_value=[0.0] * 512),
        ):
            resp = client.post(
                "/api/v1/os/memory/remember",
                json={"content": "Owner's name is Sam"},
                headers=_auth(),
            )
        assert resp.status_code == 201
        assert resp.json()["kind"] == "fact"

    def test_update_memory(self):
        fake = FakeSupabase()
        fake.seed(
            "os_memory_entries",
            {"id": "m1", "client_id": _TENANT, "content": "old", "kind": "fact"},
        )
        with patched_db(fake), patch(
            "backend.services.os_memory.embed_text",
            AsyncMock(return_value=[0.0] * 512),
        ):
            resp = client.patch(
                "/api/v1/os/memory/m1",
                json={"content": "updated", "is_pinned": True},
                headers=_auth(),
            )
        assert resp.status_code == 200
        assert resp.json()["content"] == "updated"

    def test_update_memory_invalid_kind_422(self):
        fake = FakeSupabase()
        with patched_db(fake):
            resp = client.patch(
                "/api/v1/os/memory/m1",
                json={"kind": "nonsense"},
                headers=_auth(),
            )
        assert resp.status_code == 422

    def test_update_memory_missing_404(self):
        fake = FakeSupabase()
        with patched_db(fake):
            resp = client.patch(
                "/api/v1/os/memory/missing",
                json={"is_pinned": True},
                headers=_auth(),
            )
        assert resp.status_code == 404

    def test_update_memory_requires_owner(self):
        fake = FakeSupabase()
        with patched_db(fake):
            resp = client.patch(
                "/api/v1/os/memory/m1",
                json={"is_pinned": True},
                headers=_auth(role="staff"),
            )
        assert resp.status_code == 403

    def test_delete_memory(self):
        fake = FakeSupabase()
        fake.seed(
            "os_memory_entries",
            {"id": "m1", "client_id": _TENANT, "content": "a"},
        )
        with patched_db(fake):
            resp = client.delete("/api/v1/os/memory/m1", headers=_auth())
        assert resp.status_code == 204

    def test_delete_memory_missing_404(self):
        fake = FakeSupabase()
        with patched_db(fake):
            resp = client.delete("/api/v1/os/memory/missing", headers=_auth())
        assert resp.status_code == 404

    def test_delete_memory_requires_owner(self):
        fake = FakeSupabase()
        with patched_db(fake):
            resp = client.delete("/api/v1/os/memory/m1", headers=_auth(role="staff"))
        assert resp.status_code == 403


# ===========================================================================
# os_backlog router
# ===========================================================================


class TestBacklogRouter:
    def test_list_backlog(self):
        fake = FakeSupabase()
        fake.seed(
            "os_backlog_requests",
            {
                "id": "b1",
                "client_id": _TENANT,
                "summary": "thing",
                "status": "pending",
                "created_at": "2026-05-01",
            },
        )
        with patched_db(fake):
            resp = client.get("/api/v1/os/backlog", headers=_auth())
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_decide_backlog_accepts(self):
        fake = FakeSupabase()
        fake.seed(
            "os_backlog_requests",
            {"id": "b1", "client_id": _TENANT, "summary": "thing", "status": "pending"},
        )
        with patched_db(fake):
            resp = client.post(
                "/api/v1/os/backlog/b1/decision",
                json={"decision": "accepted", "note": "build it"},
                headers=_auth(),
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "accepted"
        assert body["decision_note"] == "build it"

    def test_decide_backlog_invalid_decision_422(self):
        fake = FakeSupabase()
        fake.seed(
            "os_backlog_requests",
            {"id": "b1", "client_id": _TENANT, "status": "pending"},
        )
        with patched_db(fake):
            resp = client.post(
                "/api/v1/os/backlog/b1/decision",
                json={"decision": "maybe"},
                headers=_auth(),
            )
        assert resp.status_code == 422

    def test_decide_backlog_missing_404(self):
        fake = FakeSupabase()
        with patched_db(fake):
            resp = client.post(
                "/api/v1/os/backlog/missing/decision",
                json={"decision": "declined"},
                headers=_auth(),
            )
        assert resp.status_code == 404

    def test_decide_backlog_requires_owner(self):
        fake = FakeSupabase()
        with patched_db(fake):
            resp = client.post(
                "/api/v1/os/backlog/b1/decision",
                json={"decision": "accepted"},
                headers=_auth(role="staff"),
            )
        assert resp.status_code == 403
