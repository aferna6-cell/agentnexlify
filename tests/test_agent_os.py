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

    async def test_run_worker_auto_send_marks_approved(self):
        fake = FakeSupabase()
        _seed_run(fake, "run-001")
        fake.seed("tenants", {"id": _TENANT, "os_auto_send_enabled": True})
        with patch(
            "backend.services.os_workers.get_service_supabase", return_value=fake
        ):
            await os_workers.run_worker(
                "run-001", _TENANT, "thread-001", "generalist", "do it", "My Draft"
            )
        run = fake.store["os_agent_runs"][0]
        assert run["status"] == "succeeded"
        assert run["deliverable_status"] == "approved"

    async def test_run_worker_auto_send_default_off(self):
        fake = FakeSupabase()
        _seed_run(fake, "run-001")
        fake.seed("tenants", {"id": _TENANT, "os_auto_send_enabled": False})
        with patch(
            "backend.services.os_workers.get_service_supabase", return_value=fake
        ):
            await os_workers.run_worker(
                "run-001", _TENANT, "thread-001", "generalist", "do it", "My Draft"
            )
        run = fake.store["os_agent_runs"][0]
        assert run["deliverable_status"] == "pending_approval"

    async def test_run_worker_persists_action_type_from_worker_result(self):
        """Worker that returns ``action_type`` must persist it to ``os_agent_runs``.

        Without this, Group B action handlers stay dead — ``approve_deliverable``
        reads ``run.action_type`` to decide whether to fire a registered handler.
        """
        fake = FakeSupabase()
        _seed_run(fake, "run-001")
        fake_spec = os_workers.WorkerSpec(
            name="booking",
            description="test",
            run=AsyncMock(
                return_value=os_workers.WorkerResult(
                    deliverable={"title": "Booking Reply", "body": "x"},
                    summary="ready",
                    action_type="calendar.event.create",
                )
            ),
        )
        with patch(
            "backend.services.os_workers.get_service_supabase", return_value=fake
        ), patch("backend.services.os_workers.get_worker", return_value=fake_spec):
            await os_workers.run_worker(
                "run-001", _TENANT, "thread-001", "booking", "do it", "My Draft"
            )
        run = fake.store["os_agent_runs"][0]
        assert run["status"] == "succeeded"
        assert run["action_type"] == "calendar.event.create"

    async def test_run_worker_skips_action_type_when_worker_omits_it(self):
        """Workers that omit ``action_type`` must not write the column.

        Preserves existing behavior for catch-all workers (generalist) that have
        no registered action handler.
        """
        fake = FakeSupabase()
        _seed_run(fake, "run-001")
        with patch(
            "backend.services.os_workers.get_service_supabase", return_value=fake
        ):
            await os_workers.run_worker(
                "run-001", _TENANT, "thread-001", "generalist", "do it", "My Draft"
            )
        run = fake.store["os_agent_runs"][0]
        assert run.get("action_type") is None

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
# lead_nurture worker — runtime channel routing (1:N action mapping)
# ===========================================================================


class TestLeadNurtureChannelRouting:
    """Owner request picks the action_type at worker runtime.

    lead_nurture is a 1:N worker — three registered handlers consume its
    deliverable: ``email.send``, ``sms.send``, and ``crm.contact_upsert``.
    The worker chooses one per run; the default keeps the existing
    email-led follow-up behavior.
    """

    def test_defaults_to_email_when_no_channel_directive(self):
        from backend.services.os_workers.lead_nurture import _choose_action_type

        assert _choose_action_type("Follow up with Jane about her quote") == (
            "email.send"
        )
        assert _choose_action_type("") == "email.send"

    def test_explicit_sms_request_routes_to_sms_send(self):
        from backend.services.os_workers.lead_nurture import _choose_action_type

        assert _choose_action_type("Text this lead about pricing") == "sms.send"
        assert _choose_action_type("Send an SMS reminder") == "sms.send"
        assert _choose_action_type("Reach out via text") == "sms.send"

    def test_explicit_crm_note_request_routes_to_crm_upsert(self):
        from backend.services.os_workers.lead_nurture import _choose_action_type

        assert _choose_action_type("Log a note that they're still thinking") == (
            "crm.contact_upsert"
        )
        assert _choose_action_type("Add a CRM note for Jane") == "crm.contact_upsert"

    def test_email_directive_beats_other_channels(self):
        from backend.services.os_workers.lead_nurture import _choose_action_type

        assert _choose_action_type("Email Jane and also text her") == "email.send"
        assert _choose_action_type("Send an email reminder") == "email.send"


# ===========================================================================
# campaign worker — runtime channel routing (1:N action mapping)
# ===========================================================================


class TestCampaignChannelRouting:
    """Owner request picks the social action at worker runtime.

    campaign is a 1:N worker — three registered handlers consume its
    deliverable: ``gbp.post``, ``social.instagram.post``,
    ``social.facebook.post``. Default is GBP (universal SMB reach, no
    follower base, helps local SEO). Explicit channel directives win.
    """

    def test_defaults_to_gbp_when_no_channel_directive(self):
        from backend.services.os_workers.campaign import _choose_action_type

        assert _choose_action_type("Draft a summer sale campaign") == "gbp.post"
        assert _choose_action_type("") == "gbp.post"

    def test_instagram_directive_routes_to_instagram(self):
        from backend.services.os_workers.campaign import _choose_action_type

        assert _choose_action_type("Post to Instagram for our sale") == (
            "social.instagram.post"
        )
        assert _choose_action_type("Make an IG post") == "social.instagram.post"

    def test_facebook_directive_routes_to_facebook(self):
        from backend.services.os_workers.campaign import _choose_action_type

        assert _choose_action_type("Post on Facebook about the event") == (
            "social.facebook.post"
        )
        assert _choose_action_type("Write a FB post") == "social.facebook.post"

    def test_gbp_directive_routes_to_gbp(self):
        from backend.services.os_workers.campaign import _choose_action_type

        assert _choose_action_type("Create a Google Business post") == "gbp.post"
        assert _choose_action_type("Draft a GBP update") == "gbp.post"


