"""KB chunk size and one-tenant reindex.

Tiny heading bodies were stored as their own chunks (about 30 characters, no
embeddings). Reindex must pack them and must not delete existing rows when
Voyage fails.
"""

import asyncio
from types import SimpleNamespace

import pytest

from backend.services.business_retrieval import CorpusChunk
from backend.services.embeddings import EmbeddingUnavailable
from backend.services.tenant_kb_index import (
    KbIndexPersistError,
    embed_chunk_texts,
    index_after_compile,
    pack_text,
    reindex_tenant,
    replace_chunks_for_tenant,
)
from backend.tests.conftest import _make_auth_token

TENANT = "00000000-0000-0000-0000-000000000001"


def test_pack_text_keeps_a_short_document_intact():
    assert pack_text("Oil changes are $79.99.") == ["Oil changes are $79.99."]
    assert pack_text("  \n  ") == []


def test_pack_text_splits_a_long_paragraph_with_overlap():
    block = "brake " * 400
    chunks = pack_text(block.strip())
    assert len(chunks) >= 2
    assert all(len(chunk) <= 1000 for chunk in chunks)
    assert chunks[0][-40:] in chunks[1]


def test_pack_text_flushes_a_short_paragraph_before_a_long_one():
    chunks = pack_text("Oil changes.\n" + ("tire rotation " * 120))
    assert chunks[0].startswith("Oil changes.")
    assert all(len(chunk) <= 1000 for chunk in chunks)


def test_pack_text_drops_overlap_when_the_next_paragraph_fills_the_window():
    chunks = pack_text(("A" * 100) + "\n" + ("B" * 1000))
    assert chunks[0] == "A" * 100
    assert chunks[-1] == "B" * 1000


def test_pack_text_merges_a_short_whitespace_tail():
    chunks = pack_text(("B" * 100) + (" " * 900) + ("C" * 200))
    assert len(chunks) == 1
    assert chunks[0].startswith("B" * 100)
    assert "C" * 200 in chunks[0]


def test_pack_text_keeps_overlap_inside_the_max():
    first = "A" * 900
    second = "B" * 200
    chunks = pack_text(f"{first}\n{second}")
    assert all(len(chunk) <= 1000 for chunk in chunks)
    assert chunks[0] == first
    assert chunks[1].endswith(second)
    assert "A" in chunks[1]


def test_pack_text_merges_tiny_lines_into_500_to_1000_char_windows():
    lines = [f"Service {i}: oil, brakes, and tires for local drivers." for i in range(80)]
    chunks = pack_text("\n".join(lines))
    assert len(chunks) < 15
    assert all(len(chunk) <= 1000 for chunk in chunks)
    assert all(len(chunk) >= 500 for chunk in chunks[:-1])
    assert chunks[0][-60:] in chunks[1]


def test_reindex_does_not_delete_when_embeddings_fail(monkeypatch):
    class _DB:
        def __init__(self):
            self.deleted = False

        def table(self, name):
            return self

        def select(self, *args, **kwargs):
            return self

        def eq(self, *args, **kwargs):
            return self

        def delete(self):
            self.deleted = True
            return self

        def execute(self):
            return SimpleNamespace(data=[{
                "id": "11111111-1111-1111-1111-111111111111",
                "filename": "Services.md",
                "content_md": "We offer oil changes and brake jobs for local drivers.",
                "source": "upload",
                "status": "active",
            }])

    db = _DB()
    monkeypatch.setattr("backend.models.database.get_service_supabase", lambda: db)

    async def _boom(texts):
        raise EmbeddingUnavailable("VOYAGE_API_KEY not configured")

    monkeypatch.setattr(
        "backend.services.tenant_kb_index.embed_chunk_texts",
        _boom,
    )
    with pytest.raises(EmbeddingUnavailable):
        asyncio.run(reindex_tenant(TENANT))
    assert db.deleted is False


