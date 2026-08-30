"""Milestone 7 RAG: flag default, tenant scope, persist skip, fail-open attach, abstention contract."""

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

    def test_replace_chunks_clears_orphans_on_reindex(self):
        """Soft-deleted docs are dropped by compile; replace deletes all then inserts active."""

        class _Sink:
            def __init__(self):
                self.ops = []

            def table(self, name):
                self.ops.append(("table", name))
                return self

            def delete(self):
                self.ops.append(("delete",))
                return self

            def eq(self, col, value):
                self.ops.append(("eq", col, value))
                return self

            def insert(self, rows):
                self.ops.append(("insert", len(rows), rows[0]["document_id"]))
                return self

            def execute(self):
                self.ops.append(("execute",))
                return self

        db = _Sink()
        doc_id = "22222222-2222-2222-2222-222222222222"
        n = replace_chunks_for_tenant(
            db,
            "client-a",
            [
                CorpusChunk(
                    f"{doc_id}#0",
                    doc_id,
                    "client-a",
                    "Prices",
                    "oil",
                    "Oil is $79.99.",
                    "prices",
                    "Prices §oil",
                )
            ],
        )
        self.assertEqual(n, 1)
        self.assertIn(("delete",), db.ops)
        self.assertIn(("eq", "client_id", "client-a"), db.ops)
        self.assertTrue(any(op[0] == "insert" for op in db.ops))

    def test_inactive_documents_are_not_chunked(self):
        chunks = documents_to_chunks(
            "client-a",
            [
                {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "filename": "Gone.md",
                    "content_md": "Secret $1.",
                    "source": "upload",
                    "status": "deleted",
                }
            ],
        )
        self.assertEqual(chunks, [])

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

    def test_attach_rag_fail_open_marks_error_not_abstain(self):
        os.environ["RAG_ENABLED"] = "1"
        original = {"kb": [{"topic": "keep", "answer": "me"}], "businessProfile": {}}

        class _Boom:
            def __iter__(self):
                raise RuntimeError("retrieval exploded")

        out = attach_rag_knowledge(original, "client-a", "oil change?", _Boom())
        self.assertEqual(out["ragStatus"], "error")
        self.assertEqual(out["ragAbstainReason"], "infrastructure_error")
        self.assertEqual(out["ragEvidence"], [])
        self.assertEqual(out["kb"], [{"topic": "keep", "answer": "me"}])
        os.environ.pop("RAG_ENABLED", None)

    def test_attach_rag_off_is_noop(self):
        os.environ.pop("RAG_ENABLED", None)
        ctx = {"kb": []}
        self.assertIs(attach_rag_knowledge(ctx, "client-a", "oil?", []), ctx)

    def test_attach_abstain_does_not_inject_kb(self):
        os.environ["RAG_ENABLED"] = "1"
        price = CorpusChunk(
            "a#1", "a", "client-a", "Prices", "oil", "Oil is $79.99.", "prices", "P §oil"
        )
        ctx = {"kb": [{"topic": "hours", "answer": "Open Tue–Sat."}]}
        out = attach_rag_knowledge(ctx, "client-a", "What is our Bitcoin wallet?", [price])
        self.assertEqual(out["ragStatus"], "abstain")
        self.assertTrue(out["ragAbstainReason"])
        self.assertEqual(out["ragEvidence"], [])
        self.assertEqual(out["kb"], [{"topic": "hours", "answer": "Open Tue–Sat."}])
        os.environ.pop("RAG_ENABLED", None)

    def test_attach_ok_injects_trusted_evidence(self):
        os.environ["RAG_ENABLED"] = "1"
        corpus = [
            CorpusChunk(
                "a#1",
                "a",
                "client-a",
                "Prices",
                "oil",
                "Oil changes are $79.99 including filter.",
                "prices",
                "P §oil",
            ),
            CorpusChunk(
                "a#2",
                "a",
                "client-a",
                "Hours",
                "open",
                "We are open Tuesday–Saturday 8am–5pm.",
                "faqs",
                "Hours §open",
            ),
            CorpusChunk(
                "a#3",
                "a",
                "client-a",
                "Warranty",
                "parts",
                "Parts we install carry a 12-month warranty.",
                "policies",
                "Warranty §parts",
            ),
        ]
        ctx = {"kb": []}
        out = attach_rag_knowledge(ctx, "client-a", "How much is an oil change?", corpus)
        self.assertEqual(out["ragStatus"], "ok")
        self.assertIsNone(out["ragAbstainReason"])
        self.assertEqual(out["ragEvidence"][0]["chunkId"], "a#1")
        self.assertTrue(any(e["topic"].startswith("rag:") for e in out["kb"]))
        os.environ.pop("RAG_ENABLED", None)

    def test_attach_no_corpus_abstains_explicitly(self):
        os.environ["RAG_ENABLED"] = "1"
        out = attach_rag_knowledge({"kb": []}, "client-a", "oil?", [])
        self.assertEqual(out["ragStatus"], "abstain")
        self.assertEqual(out["ragAbstainReason"], "no_approved_knowledge")
        self.assertEqual(out["ragEvidence"], [])
        os.environ.pop("RAG_ENABLED", None)


if __name__ == "__main__":
    unittest.main()