# ===========================================================================
# Group C: bi-directional mirror (OS assistant → legacy channel store)
# ===========================================================================


class TestOutboundMirrorWidget:
    """OS assistant replies on widget-sourced threads must land in chat_messages.

    Customer typed in widget → bridge_widget pushed into OS → orchestrator
    answered → assistant_message lives in os_messages. But the widget reads
    from chat_messages, not os_messages. So without the outbound mirror the
    customer never sees the OS reply.

    Mirror contract:
    - widget source + session_id in metadata → insert chat_messages row,
      tag with os_message_id for idempotency, return ``mirrored``.
    - widget source missing session_id → ``skipped:no_session``.
    - owner thread (no source) → ``skipped:no_channel``.
    - sms/email/facebook → ``skipped:outbound_not_implemented``
      (those need actual provider sends, not just a DB write).
    - duplicate call with same os_message_id → only one chat_messages row.
    - DB exception → ``error:<reason>``, no raise.
    """

    def _thread(self, *, source: str | None, session_id: str | None = None) -> dict:
        meta = {"session_id": session_id} if session_id is not None else None
        return {
            "id": "thread-1",
            "source": source,
            "source_metadata": meta,
        }

    def _assistant(self, content: str = "Hello there") -> dict:
        return {
            "id": "os-msg-1",
            "thread_id": "thread-1",
            "role": "assistant",
            "content": content,
        }

    async def test_widget_thread_mirrors_to_chat_messages(self):
        from backend.services.os_outbound_mirror import mirror_assistant_message

        sb = FakeSupabase()
        result = await mirror_assistant_message(
            sb,
            _TENANT,
            self._thread(source="widget", session_id="session-abc"),
            self._assistant("Hi! How can I help?"),
        )
        assert result["status"] == "mirrored"
        rows = sb.store.get("chat_messages", [])
        assert len(rows) == 1
        row = rows[0]
        assert row["tenant_id"] == _TENANT
        assert row["session_id"] == "session-abc"
        assert row["role"] == "assistant"
        assert row["content"] == "Hi! How can I help?"
        assert row["os_message_id"] == "os-msg-1"

    async def test_widget_thread_missing_session_id_is_skipped(self):
        from backend.services.os_outbound_mirror import mirror_assistant_message

        sb = FakeSupabase()
        result = await mirror_assistant_message(
            sb,
            _TENANT,
            self._thread(source="widget", session_id=None),
            self._assistant(),
        )
        assert result["status"] == "skipped:no_session"
        assert sb.store.get("chat_messages", []) == []

    async def test_owner_thread_with_no_source_is_skipped(self):
        from backend.services.os_outbound_mirror import mirror_assistant_message

        sb = FakeSupabase()
        result = await mirror_assistant_message(
            sb,
            _TENANT,
            self._thread(source=None),
            self._assistant(),
        )
        assert result["status"] == "skipped:no_channel"
        assert sb.store.get("chat_messages", []) == []

    async def test_mirror_is_idempotent_on_replay(self):
        from backend.services.os_outbound_mirror import mirror_assistant_message

        sb = FakeSupabase()
        thread = self._thread(source="widget", session_id="session-abc")
        assistant = self._assistant("Idempotent reply")

        first = await mirror_assistant_message(sb, _TENANT, thread, assistant)
        second = await mirror_assistant_message(sb, _TENANT, thread, assistant)

        assert first["status"] == "mirrored"
        assert second["status"] == "skipped:already_mirrored"
        assert len(sb.store.get("chat_messages", [])) == 1

    async def test_db_failure_returns_error_status(self):
        from backend.services.os_outbound_mirror import mirror_assistant_message

        sb = FakeSupabase()
        sb.raise_on.add(("chat_messages", "insert"))
        result = await mirror_assistant_message(
            sb,
            _TENANT,
            self._thread(source="widget", session_id="session-abc"),
            self._assistant(),
        )
        assert result["status"].startswith("error:")
        assert sb.store.get("chat_messages", []) == []


