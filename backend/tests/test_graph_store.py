"""SupabaseCheckpointer contracts (backend/graph/store.py).

The graph runtime awaits this class at every superstep boundary, so the
contracts that matter are:
1. save() UPSERTS one row per run (keyed on run_id) — not one row per superstep.
2. load() round-trips a Checkpoint faithfully, nested interrupt/budget included.
3. load() distinguishes "no such run" (None) from "DB blew up" (raises).
4. record_step() appends to the step ledger.
5. A failing write is logged and swallowed; a failing read is not.
"""

import logging
from unittest.mock import MagicMock

import pytest

from backend.graph.checkpoint import (
    STATUS_AWAITING_INPUT,
    STATUS_RUNNING,
    Checkpoint,
    StepRecord,
)
from backend.graph.store import RUNS_TABLE, STEPS_TABLE, SupabaseCheckpointer
from backend.tests.fake_supabase import db as _db

RUN_ID = "11111111-1111-4111-8111-111111111111"
TENANT_ID = "22222222-2222-4222-8222-222222222222"

# An awaiting_input checkpoint — the richest shape the runtime writes: nested
# interrupt payloads, banked sibling results, and a budget snapshot.
INTERRUPT = {
    "nodes": ["approve"],
    "reason": "needs human approval",
    "payloads": {"approve": {"quote": 1250, "currency": "usd"}},
    "pending_results": [
        {
            "node": "draft",
            "updates": {"findings": [{"id": 7, "score": 0.91}]},
            "goto": ["approve"],
            "meta": {"tokens": 412},
        }
    ],
}
BUDGET = {"supersteps": 3, "tokens": 412, "nodes": {"draft": 1}, "max_tokens": 50000}


def _checkpoint(**overrides) -> Checkpoint:
    base = dict(
        run_id=RUN_ID,
        graph_name="triage",
        graph_version="2",
        superstep=3,
        status=STATUS_AWAITING_INPUT,
        state={"lead_id": "abc", "findings": [{"id": 7, "score": 0.91}]},
        frontier=["approve"],
        budget=BUDGET,
        tenant_id=TENANT_ID,
        interrupt=INTERRUPT,
    )
    base.update(overrides)
    return Checkpoint(**base)


def _run_row(checkpoint: Checkpoint) -> dict:
    """A graph_runs row as PostgREST would hand it back."""
    row = checkpoint.to_dict()
    row["id"] = row.pop("run_id")
    row["updated_at"] = "2026-07-27T00:00:00+00:00"
    return row


def _raising_client(exc: Exception = None) -> MagicMock:
    client = MagicMock()
    client.table.side_effect = exc or RuntimeError("supabase is down")
    return client


class TestSave:
    async def test_save_upserts_one_row_keyed_on_run_id(self):
        client = _db({RUNS_TABLE: []})
        await SupabaseCheckpointer(client).save(_checkpoint())

        calls = [c for c in client._sink if c[0] == RUNS_TABLE]
        methods = [method for _, method, _ in calls]
        assert methods == ["upsert", "execute"]
        assert "insert" not in methods

        row = calls[0][2][0]
        assert row["id"] == RUN_ID
        assert row["tenant_id"] == TENANT_ID
        assert row["graph_name"] == "triage"
        assert row["graph_version"] == "2"
        assert row["status"] == STATUS_AWAITING_INPUT
        assert row["superstep"] == 3
        assert row["frontier"] == ["approve"]
        assert row["budget"] == BUDGET
        assert row["interrupt"] == INTERRUPT
        assert row["error"] is None
        assert row["updated_at"]
        # created_at is the column default — writing it would push the run's
        # birth timestamp forward at every superstep.
        assert "created_at" not in row

    async def test_repeated_save_stays_an_upsert(self):
        """A resumed run re-writes the boundary it resumed from."""
        client = _db({RUNS_TABLE: []})
        store = SupabaseCheckpointer(client)
        await store.save(_checkpoint())
        await store.save(_checkpoint(status=STATUS_RUNNING, superstep=4))

        upserts = [c for c in client._sink if c[1] == "upsert"]
        assert len(upserts) == 2
        assert {c[2][0]["id"] for c in upserts} == {RUN_ID}
        assert [c[2][0]["superstep"] for c in upserts] == [3, 4]

    async def test_save_swallows_db_failure_and_logs(self, caplog):
        store = SupabaseCheckpointer(_raising_client())

        with caplog.at_level(logging.ERROR, logger="backend.graph.store"):
            assert await store.save(_checkpoint()) is None

        assert "graph.store.save_failed" in caplog.text
        assert "supabase is down" in caplog.text


