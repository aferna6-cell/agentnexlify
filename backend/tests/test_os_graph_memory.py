"""Knowledge-graph memory contracts (os_graph_memory).

Covers the pipeline the graph-memory ADR's revisit trigger brought to life:
1. Extraction parsing is hostile-input safe (fences, garbage, bad types).
2. accumulate_from_turn skips no-signal turns, upserts nodes with fact
   dedup + capped history, writes new facts through to semantic memory,
   and links edges only between nodes it actually created.
3. graph_kb_entries shapes memory into the engine's KbEntry {topic, answer}
   and never raises — memory enrichment can't break a turn.
"""

import pytest

from backend.services import os_graph_memory as g


# --- chainable supabase fake -------------------------------------------------


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, table):
        self._t = table
        self._filters = {}

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def insert(self, payload):
        row = {**payload, "id": f"{self._t.name}-{len(self._t.rows) + 1}"}
        # Mirror the schema defaults production supplies (migration 133).
        if self._t.name == "os_graph_nodes":
            row.setdefault("mention_count", 1)
        if self._t.name == "os_graph_edges":
            row.setdefault("observed_count", 1)
        self._t.rows.append(row)
        self._t.inserts.append(row)
        return _InsertExec([row])

    def update(self, patch):
        self._patch = patch
        return self

    def delete(self):
        self._deleting = True
        return self

    def execute(self):
        if getattr(self, "_deleting", False):
            kept, gone = [], []
            for r in self._t.rows:
                (gone if all(r.get(k) == v for k, v in self._filters.items()) else kept).append(r)
            self._t.rows[:] = kept
            return _Result(gone)
        if hasattr(self, "_patch"):
            out = []
            for r in self._t.rows:
                if all(r.get(k) == v for k, v in self._filters.items()):
                    r.update(self._patch)
                    out.append(r)
            return _Result(out)
        rows = [
            r
            for r in self._t.rows
            if all(r.get(k) == v for k, v in self._filters.items())
        ]
        return _Result(rows)


class _InsertExec:
    def __init__(self, rows):
        self._rows = rows

    def execute(self):
        return _Result(self._rows)


class _Table:
    def __init__(self, name):
        self.name = name
        self.rows: list[dict] = []
        self.inserts: list[dict] = []


class _FakeDB:
    def __init__(self):
        self.tables: dict[str, _Table] = {}

    def get(self, name):
        return self.tables.setdefault(name, _Table(name))


@pytest.fixture
def fake_db(monkeypatch):
    db = _FakeDB()
    monkeypatch.setattr(
        g, "tenant_table", lambda _db, table, client_id: _Query(db.get(table))
    )
    return db


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    async def fake_embed(_text):
        return [0.0] * 4

    monkeypatch.setattr(g, "embed_text", fake_embed)


# --- 1. parsing ----------------------------------------------------------------


def test_parse_clean_json():
    out = g.parse_extraction(
        '{"entities": [{"type": "customer", "name": "Sarah", "fact": "Has a $680 quote"}],'
        ' "relations": [{"from": "Sarah", "to": "brake job", "relation": "requested"}]}'
    )
    assert out["entities"] == [
        {"type": "customer", "name": "Sarah", "fact": "Has a $680 quote"}
    ]
    assert out["relations"][0]["relation"] == "requested"


def test_parse_fenced_json_and_bad_type():
    out = g.parse_extraction(
        '```json\n{"entities": [{"type": "alien", "name": "X", "fact": "f"}], "relations": []}\n```'
    )
    assert out["entities"][0]["type"] == "other"


def test_parse_garbage_returns_empty():
    assert g.parse_extraction("not json at all") == {"entities": [], "relations": []}
    assert g.parse_extraction("") == {"entities": [], "relations": []}


def test_parse_skips_incomplete_entities():
    out = g.parse_extraction('{"entities": [{"type": "customer", "name": "", "fact": "f"}]}')
    assert out["entities"] == []


def test_normalize_name_collapses_case_and_spaces():
    assert g.normalize_name("  Sarah   CHEN ") == "sarah chen"


# --- 2. accumulation -------------------------------------------------------------


@pytest.mark.asyncio
async def test_short_turn_is_skipped(fake_db):
    out = await g.accumulate_from_turn(object(), "t1", "ok", None, "thread:x")
    assert out["skipped"] == "short_turn"
    assert fake_db.get("os_graph_nodes").rows == []