class TestOutboundMirrorSMS:
    """OS assistant replies on sms-sourced threads must dispatch outbound SMS.

    Customer texted in → twilio webhook bridged into OS → orchestrator
    answered → assistant_message lives in os_messages. Without phase-2
    outbound send the customer never sees the OS reply.

    Mirror contract for SMS:
    - sms source + recipient phone in metadata + non-empty content
      → call Twilio (BYO if connected, else platform pool), return
      ``mirrored`` with provider tag on success.
    - sms source + ``stop_keyword=True`` in metadata → ``skipped:stop_keyword``
      (TCPA: never send to unsubscribed numbers).
    - sms source + missing ``from`` phone → ``skipped:no_session``.
    - sms source + empty assistant content → ``skipped:empty_content``.
    - twilio transport returns ``success=False`` → ``error:sms_send:<detail>``.
    """

    def _sms_thread(
        self,
        *,
        from_phone: str | None = "+15551234567",
        to_phone: str = "+15559990000",
        stop_keyword: bool = False,
    ) -> dict:
        meta: dict[str, Any] = {"provider": "twilio"}
        if from_phone is not None:
            meta["from"] = from_phone
        meta["to"] = to_phone
        if stop_keyword:
            meta["stop_keyword"] = True
        return {
            "id": "thread-sms-1",
            "source": "sms",
            "source_metadata": meta,
        }

    def _assistant(self, content: str = "Booked 2pm Tuesday") -> dict:
        return {
            "id": "os-msg-sms-1",
            "thread_id": "thread-sms-1",
            "role": "assistant",
            "content": content,
        }

    async def test_sms_sends_via_byo_when_connected(self, monkeypatch):
        import backend.services.os_outbound_mirror as mod
        import backend.services.twilio_tenant as twilio_tenant

        captured: dict[str, Any] = {}

        async def fake_byo_send(*, tenant_id, to, body):
            captured["tenant_id"] = tenant_id
            captured["to"] = to
            captured["body"] = body
            return {"success": True, "detail": "sent", "message_sid": "SMxxx"}

        monkeypatch.setattr(twilio_tenant, "is_connected", lambda tid: True)
        monkeypatch.setattr(twilio_tenant, "send_sms_via_tenant", fake_byo_send)

        result = await mod.mirror_assistant_message(
            FakeSupabase(),
            _TENANT,
            self._sms_thread(),
            self._assistant("Booked 2pm Tuesday"),
        )
        assert result["status"] == "mirrored"
        assert result["provider"] == "twilio_byo"
        assert result["message_sid"] == "SMxxx"
        assert captured == {
            "tenant_id": _TENANT,
            "to": "+15551234567",
            "body": "Booked 2pm Tuesday",
        }

    async def test_sms_falls_back_to_platform_when_no_byo(self, monkeypatch):
        import backend.services.os_outbound_mirror as mod
        import backend.services.twilio_service as twilio_service
        import backend.services.twilio_tenant as twilio_tenant

        captured: dict[str, Any] = {}

        async def fake_platform_send(to, body, from_number=None):
            captured["to"] = to
            captured["body"] = body
            return True

        async def should_not_call(**kwargs):
            raise AssertionError("BYO sender called but BYO is disconnected")

        monkeypatch.setattr(twilio_tenant, "is_connected", lambda tid: False)
        monkeypatch.setattr(twilio_tenant, "send_sms_via_tenant", should_not_call)
        monkeypatch.setattr(twilio_service, "send_sms", fake_platform_send)

        result = await mod.mirror_assistant_message(
            FakeSupabase(),
            _TENANT,
            self._sms_thread(from_phone="+15557654321"),
            self._assistant("Platform path reply"),
        )
        assert result["status"] == "mirrored"
        assert result["provider"] == "twilio_platform"
        assert captured == {"to": "+15557654321", "body": "Platform path reply"}

    async def test_sms_byo_failure_returns_error(self, monkeypatch):
        import backend.services.os_outbound_mirror as mod
        import backend.services.twilio_tenant as twilio_tenant

        async def fake_byo_send(*, tenant_id, to, body):
            return {"success": False, "detail": "twilio HTTP 400: invalid To"}

        monkeypatch.setattr(twilio_tenant, "is_connected", lambda tid: True)
        monkeypatch.setattr(twilio_tenant, "send_sms_via_tenant", fake_byo_send)

        result = await mod.mirror_assistant_message(
            FakeSupabase(), _TENANT, self._sms_thread(), self._assistant()
        )
        assert result["status"].startswith("error:sms_send:")
        assert "invalid To" in result["status"]

    async def test_sms_platform_failure_returns_error(self, monkeypatch):
        import backend.services.os_outbound_mirror as mod
        import backend.services.twilio_service as twilio_service
        import backend.services.twilio_tenant as twilio_tenant

        async def fake_platform_send(to, body, from_number=None):
            return False

        monkeypatch.setattr(twilio_tenant, "is_connected", lambda tid: False)
        monkeypatch.setattr(twilio_service, "send_sms", fake_platform_send)

        result = await mod.mirror_assistant_message(
            FakeSupabase(), _TENANT, self._sms_thread(), self._assistant()
        )
        assert result["status"] == "error:sms_send:platform_send_failed"

    async def test_sms_stop_keyword_suppresses_outbound(self, monkeypatch):
        import backend.services.os_outbound_mirror as mod
        import backend.services.twilio_service as twilio_service
        import backend.services.twilio_tenant as twilio_tenant

        async def should_not_call(*args, **kwargs):
            raise AssertionError("outbound called on stop_keyword thread")

        monkeypatch.setattr(twilio_tenant, "is_connected", lambda tid: True)
        monkeypatch.setattr(twilio_tenant, "send_sms_via_tenant", should_not_call)
        monkeypatch.setattr(twilio_service, "send_sms", should_not_call)

        result = await mod.mirror_assistant_message(
            FakeSupabase(),
            _TENANT,
            self._sms_thread(stop_keyword=True),
            self._assistant(),
        )
        assert result["status"] == "skipped:stop_keyword"

    async def test_sms_missing_from_phone_is_skipped(self, monkeypatch):
        import backend.services.os_outbound_mirror as mod
        import backend.services.twilio_service as twilio_service
        import backend.services.twilio_tenant as twilio_tenant

        async def should_not_call(*args, **kwargs):
            raise AssertionError("outbound called without recipient phone")

        monkeypatch.setattr(twilio_tenant, "is_connected", lambda tid: True)
        monkeypatch.setattr(twilio_tenant, "send_sms_via_tenant", should_not_call)
        monkeypatch.setattr(twilio_service, "send_sms", should_not_call)

        result = await mod.mirror_assistant_message(
            FakeSupabase(),
            _TENANT,
            self._sms_thread(from_phone=None),
            self._assistant(),
        )
        assert result["status"] == "skipped:no_session"

    async def test_sms_empty_content_is_skipped(self, monkeypatch):
        import backend.services.os_outbound_mirror as mod
        import backend.services.twilio_service as twilio_service
        import backend.services.twilio_tenant as twilio_tenant

        async def should_not_call(*args, **kwargs):
            raise AssertionError("outbound called with empty content")

        monkeypatch.setattr(twilio_tenant, "is_connected", lambda tid: True)
        monkeypatch.setattr(twilio_tenant, "send_sms_via_tenant", should_not_call)
        monkeypatch.setattr(twilio_service, "send_sms", should_not_call)

        result = await mod.mirror_assistant_message(
            FakeSupabase(), _TENANT, self._sms_thread(), self._assistant(content="   ")
        )
        assert result["status"] == "skipped:empty_content"