class TestLoad:
    async def test_load_round_trips_checkpoint(self):
        original = _checkpoint()
        client = _db({RUNS_TABLE: [_run_row(original)]})

        loaded = await SupabaseCheckpointer(client).load(RUN_ID)

        assert isinstance(loaded, Checkpoint)
        assert loaded.run_id == RUN_ID
        assert loaded.tenant_id == TENANT_ID
        assert loaded.graph_name == "triage"
        assert loaded.graph_version == "2"
        assert loaded.superstep == 3
        assert loaded.status == STATUS_AWAITING_INPUT
        assert loaded.state == original.state
        assert loaded.frontier == ["approve"]
        # Nested structures survive intact — resume() reads pending_results to
        # avoid re-running siblings that already succeeded.
        assert loaded.budget == BUDGET
        assert loaded.interrupt == INTERRUPT
        assert loaded.interrupt["payloads"]["approve"]["quote"] == 1250
        assert loaded.interrupt["pending_results"][0]["updates"] == {
            "findings": [{"id": 7, "score": 0.91}]
        }

    async def test_load_filters_by_run_id(self):
        client = _db({RUNS_TABLE: [_run_row(_checkpoint())]})
        await SupabaseCheckpointer(client).load(RUN_ID)

        methods = [(m, a) for t, m, a in client._sink if t == RUNS_TABLE]
        assert ("eq", ("id", RUN_ID)) in methods

    async def test_load_returns_none_when_missing(self):
        client = _db({RUNS_TABLE: []})
        assert await SupabaseCheckpointer(client).load("nope") is None

    async def test_load_coerces_null_jsonb_columns(self):
        row = _run_row(_checkpoint())
        row.update(state=None, frontier=None, budget=None, superstep=None)
        client = _db({RUNS_TABLE: [row]})

        loaded = await SupabaseCheckpointer(client).load(RUN_ID)

        assert loaded.state == {}
        assert loaded.frontier == []
        assert loaded.budget == {}
        assert loaded.superstep == 0

    async def test_load_raises_on_db_failure(self):
        """Resuming from a checkpoint you could not read is not safe."""
        store = SupabaseCheckpointer(_raising_client())
        with pytest.raises(RuntimeError, match="supabase is down"):
            await store.load(RUN_ID)


class TestRecordStep:
    async def test_record_step_inserts_ledger_row(self):
        client = _db({STEPS_TABLE: []})
        step = StepRecord(
            run_id=RUN_ID,
            superstep=2,
            node="classify",
            status="ok",
            kind="agent",
            attempts=2,
            duration_ms=417,
            tokens=1290,
            updates={"score": 0.91},
            meta={"tokens": 1290},
            tenant_id=TENANT_ID,
        )

        await SupabaseCheckpointer(client).record_step(step)

        calls = [c for c in client._sink if c[0] == STEPS_TABLE]
        assert [method for _, method, _ in calls] == ["insert", "execute"]

        row = calls[0][2][0]
        assert row["run_id"] == RUN_ID
        assert row["tenant_id"] == TENANT_ID
        assert row["superstep"] == 2
        assert row["node"] == "classify"
        assert row["kind"] == "agent"
        assert row["status"] == "ok"
        assert row["attempts"] == 2
        assert row["duration_ms"] == 417
        assert row["tokens"] == 1290
        assert row["updates"] == {"score": 0.91}
        assert row["meta"] == {"tokens": 1290}
        assert row["error"] is None
        assert row["created_at"] == step.created_at

    async def test_record_step_swallows_db_failure_and_logs(self, caplog):
        store = SupabaseCheckpointer(_raising_client())
        step = StepRecord(run_id=RUN_ID, superstep=0, node="classify", status="ok")

        with caplog.at_level(logging.ERROR, logger="backend.graph.store"):
            assert await store.record_step(step) is None

        assert "graph.store.record_step_failed" in caplog.text


class TestHistory:
    async def test_history_returns_current_run_row(self):
        client = _db({RUNS_TABLE: [_run_row(_checkpoint())]})
        history = await SupabaseCheckpointer(client).history(RUN_ID)

        assert len(history) == 1
        assert history[0].run_id == RUN_ID
        assert history[0].superstep == 3

    async def test_history_empty_for_unknown_run(self):
        client = _db({RUNS_TABLE: []})
        assert await SupabaseCheckpointer(client).history("nope") == []


class TestClientResolution:
    async def test_defaults_to_service_supabase(self, monkeypatch):
        """No injected client -> resolve the service-role client lazily."""
        client = _db({RUNS_TABLE: []})
        import backend.models.database as database

        monkeypatch.setattr(database, "get_service_supabase", lambda: client)

        store = SupabaseCheckpointer()
        assert store._client is None  # not resolved at construction time
        await store.save(_checkpoint())

        assert [c[1] for c in client._sink] == ["upsert", "execute"]