@pytest.mark.asyncio
async def test_turn_creates_nodes_edges_and_semantic_writethrough(
    fake_db, monkeypatch
):
    async def fake_extract(_b, _u, _a):
        return {
            "entities": [
                {"type": "customer", "name": "Sarah Chen", "fact": "Has a $680 brake quote"},
                {"type": "job", "name": "brake job", "fact": "Quoted at $680"},
            ],
            "relations": [
                {"from": "Sarah Chen", "to": "brake job", "relation": "requested"},
                {"from": "Sarah Chen", "to": "ghost", "relation": "knows"},  # unmatched
            ],
        }

    monkeypatch.setattr(g, "extract_turn_knowledge", fake_extract)
    written = []

    async def fake_write_memory(_db, client_id, content, **kw):
        written.append((client_id, content))
        return {}

    monkeypatch.setattr(g.os_memory, "write_memory", fake_write_memory)

    out = await g.accumulate_from_turn(
        object(), "t1", "Sarah Chen called about her brake quote", "Draft ready", "thread:x"
    )
    assert out == {"nodes": 2, "edges": 1}
    nodes = fake_db.get("os_graph_nodes").rows
    assert {n["normalized_name"] for n in nodes} == {"sarah chen", "brake job"}
    edges = fake_db.get("os_graph_edges").rows
    assert len(edges) == 1 and edges[0]["relation"] == "requested"
    assert len(written) == 2  # each new fact reaches semantic memory


@pytest.mark.asyncio
async def test_repeat_fact_dedups_and_increments_mentions(fake_db, monkeypatch):
    async def fake_extract(_b, _u, _a):
        return {
            "entities": [
                {"type": "customer", "name": "Sarah Chen", "fact": "Has a $680 brake quote"}
            ],
            "relations": [],
        }

    monkeypatch.setattr(g, "extract_turn_knowledge", fake_extract)
    written = []

    async def fake_write_memory(_db, client_id, content, **kw):
        written.append(content)
        return {}

    monkeypatch.setattr(g.os_memory, "write_memory", fake_write_memory)

    ask = "Sarah Chen called about her brake quote again today"
    await g.accumulate_from_turn(object(), "t1", ask, None, "thread:x")
    await g.accumulate_from_turn(object(), "t1", ask, None, "thread:y")

    nodes = fake_db.get("os_graph_nodes").rows
    assert len(nodes) == 1
    assert nodes[0]["mention_count"] == 2
    assert len(nodes[0]["facts"]) == 1  # same fact stored once
    assert len(written) == 1  # semantic write-through only on NEW facts


# --- 3. retrieval shaping ---------------------------------------------------------


def test_node_to_kb_entry_shape():
    entry = g.node_to_kb_entry(
        {"entity_type": "customer", "name": "Sarah", "summary": "Has a quote"}
    )
    assert entry == {"topic": "customer: Sarah", "answer": "Has a quote"}


@pytest.mark.asyncio
async def test_graph_kb_entries_merges_nodes_and_semantic_hits(fake_db, monkeypatch):
    fake_db.get("os_graph_nodes").rows.append(
        {
            "id": "n1",
            "entity_type": "preference",
            "name": "Sunday hours",
            "summary": "Closed on Sundays",
            "mention_count": 3,
            "last_seen_at": "2026-06-09",
        }
    )

    async def fake_search(_db, _cid, _q, match_count=6):
        return [
            {"kind": "fact", "content": "Sarah has a $680 quote"},
            {"kind": "fact", "content": "Closed on Sundays"},  # dup of node summary
        ]

    monkeypatch.setattr(g.os_memory, "search_memory", fake_search)
    entries = await g.graph_kb_entries(object(), "t1", "when are we open?")
    topics = [e["topic"] for e in entries]
    assert "preference: Sunday hours" in topics
    assert {"topic": "memory: fact", "answer": "Sarah has a $680 quote"} in entries
    # node summary not duplicated by the semantic hit
    assert sum(1 for e in entries if e["answer"] == "Closed on Sundays") == 1


@pytest.mark.asyncio
async def test_graph_kb_entries_survives_total_failure(monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("db down")

    monkeypatch.setattr(g, "tenant_table", boom)

    async def boom_search(*_a, **_k):
        raise RuntimeError("search down")

    monkeypatch.setattr(g.os_memory, "search_memory", boom_search)
    assert await g.graph_kb_entries(object(), "t1", "anything") == []