class TestOutboundMirrorEmail:
    """OS assistant replies on email-sourced threads must dispatch outbound email.

    Customer emailed in → Postmark/Mailgun inbound webhook bridged into OS →
    orchestrator answered → assistant_message lives in os_messages. Without
    phase-2 outbound the customer never sees the OS reply on their inbox.

    Mirror contract for email:
    - email source + recipient address in metadata + non-empty content →
      call Resend via send_email_reply with Re:-prefixed subject and
      In-Reply-To header threading against source_thread_id; return
      ``mirrored`` with provider=resend on success.
    - existing ``Re:`` prefix on inbound subject must NOT be doubled
      (case-insensitive idempotent).
    - empty inbound subject → fallback ``Re: your message``.
    - email source + missing ``from`` address → ``skipped:no_session``.
    - email source + empty assistant content → ``skipped:empty_content``.
    - Resend transport returns ``success=False`` → ``error:email_send:<detail>``.
    """

    def _email_thread(
        self,
        *,
        from_addr: str | None = "customer@example.com",
        subject: str | None = "Question about pricing",
        source_thread_id: str | None = "<orig-message-id@mail.example.com>",
    ) -> dict:
        meta: dict[str, Any] = {"provider": "postmark"}
        if from_addr is not None:
            meta["from"] = from_addr
        if subject is not None:
            meta["subject"] = subject
        return {
            "id": "thread-email-1",
            "source": "email",
            "source_metadata": meta,
            "source_thread_id": source_thread_id,
        }

    def _assistant(self, content: str = "Pricing starts at $99/mo.") -> dict:
        return {
            "id": "os-msg-email-1",
            "thread_id": "thread-email-1",
            "role": "assistant",
            "content": content,
        }

    async def test_email_sends_with_re_prefix_when_inbound_subject_lacks_one(
        self, monkeypatch
    ):
        import backend.services.email_sender as email_sender
        import backend.services.os_outbound_mirror as mod

        captured: dict[str, Any] = {}

        async def fake_reply(
            *, to, subject, body_text, tenant_id, in_reply_to="", references=""
        ):
            captured["to"] = to
            captured["subject"] = subject
            captured["body_text"] = body_text
            captured["tenant_id"] = tenant_id
            captured["in_reply_to"] = in_reply_to
            captured["references"] = references
            return {"success": True, "detail": "sent", "resend_id": "rsnd_abc"}

        monkeypatch.setattr(email_sender, "send_email_reply", fake_reply)

        result = await mod.mirror_assistant_message(
            FakeSupabase(),
            _TENANT,
            self._email_thread(subject="Question about pricing"),
            self._assistant("Pricing starts at $99/mo."),
        )
        assert result["status"] == "mirrored"
        assert result["provider"] == "resend"
        assert result["resend_id"] == "rsnd_abc"
        assert captured["to"] == "customer@example.com"
        assert captured["subject"] == "Re: Question about pricing"
        assert captured["body_text"] == "Pricing starts at $99/mo."
        assert captured["tenant_id"] == _TENANT
        assert captured["in_reply_to"] == "<orig-message-id@mail.example.com>"

    async def test_email_does_not_double_prefix_existing_re(self, monkeypatch):
        import backend.services.email_sender as email_sender
        import backend.services.os_outbound_mirror as mod

        captured: dict[str, Any] = {}

        async def fake_reply(
            *, to, subject, body_text, tenant_id, in_reply_to="", references=""
        ):
            captured["subject"] = subject
            return {"success": True, "detail": "sent", "resend_id": "rsnd_xyz"}

        monkeypatch.setattr(email_sender, "send_email_reply", fake_reply)

        result = await mod.mirror_assistant_message(
            FakeSupabase(),
            _TENANT,
            self._email_thread(subject="Re: Question about pricing"),
            self._assistant(),
        )
        assert result["status"] == "mirrored"
        assert captured["subject"] == "Re: Question about pricing"

        # lowercase + mixed case variants — all idempotent
        for inbound in ("re: lowercase", "RE: SHOUTING", "Re:no-space-after"):
            captured.clear()
            result = await mod.mirror_assistant_message(
                FakeSupabase(),
                _TENANT,
                self._email_thread(subject=inbound),
                self._assistant(),
            )
            assert result["status"] == "mirrored"
            assert (
                captured["subject"] == inbound
            ), f"existing Re: prefix lost or doubled for {inbound!r}"

    async def test_email_uses_fallback_subject_when_inbound_subject_missing(
        self, monkeypatch
    ):
        import backend.services.email_sender as email_sender
        import backend.services.os_outbound_mirror as mod

        captured: dict[str, Any] = {}

        async def fake_reply(
            *, to, subject, body_text, tenant_id, in_reply_to="", references=""
        ):
            captured["subject"] = subject
            return {"success": True, "detail": "sent", "resend_id": "rsnd_def"}

        monkeypatch.setattr(email_sender, "send_email_reply", fake_reply)

        # Empty string subject
        result = await mod.mirror_assistant_message(
            FakeSupabase(),
            _TENANT,
            self._email_thread(subject=""),
            self._assistant(),
        )
        assert result["status"] == "mirrored"
        assert captured["subject"] == "Re: your message"

        # Whitespace-only subject
        captured.clear()
        result = await mod.mirror_assistant_message(
            FakeSupabase(),
            _TENANT,
            self._email_thread(subject="   "),
            self._assistant(),
        )
        assert result["status"] == "mirrored"
        assert captured["subject"] == "Re: your message"

    async def test_email_missing_recipient_is_skipped(self, monkeypatch):
        import backend.services.email_sender as email_sender
        import backend.services.os_outbound_mirror as mod

        async def should_not_call(*args, **kwargs):
            raise AssertionError("send_email_reply called without recipient address")

        monkeypatch.setattr(email_sender, "send_email_reply", should_not_call)

        result = await mod.mirror_assistant_message(
            FakeSupabase(),
            _TENANT,
            self._email_thread(from_addr=None),
            self._assistant(),
        )
        assert result["status"] == "skipped:no_session"

    async def test_email_empty_content_is_skipped(self, monkeypatch):
        import backend.services.email_sender as email_sender
        import backend.services.os_outbound_mirror as mod

        async def should_not_call(*args, **kwargs):
            raise AssertionError("send_email_reply called with empty body")

        monkeypatch.setattr(email_sender, "send_email_reply", should_not_call)

        result = await mod.mirror_assistant_message(
            FakeSupabase(),
            _TENANT,
            self._email_thread(),
            self._assistant(content="   "),
        )
        assert result["status"] == "skipped:empty_content"

    async def test_email_send_failure_returns_error(self, monkeypatch):
        import backend.services.email_sender as email_sender
        import backend.services.os_outbound_mirror as mod

        async def failing_reply(**kwargs):
            return {"success": False, "detail": "resend HTTP 422: invalid To"}

        monkeypatch.setattr(email_sender, "send_email_reply", failing_reply)

        result = await mod.mirror_assistant_message(
            FakeSupabase(),
            _TENANT,
            self._email_thread(),
            self._assistant(),
        )
        assert result["status"].startswith("error:email_send:")
        assert "invalid To" in result["status"]

    async def test_email_in_reply_to_falls_back_to_empty_when_missing(
        self, monkeypatch
    ):
        import backend.services.email_sender as email_sender
        import backend.services.os_outbound_mirror as mod

        captured: dict[str, Any] = {}

        async def fake_reply(
            *, to, subject, body_text, tenant_id, in_reply_to="", references=""
        ):
            captured["in_reply_to"] = in_reply_to
            return {"success": True, "detail": "sent", "resend_id": "rsnd_ghi"}

        monkeypatch.setattr(email_sender, "send_email_reply", fake_reply)

        result = await mod.mirror_assistant_message(
            FakeSupabase(),
            _TENANT,
            self._email_thread(source_thread_id=None),
            self._assistant(),
        )
        assert result["status"] == "mirrored"
        assert captured["in_reply_to"] == ""


