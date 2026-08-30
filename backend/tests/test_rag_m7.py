"""Milestone 7 RAG: flag default, tenant scope, persist skip, fail-open attach."""

import os
import unittest

from backend.services.business_retrieval import (
    CorpusChunk,
    attach_rag_knowledge,
    retrieve_business_context,
)
from backend.services.rag_flags import rag_enabled
from backend.services.tenant_kb_index import documents_to_chunks, replace_chunks_for_tenant


class RagM7Tests(unittest.TestCase):
    def test_rag_enabled_defaults_off(self):
        os.environ.pop("RAG_ENABLED", None)
        self.assertFalse(rag_enabled())
        os.environ["RAG_ENABLED"] = "0"
        self.assertFalse(rag_enabled())
        os.environ["RAG_ENABLED"] = "false"
        self.assertFalse(rag_enabled())

    def test_documents_to_chunks_uses_client_id_not_tenant_id(self):
        chunks = documents_to_chunks(
            "client-a",
            [
                {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "filename": "Prices.md",
                    "content_md": "Oil changes are $79.99.",
                    "source": "upload",
                    "status": "active",
                }
            ],
        )
        self.assertTrue(chunks)
        self.assertTrue(all(c.account_id == "client-a" for c in chunks))

    def test_replace_chunks_skips_non_uuid_document_ids(self):
        class _Sink:
            def __init__(self):
                self.deleted = []
                self.inserted = []
                self.table_name = None

            def table(self, name):
                self.table_name = name
                return self

            def delete(self):
                return self

            def eq(self, col, value):
                self.deleted.append((col, value))
                return self

            def insert(self, rows):
                self.inserted.extend(rows)
                return self

            def execute(self):
                return self

        db = _Sink()
        n = replace_chunks_for_tenant(
            db,
            "client-a",
            [
                CorpusChunk(
                    "eval-doc#0",
                    "eval-doc",
                    "client-a",
                    "Prices",
                    "oil",
                    "Oil is $79.99.",
                    "prices",
                    "Prices §oil",
                )
            ],
        )
        self.assertEqual(n, 0)
        self.assertEqual(db.inserted, [])
        self.assertEqual(db.deleted, [("client_id", "client-a")])
        self.assertEqual(db.table_name, "tenant_kb_chunks")

    def test_retrieve_never_returns_other_tenant(self):
        a = CorpusChunk(
            "a#1", "a", "tenant-a", "P", "oil", "Oil is $79.99.", "prices", "P §oil"
        )
        b = CorpusChunk(
            "b#1", "b", "tenant-b", "P", "oil", "Oil is $149.00.", "prices", "P §oil"
        )
        r = retrieve_business_context("tenant-a", "How much is an oil change?", [a, b])
        self.assertTrue(all(e.account_id == "tenant-a" for e in r.evidence))
        self.assertFalse(any(e.chunk_id == "b#1" for e in r.evidence))

    def test_attach_rag_fail_open_returns_original_context(self):
        os.environ["RAG_ENABLED"] = "1"
        original = {"kb": [{"topic": "keep", "answer": "me"}], "businessProfile": {}}

        class _Boom:
            def __iter__(self):
                raise RuntimeError("retrieval exploded")

        out = attach_rag_knowledge(original, "client-a", "oil change?", _Boom())
        self.assertIs(out, original)
        self.assertEqual(out["kb"], [{"topic": "keep", "answer": "me"}])
        os.environ.pop("RAG_ENABLED", None)

    def test_attach_rag_off_is_noop(self):
        os.environ.pop("RAG_ENABLED", None)
        ctx = {"kb": []}
        self.assertIs(attach_rag_knowledge(ctx, "client-a", "oil?", []), ctx)


if __name__ == "__main__":
    unittest.main()