def test_reindex_writes_embeddings_for_one_tenant(monkeypatch):
    class _DB:
        def __init__(self):
            self.inserted = []
            self.client_filter = None

        def table(self, name):
            self.name = name
            return self

        def select(self, *args, **kwargs):
            return self

        def eq(self, col, value):
            if col == "client_id":
                self.client_filter = value
            return self

        def delete(self):
            return self

        def insert(self, rows):
            self.inserted.extend(rows)
            return self

        def execute(self):
            if self.name == "tenant_kb_documents":
                return SimpleNamespace(data=[{
                    "id": "22222222-2222-2222-2222-222222222222",
                    "filename": "Services.md",
                    "content_md": "We offer oil changes.\n" * 40,
                    "source": "upload",
                    "status": "active",
                }])
            return SimpleNamespace(data=[])

    db = _DB()
    monkeypatch.setattr("backend.models.database.get_service_supabase", lambda: db)

    async def _vecs(texts):
        return [[0.1] * 512 for _ in texts]

    monkeypatch.setattr("backend.services.tenant_kb_index.embed_chunk_texts", _vecs)
    summary = asyncio.run(reindex_tenant(TENANT))
    assert summary["client_id"] == TENANT
    assert summary["embedded"] == summary["chunks"] > 0
    assert db.client_filter == TENANT
    assert all(row["client_id"] == TENANT and len(row["embedding"]) == 512 for row in db.inserted)
    assert all(len(row["content"]) <= 1000 for row in db.inserted)


def test_embed_chunk_texts_batches_and_rejects_a_short_reply(monkeypatch):
    calls = []

    async def _ok(texts):
        calls.append(list(texts))
        return [[0.0] * 512 for _ in texts]

    monkeypatch.setattr("backend.services.embeddings.embed_batch", _ok)
    texts = [f"chunk {i}" for i in range(70)]
    vectors = asyncio.run(embed_chunk_texts(texts))
    assert len(vectors) == 70
    assert calls == [texts]
    assert asyncio.run(embed_chunk_texts([])) == []

    async def _short(texts):
        return []

    monkeypatch.setattr("backend.services.embeddings.embed_batch", _short)
    with pytest.raises(RuntimeError):
        asyncio.run(embed_chunk_texts(["hello"]))


def test_reindex_keeps_chunks_when_voyage_errors(monkeypatch):
    db = _Docs()
    monkeypatch.setattr("backend.models.database.get_service_supabase", lambda: db)

    async def _boom(texts):
        raise RuntimeError("voyage 500")

    monkeypatch.setattr("backend.services.tenant_kb_index.embed_chunk_texts", _boom)
    with pytest.raises(EmbeddingUnavailable):
        asyncio.run(reindex_tenant(TENANT))
    assert db.deleted is False


def test_compile_index_stores_embeddings_and_fail_opens(monkeypatch):
    db = _Docs()
    monkeypatch.setattr("backend.models.database.get_service_supabase", lambda: db)

    async def _vecs(texts):
        return [[0.2] * 512 for _ in texts]

    monkeypatch.setattr("backend.services.tenant_kb_index.embed_chunk_texts", _vecs)
    index_after_compile(TENANT)
    assert db.inserted and db.inserted[0]["embedding"][0] == 0.2

    db.inserted.clear()
    db.deleted = False

    async def _down(texts):
        raise EmbeddingUnavailable("VOYAGE_API_KEY not configured")

    monkeypatch.setattr("backend.services.tenant_kb_index.embed_chunk_texts", _down)
    index_after_compile(TENANT)
    assert db.inserted and "embedding" not in db.inserted[0]
    assert db.deleted is False


class _Docs:
    """Service client stub: one active document, then chunk writes."""

    def __init__(self):
        self.name = ""
        self.deleted = False
        self.inserted = []

    def table(self, name):
        self.name = name
        return self

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def delete(self):
        self.deleted = True
        return self

    def insert(self, rows):
        self.inserted.extend(rows)
        return self

    def execute(self):
        if self.name == "tenant_kb_documents":
            return SimpleNamespace(data=[{
                "id": "22222222-2222-2222-2222-222222222222",
                "filename": "Services.md",
                "content_md": "We offer oil changes and brake jobs for local drivers.",
                "source": "upload",
                "status": "active",
            }])
        return SimpleNamespace(data=[])


def test_reindex_rejects_a_non_uuid():
    with pytest.raises(ValueError):
        asyncio.run(reindex_tenant("not-a-tenant"))


def test_reindex_endpoint_is_tenant_scoped(client, monkeypatch):
    from backend.services.embeddings import EmbeddingUnavailable as Missing

    calls = []

    async def _ok(client_id):
        calls.append(client_id)
        return {"client_id": client_id, "chunks": 2, "embedded": 2, "with_embeddings": 2}

    monkeypatch.setattr("backend.services.tenant_kb_index.reindex_tenant", _ok)
    headers = {"Authorization": f"Bearer {_make_auth_token(TENANT)}"}
    other = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    forbidden = client.post(f"/api/v1/kb/{other}/reindex", headers=headers)
    assert forbidden.status_code == 403
    assert calls == []

    async def _missing(client_id):
        raise Missing("VOYAGE_API_KEY not configured")

    monkeypatch.setattr("backend.services.tenant_kb_index.reindex_tenant", _missing)
    unavailable = client.post(f"/api/v1/kb/{TENANT}/reindex", headers=headers)
    assert unavailable.status_code == 503

    async def _bad(client_id):
        raise ValueError("client_id must be a UUID")

    monkeypatch.setattr("backend.services.tenant_kb_index.reindex_tenant", _bad)
    refused = client.post(f"/api/v1/kb/{TENANT}/reindex", headers=headers)
    assert refused.status_code == 422