class TestOutboundMirrorFacebook:
    """OS assistant replies on facebook-sourced threads must DM the customer.

    Customer DM'd the Page → FB webhook bridged into OS → orchestrator
    answered → assistant_message lives in os_messages. Without phase-2
    outbound the customer never sees the OS reply on Messenger.

    Mirror contract for Facebook:
    - facebook source + ``sender_id`` (PSID) in metadata + non-empty content
      → call FB Send API via send_messenger_reply; return ``mirrored`` with
      provider=messenger + message_id.
    - missing PSID → ``skipped:no_session``.
    - empty/whitespace content → ``skipped:empty_content``.
    - send_messenger_reply returns ``success=False`` → ``error:facebook_send:<detail>``
      (no_page when token missing, http_<status>:<body> when API rejects).
    - send_messenger_reply raises → ``error:facebook_send:<exc>``.
    """

    def _fb_thread(
        self,
        *,
        psid: str | None = "psid-cust-123",
        page_id: str = "page-tenant-1",
    ) -> dict:
        meta: dict[str, Any] = {"provider": "facebook", "page_id": page_id}
        if psid is not None:
            meta["sender_id"] = psid
        return {
            "id": "thread-fb-1",
            "source": "facebook",
            "source_metadata": meta,
            "source_thread_id": f"{page_id}:{psid}" if psid else page_id,
        }

    def _assistant(self, content: str = "Hi! Yes we're open Saturday 9-5.") -> dict:
        return {
            "id": "os-msg-fb-1",
            "thread_id": "thread-fb-1",
            "role": "assistant",
            "content": content,
        }

    async def test_facebook_sends_via_messenger_send_api_on_success(self, monkeypatch):
        import backend.services.facebook_messenger as fb_messenger
        import backend.services.os_outbound_mirror as mod

        captured: dict[str, Any] = {}

        async def fake_send(*, tenant_id, recipient_psid, content):
            captured["tenant_id"] = tenant_id
            captured["recipient_psid"] = recipient_psid
            captured["content"] = content
            return {
                "success": True,
                "message_id": "mid_fb_abc",
                "recipient_id": recipient_psid,
            }

        monkeypatch.setattr(fb_messenger, "send_messenger_reply", fake_send)

        result = await mod.mirror_assistant_message(
            FakeSupabase(),
            _TENANT,
            self._fb_thread(),
            self._assistant(),
        )
        assert result["status"] == "mirrored"
        assert result["provider"] == "messenger"
        assert result["message_id"] == "mid_fb_abc"
        assert captured["tenant_id"] == _TENANT
        assert captured["recipient_psid"] == "psid-cust-123"
        assert captured["content"] == "Hi! Yes we're open Saturday 9-5."

    async def test_facebook_accepts_legacy_psid_key_in_metadata(self, monkeypatch):
        """Older threads may store the PSID under ``psid`` instead of ``sender_id``."""
        import backend.services.facebook_messenger as fb_messenger
        import backend.services.os_outbound_mirror as mod

        captured: dict[str, Any] = {}

        async def fake_send(*, tenant_id, recipient_psid, content):
            captured["recipient_psid"] = recipient_psid
            return {"success": True, "message_id": "mid_legacy"}

        monkeypatch.setattr(fb_messenger, "send_messenger_reply", fake_send)

        thread = {
            "id": "thread-fb-legacy",
            "source": "facebook",
            "source_metadata": {"psid": "psid-legacy-9"},
        }
        result = await mod.mirror_assistant_message(
            FakeSupabase(), _TENANT, thread, self._assistant()
        )
        assert result["status"] == "mirrored"
        assert captured["recipient_psid"] == "psid-legacy-9"

    async def test_facebook_missing_psid_is_skipped(self, monkeypatch):
        import backend.services.facebook_messenger as fb_messenger
        import backend.services.os_outbound_mirror as mod

        async def should_not_call(**kwargs):
            raise AssertionError("messenger send called without recipient PSID")

        monkeypatch.setattr(fb_messenger, "send_messenger_reply", should_not_call)

        result = await mod.mirror_assistant_message(
            FakeSupabase(), _TENANT, self._fb_thread(psid=None), self._assistant()
        )
        assert result["status"] == "skipped:no_session"

    async def test_facebook_empty_content_is_skipped(self, monkeypatch):
        import backend.services.facebook_messenger as fb_messenger
        import backend.services.os_outbound_mirror as mod

        async def should_not_call(**kwargs):
            raise AssertionError("messenger send called with empty content")

        monkeypatch.setattr(fb_messenger, "send_messenger_reply", should_not_call)

        for blank in ["", "   ", "\n\t  \n"]:
            result = await mod.mirror_assistant_message(
                FakeSupabase(),
                _TENANT,
                self._fb_thread(),
                self._assistant(content=blank),
            )
            assert (
                result["status"] == "skipped:empty_content"
            ), f"expected empty_content skip for {blank!r}, got {result['status']}"

    async def test_facebook_no_page_token_returns_error(self, monkeypatch):
        """send_messenger_reply returns success=False, detail=no_page when token missing."""
        import backend.services.facebook_messenger as fb_messenger
        import backend.services.os_outbound_mirror as mod

        async def fake_send(*, tenant_id, recipient_psid, content):
            return {"success": False, "detail": "no_page"}

        monkeypatch.setattr(fb_messenger, "send_messenger_reply", fake_send)

        result = await mod.mirror_assistant_message(
            FakeSupabase(), _TENANT, self._fb_thread(), self._assistant()
        )
        assert result["status"].startswith("error:facebook_send:")
        assert "no_page" in result["status"]

    async def test_facebook_http_error_returns_error_with_status_code(
        self, monkeypatch
    ):
        """FB Send API returns 400 → mirror surfaces http_<status>:<body>."""
        import backend.services.facebook_messenger as fb_messenger
        import backend.services.os_outbound_mirror as mod

        async def fake_send(*, tenant_id, recipient_psid, content):
            return {
                "success": False,
                "detail": "http_400:(#100) Invalid parameter recipient.id",
            }

        monkeypatch.setattr(fb_messenger, "send_messenger_reply", fake_send)

        result = await mod.mirror_assistant_message(
            FakeSupabase(), _TENANT, self._fb_thread(), self._assistant()
        )
        assert result["status"].startswith("error:facebook_send:")
        assert "http_400" in result["status"]
        assert "Invalid parameter" in result["status"]

    async def test_facebook_send_exception_returns_error(self, monkeypatch):
        """send_messenger_reply raises → mirror catches and returns error."""
        import backend.services.facebook_messenger as fb_messenger
        import backend.services.os_outbound_mirror as mod

        async def fake_send(*, tenant_id, recipient_psid, content):
            raise RuntimeError("network down")

        monkeypatch.setattr(fb_messenger, "send_messenger_reply", fake_send)

        result = await mod.mirror_assistant_message(
            FakeSupabase(), _TENANT, self._fb_thread(), self._assistant()
        )
        assert result["status"].startswith("error:facebook_send:")
        assert "network down" in result["status"]


