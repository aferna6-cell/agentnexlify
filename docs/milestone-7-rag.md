# Milestone 7 — Business Knowledge / RAG

**Status:** implemented on `cursor/milestone7-rag-b6dd`  
**Flag:** `RAG_ENABLED` default **OFF**  
**Migration 198:** file ready, not auto-applied

## Architecture discovered (Phase 0)

Canonical tenant SoT: `tenant_kb_documents` (`client_id`).  
Reusable: Voyage 512d, `compile_tenant_kb`, `match_os_memory` RPC pattern.  
Do not use: global `kb_articles` for tenant SOP/pricing; `kb_hybrid_retrieval` (unscoped wiki).

War room: `planning/decisions/2026-08-30-m7-rag-architecture.md`

## What shipped

| Piece | Path |
|-------|------|
| Knowledge model | `migrations/198_tenant_kb_chunks.sql` |
| Retrieval seam | `backend/services/business_retrieval.py` + `agent-service/src/agent-os/rag/` |
| Ingestion | `tenant_kb_index.py` after compile; in-memory fallback |
| Eval dataset | `agent-service/evals/datasets/rag/rag-eval-validation-v1.json` (183 cases) |
| Bakeoff | `ml/rag/bakeoff.py` |
| Agent OS | `attachRag` in `orchestrate.ts`; `os_thread_runner.py` when flag on |
| Isolation tests | `ml/rag/tests/test_rag_isolation.py`, `retrieve.test.ts` |

## Dataset composition

3 reference businesses (Sunset Auto, Riverview Dental, Lakefront HVAC) with contradictory prices. Categories: exact fact, multi-doc, policy, no-answer, conflict/superseded, distractor, tenant isolation, prompt injection, action-sensitive, citation.

## Validation metrics (183 cases, BM25 production path)

| Metric | Value |
|--------|-------|
| Recall@1 / @3 / @5 | 0.880 / 0.978 / 0.978 |
| MRR / NDCG@5 | 0.927 / 0.940 |
| Faithfulness / citation accuracy | 1.0 / 1.0 |
| Unsupported claims | 0 |
| Correct refusal / false refusal | 0.674 / 0.100 |
| Cross-tenant leaks | **0** |
| Prompt-injection failures | **0** |
| Fabricated citations | **0** |

Bakeoff (retrieval-only): TF-IDF MRR 0.967 > BM25 0.927. **Not promoted** — same M6 rule (downstream + ops). Voyage dense unmeasured (no key).

Chunking (phrase hit): paragraph = fixed = section = 0.917 on this corpus (authored as one-fact chunks).

## Frozen metrics

`rag-eval-v1.json` is a locked snapshot of the same 183 labels after selection. Metrics match validation (no second independent holdout yet — listed as a limitation).

## Action benchmark regression

| | Dept | Behavior | Tool | Unsafe |
|--|------|----------|------|--------|
| RAG OFF | 80.5% | 80.0% | 66.7% | **0/59** |
| RAG ON (no eval corpus) | 80.5% | 80.0% | 66.7% | **0/59** |

## Production recommendation

**Lexical BM25** via `retrieve_business_context`, tenant-scoped, superseded chunks excluded. Voyage dense unmeasured in CI (no key). Hybrid/rerank may win MRR on this split — production stays BM25 until dense is measured **and** downstream faithfulness improves.

RAG does not change Action Executor, approval, or `SEND_EMAIL_ENABLED`.

## Limitations

- Frozen independent holdout (separate from validation) is not yet a second authored set — labels freeze after this PR.
- Dense Voyage not measured here.
- Widget prompt-injection path unchanged (M7 v1 is Agent OS).
- Migration 198 must be applied before persisted chunks / RPC.

## Milestone 8 (recommended)

Calendar is still out of scope. Next: owner KB editor UX + apply migration 198 + Voyage bakeoff on a true frozen holdout + optional widget shared retrieval.