DOC = "22222222-2222-2222-2222-222222222222"
OLD = "33333333-3333-3333-3333-333333333333"


def _faq_chunk():
    return CorpusChunk(
        "faq-0",
        DOC,
        TENANT,
        "Services",
        "faq",
        "We offer oil changes and brake jobs.",
        "faq",
        "FAQ",
    )


class _ChunkTable:
    """Records insert vs delete. Insert can be told to fail."""

    def __init__(self, fail_insert=False):
        self.fail_insert = fail_insert
        self.mode = ""
        self.ops = []
        self.inserted = []
        self.deleted_ids = []
        self.updates = []
        self._pending = []

    def table(self, name):
        return self

    def select(self, *args, **kwargs):
        self.mode = "select"
        return self

    def eq(self, *args, **kwargs):
        return self

    def range(self, *args, **kwargs):
        return self

    def delete(self):
        self.mode = "delete"
        self.ops.append("delete")
        return self

    def in_(self, col, values):
        if col == "id":
            self.deleted_ids.extend(values)
        return self

    def update(self, values):
        self.mode = "update"
        self.updates.append(dict(values))
        return self

    def insert(self, rows):
        self.mode = "insert"
        self.ops.append("insert")
        self._pending = rows
        self.inserted.extend(rows)
        return self

    def execute(self):
        if self.mode == "insert":
            if self.fail_insert:
                raise RuntimeError("insert failed")
            return SimpleNamespace(data=[{"id": "new-id"}])
        if self.mode == "select":
            return SimpleNamespace(data=[{
                "id": OLD,
                "document_id": DOC,
                "chunk_index": 0,
            }])
        return SimpleNamespace(data=[])


def test_faq_chunk_id_is_stored_by_position_and_old_rows_survive_until_insert():
    db = _ChunkTable()
    written = replace_chunks_for_tenant(db, TENANT, [_faq_chunk()])
    assert written == 1
    assert db.inserted[0]["chunk_index"] != 0
    assert db.ops.index("insert") < db.ops.index("delete")
    assert db.deleted_ids == [OLD]
    assert db.updates == [{"chunk_index": 0}]


def test_insert_failure_does_not_delete_existing_chunks():
    db = _ChunkTable(fail_insert=True)
    with pytest.raises(KbIndexPersistError):
        replace_chunks_for_tenant(db, TENANT, [_faq_chunk()])
    assert "delete" not in db.ops
    assert db.inserted[0]["chunk_index"] != 0


def test_existing_chunk_pages_stop_when_the_client_cannot_page():
    class _Wide:
        def __init__(self):
            self.mode = ""
            self.selects = 0
            self.deleted = []

        def table(self, name):
            return self

        def select(self, *args, **kwargs):
            self.mode = "select"
            return self

        def eq(self, *args, **kwargs):
            return self

        def insert(self, rows):
            self.mode = "insert"
            return self

        def delete(self):
            self.mode = "delete"
            return self

        def in_(self, col, values):
            if col == "id":
                self.deleted.extend(values)
            return self

        def update(self, values):
            self.mode = "update"
            return self

        def execute(self):
            if self.mode == "select":
                self.selects += 1
                if self.selects == 1:
                    return SimpleNamespace(data=[
                        {"id": f"old-{i}", "document_id": DOC, "chunk_index": 1000 + i}
                        for i in range(1000)
                    ])
                return SimpleNamespace(data=[])
            return SimpleNamespace(data=[])

    db = _Wide()
    written = replace_chunks_for_tenant(db, TENANT, [_faq_chunk()])
    assert written == 1
    assert db.selects == 1
    assert len(db.deleted) == 1000


def test_reindex_script_exits_nonzero_when_persist_fails(monkeypatch):
    import importlib.util

    path = "scripts/reindex_tenant_kb.py"
    spec = importlib.util.spec_from_file_location("reindex_tenant_kb_script", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def _boom(client_id):
        raise KbIndexPersistError("existing chunks were kept")

    monkeypatch.setattr(module, "reindex_tenant", _boom)
    monkeypatch.setattr("sys.argv", ["reindex_tenant_kb.py", "--client-id", TENANT])
    assert module.main() == 1