class TestThreadRunnerMirrorIntegration:
    """Runner wiring: widget-sourced thread → assistant reply mirrors to chat_messages."""

    def test_widget_sourced_thread_mirrors_assistant_answer(self):
        fake = FakeSupabase()
        fake.seed(
            "os_threads",
            {
                "id": "thread-widget-1",
                "client_id": _TENANT,
                "source": "widget",
                "source_metadata": {"session_id": "sess-xyz"},
                "title": "Widget chat",
                "updated_at": "2026-05-01T00:00:00+00:00",
            },
        )
        with patched_db(fake), patched_orchestrator(
            '{"action": "answer", "reply": "Hi from OS"}'
        ):
            resp = client.post(
                "/api/v1/os/threads/thread-widget-1/messages",
                json={"content": "customer message"},
                headers=_auth(),
            )
        assert resp.status_code == 201
        chat_rows = fake.store.get("chat_messages", [])
        assert len(chat_rows) == 1
        assert chat_rows[0]["session_id"] == "sess-xyz"
        assert chat_rows[0]["role"] == "assistant"
        assert chat_rows[0]["content"] == "Hi from OS"
        assert chat_rows[0]["os_message_id"] == resp.json()["assistant_message"]["id"]

    def test_owner_sourced_thread_does_not_mirror(self):
        fake = FakeSupabase()
        _seed_thread(fake)
        with patched_db(fake), patched_orchestrator(
            '{"action": "answer", "reply": "owner reply"}'
        ):
            resp = client.post(
                "/api/v1/os/threads/thread-001/messages",
                json={"content": "hi"},
                headers=_auth(),
            )
        assert resp.status_code == 201
        assert fake.store.get("chat_messages", []) == []


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
            "backend.services.os_thread_runner.send_email", sender
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

    def test_pending_deliverables_returns_only_pending(self):
        fake = FakeSupabase()
        _seed_thread(fake)
        _seed_deliverable_run(fake, run_id="run-pending-1")
        _seed_deliverable_run(fake, run_id="run-pending-2")
        _seed_deliverable_run(fake, run_id="run-approved", status="approved")
        _seed_deliverable_run(fake, run_id="run-rejected", status="rejected")
        with patched_db(fake):
            resp = client.get("/api/v1/os/deliverables/pending", headers=_auth())
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 2
        run_ids = {item["run_id"] for item in body["items"]}
        assert run_ids == {"run-pending-1", "run-pending-2"}
        for item in body["items"]:
            assert item["title"] == "Draft"
            assert item["thread_id"] == "thread-001"

    def test_pending_deliverables_empty(self):
        fake = FakeSupabase()
        with patched_db(fake):
            resp = client.get("/api/v1/os/deliverables/pending", headers=_auth())
        assert resp.status_code == 200
        assert resp.json() == {"count": 0, "items": []}

    def test_pending_deliverables_scoped_to_tenant(self):
        fake = FakeSupabase()
        _seed_thread(fake)
        _seed_deliverable_run(fake, run_id="run-mine")
        # Seed a deliverable for a DIFFERENT tenant — must not leak.
        _seed_run(
            fake,
            "run-other-tenant",
            tenant="tenant-other",
            status="succeeded",
            deliverable={"title": "Leak", "body": "x"},
            deliverable_status="pending_approval",
        )
        with patched_db(fake):
            resp = client.get("/api/v1/os/deliverables/pending", headers=_auth())
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1
        assert body["items"][0]["run_id"] == "run-mine"


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


# ===========================================================================
# calendar.event.create — runtime provider dispatch (Google vs M365)
# ===========================================================================


class TestCalendarActionDispatch:
    """Single action_type dispatches to whichever provider the tenant connected.

    Booking worker emits one ``calendar.event.create`` action_type regardless
    of provider. Dispatch lives inside the handler so the worker stays
    provider-agnostic and tenants can swap providers without worker changes.
    """

    @staticmethod
    def _ctx() -> "object":
        from backend.services.os_actions.base import ActionContext

        return ActionContext(
            db=None,
            client_id=_TENANT,
            deliverable_id="del-1",
            action_run_id="run-1",
            action_type="calendar.event.create",
            deliverable={"body": "Book 30 min with Jane next Tuesday at 3pm UTC"},
            agent_run={"thread_id": "t-1"},
        )

    @staticmethod
    def _extracted_payload() -> dict:
        return {
            "summary": "Booking with Jane",
            "start_utc": "2026-06-09T15:00:00+00:00",
            "end_utc": "2026-06-09T15:30:00+00:00",
            "attendee_email": "jane@example.com",
            "description": "discovery call",
        }

    @pytest.mark.asyncio
    async def test_dispatches_to_google_when_google_integration_present(self):
        from backend.services.os_actions import calendar as calendar_action

        ctx = self._ctx()
        with patch.object(
            calendar_action,
            "_extract_event_payload",
            AsyncMock(return_value=self._extracted_payload()),
        ), patch.object(
            calendar_action.google_calendar,
            "get_integration",
            return_value={"id": "i1", "provider": "google_calendar"},
        ), patch.object(
            calendar_action.m365_calendar,
            "get_integration",
            return_value=None,
        ), patch.object(
            calendar_action.google_calendar,
            "create_calendar_event",
            return_value="google-event-123",
        ) as google_create, patch.object(
            calendar_action.m365_calendar,
            "create_calendar_event",
            return_value="m365-event-999",
        ) as m365_create:
            result = await calendar_action._run(ctx)

        assert result.status == "succeeded"
        assert result.response_payload["provider"] == "google_calendar"
        assert result.response_payload["event_id"] == "google-event-123"
        google_create.assert_called_once()
        m365_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatches_to_m365_when_only_m365_connected(self):
        from backend.services.os_actions import calendar as calendar_action

        ctx = self._ctx()
        with patch.object(
            calendar_action,
            "_extract_event_payload",
            AsyncMock(return_value=self._extracted_payload()),
        ), patch.object(
            calendar_action.google_calendar,
            "get_integration",
            return_value=None,
        ), patch.object(
            calendar_action.m365_calendar,
            "get_integration",
            return_value={"id": "i2", "provider": "m365_calendar"},
        ), patch.object(
            calendar_action.google_calendar,
            "create_calendar_event",
            return_value="google-event-123",
        ) as google_create, patch.object(
            calendar_action.m365_calendar,
            "create_calendar_event",
            return_value="m365-event-999",
        ) as m365_create:
            result = await calendar_action._run(ctx)

        assert result.status == "succeeded"
        assert result.response_payload["provider"] == "m365_calendar"
        assert result.response_payload["event_id"] == "m365-event-999"
        m365_create.assert_called_once()
        google_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_prefers_google_when_both_providers_connected(self):
        """Stable order — Google wins when both connected.

        Preserves behavior for existing google-connected tenants; M365 only
        activates for tenants that have ONLY m365_calendar.
        """
        from backend.services.os_actions import calendar as calendar_action

        ctx = self._ctx()
        with patch.object(
            calendar_action,
            "_extract_event_payload",
            AsyncMock(return_value=self._extracted_payload()),
        ), patch.object(
            calendar_action.google_calendar,
            "get_integration",
            return_value={"id": "i1", "provider": "google_calendar"},
        ), patch.object(
            calendar_action.m365_calendar,
            "get_integration",
            return_value={"id": "i2", "provider": "m365_calendar"},
        ), patch.object(
            calendar_action.google_calendar,
            "create_calendar_event",
            return_value="google-event-123",
        ) as google_create, patch.object(
            calendar_action.m365_calendar,
            "create_calendar_event",
            return_value="m365-event-999",
        ) as m365_create:
            result = await calendar_action._run(ctx)

        assert result.response_payload["provider"] == "google_calendar"
        google_create.assert_called_once()
        m365_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_fails_when_no_calendar_provider_connected(self):
        from backend.services.os_actions import calendar as calendar_action

        ctx = self._ctx()
        with patch.object(
            calendar_action,
            "_extract_event_payload",
            AsyncMock(return_value=self._extracted_payload()),
        ), patch.object(
            calendar_action.google_calendar,
            "get_integration",
            return_value=None,
        ), patch.object(
            calendar_action.m365_calendar,
            "get_integration",
            return_value=None,
        ):
            result = await calendar_action._run(ctx)

        assert result.status == "failed"
        assert result.error_detail is not None
        assert result.error_detail["stage"] == "connector"

    @pytest.mark.asyncio
    async def test_m365_create_failure_surfaces_provider_in_error(self):
        from backend.services.os_actions import calendar as calendar_action

        ctx = self._ctx()
        with patch.object(
            calendar_action,
            "_extract_event_payload",
            AsyncMock(return_value=self._extracted_payload()),
        ), patch.object(
            calendar_action.google_calendar,
            "get_integration",
            return_value=None,
        ), patch.object(
            calendar_action.m365_calendar,
            "get_integration",
            return_value={"id": "i2", "provider": "m365_calendar"},
        ), patch.object(
            calendar_action.m365_calendar,
            "create_calendar_event",
            return_value=None,
        ):
            result = await calendar_action._run(ctx)

        assert result.status == "failed"
        assert result.error_detail is not None
        assert result.error_detail["provider"] == "m365_calendar"
        assert result.error_detail["stage"] == "m365_calendar_create"


# ===========================================================================
# M365 OAuth router — tenant connects Microsoft 365 calendar
# ===========================================================================


class TestM365OAuthRoutes:
    """OAuth flow for Microsoft 365.

    Mirrors Google OAuth shape. State JWT carries tenant_id across the
    public callback (browser arrives via Azure AD redirect, not from SPA).
    """

    def test_m365_auth_returns_authorization_url(self):
        with patch(
            "backend.routers.integrations.m365_calendar.build_authorization_url",
            return_value="https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=x&state=signed-state",
        ) as build_url:
            resp = client.get("/api/v1/integrations/m365/auth", headers=_auth())
        assert resp.status_code == 200
        body = resp.json()
        assert "auth_url" in body
        assert "login.microsoftonline.com" in body["auth_url"]
        build_url.assert_called_once()

    def test_m365_auth_requires_authentication(self):
        resp = client.get("/api/v1/integrations/m365/auth")
        # 422 from FastAPI's missing-header validator; 401/403 from auth dep.
        assert resp.status_code in (401, 403, 422)

    def test_m365_callback_exchanges_code_and_saves_integration(self):
        from backend.routers.integrations import _encode_state

        state = _encode_state(_TENANT)
        token_payload = {
            "access_token": "graph-access-token",
            "refresh_token": "graph-refresh-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        with patch(
            "backend.routers.integrations.m365_calendar.exchange_code",
            return_value=token_payload,
        ) as exchange, patch(
            "backend.routers.integrations._fetch_m365_profile",
            return_value={"email": "user@contoso.com", "calendar_name": "User Name"},
        ), patch(
            "backend.routers.integrations.m365_calendar.save_integration"
        ) as save:
            resp = client.get(
                f"/api/v1/integrations/m365/callback?code=auth-code-123&state={state}",
                follow_redirects=False,
            )

        exchange.assert_called_once()
        save.assert_called_once()
        saved_kwargs = save.call_args.kwargs
        assert saved_kwargs["tenant_id"] == _TENANT
        assert saved_kwargs["access_token"] == "graph-access-token"
        assert saved_kwargs["refresh_token"] == "graph-refresh-token"
        assert saved_kwargs["metadata"]["email"] == "user@contoso.com"
        # 200 fallback HTML when no frontend_url; 307 redirect otherwise.
        assert resp.status_code in (200, 307)

    def test_m365_callback_rejects_missing_refresh_token(self):
        """Without offline_access scope we cannot refresh past 1h. Refuse to persist."""
        from backend.routers.integrations import _encode_state

        state = _encode_state(_TENANT)
        # No refresh_token in response.
        token_payload = {
            "access_token": "graph-access-token",
            "expires_in": 3600,
        }

        with patch(
            "backend.routers.integrations.m365_calendar.exchange_code",
            return_value=token_payload,
        ), patch("backend.routers.integrations.m365_calendar.save_integration") as save:
            resp = client.get(
                f"/api/v1/integrations/m365/callback?code=auth-code-123&state={state}",
                follow_redirects=False,
            )

        assert resp.status_code == 400
        assert "offline_access" in resp.json()["detail"]
        save.assert_not_called()

    def test_m365_callback_rejects_invalid_state(self):
        with patch(
            "backend.routers.integrations.m365_calendar.exchange_code"
        ) as exchange:
            resp = client.get(
                "/api/v1/integrations/m365/callback?code=auth-code&state=tampered-jwt",
                follow_redirects=False,
            )
        assert resp.status_code == 400
        exchange.assert_not_called()

    def test_m365_status_returns_disconnected_when_no_integration(self):
        with patch(
            "backend.routers.integrations.m365_calendar.get_integration",
            return_value=None,
        ):
            resp = client.get("/api/v1/integrations/m365/status", headers=_auth())
        assert resp.status_code == 200
        body = resp.json()
        assert body == {"connected": False, "email": None, "calendar_name": None}

    def test_m365_status_returns_connected_with_metadata(self):
        with patch(
            "backend.routers.integrations.m365_calendar.get_integration",
            return_value={
                "id": "i1",
                "provider": "m365_calendar",
                "metadata": {
                    "email": "user@contoso.com",
                    "calendar_name": "User Name",
                },
            },
        ):
            resp = client.get("/api/v1/integrations/m365/status", headers=_auth())
        assert resp.status_code == 200
        body = resp.json()
        assert body["connected"] is True
        assert body["email"] == "user@contoso.com"
        assert body["calendar_name"] == "User Name"

    def test_m365_disconnect_calls_delete_integration(self):
        with patch(
            "backend.routers.integrations.m365_calendar.delete_integration"
        ) as delete:
            resp = client.delete("/api/v1/integrations/m365", headers=_auth())
        assert resp.status_code == 200
        assert resp.json() == {"status": "disconnected"}
        delete.assert_called_once_with(_TENANT)
