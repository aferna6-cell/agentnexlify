# War room — Milestone 7 RAG architecture

**Date:** 2026-08-30  
**Status:** Accepted for implementation  
**Chief of Staff:** consolidated from specialist briefs below.

## Phase 0 findings (audited, not assumed)

Three knowledge systems exist today:

| System | Scope | Retrieval |
|--------|-------|-----------|
| `tenant_kb_documents` → `widget_configs.knowledge_base` | Tenant | Prompt injection (no vectors) |
| `kb_articles` global wiki | Platform | Voyage 512d + FTS + optional hybrid/rerank |
| `os_memory_entries` | Tenant (`client_id`) | Voyage 512d `match_os_memory` |

**Canonical tenant source of truth:** `tenant_kb_documents` (migration 165, `client_id`).  
**Global wiki is not tenant business knowledge.** Do not retrieve `kb_articles` for owner SOP/pricing questions.

pgvector exists (Voyage `voyage-3-lite`, 512d) on `kb_articles`, `os_memory_entries`, `os_graph_nodes`. **No tenant-document chunk table.**

Production-grade: `embeddings.py`, `tenant_kb.compile_tenant_kb`, `match_os_memory` pattern.  
Experimental / wrong corpus: `kb_hybrid_retrieval.py` (global wiki only — do not call from Agent OS).

---

## Specialist briefs

### RAG Architecture Agent

**Recommend:** extend, do not fork.

- Keep `tenant_kb_documents` as approved source store.
- Keep compiled blob as widget backward-compat cache.
- Add `tenant_kb_chunks` + `match_tenant_kb_chunks(p_client_id, …)` for authoritative retrieval.
- Shared capability: `retrieveBusinessContext({ accountId, ask, intent })`.
- Retrieve at **context assembly** (FastAPI `os_thread_runner` + engine `runOrchestration`), not once per department.

### Retrieval / ML Agent

**Recommend:** lexical baseline first; dense only if Voyage is available.

- No true BM25 in production today — FTS is `ts_rank_cd`.
- Bakeoff must include in-process BM25 (eval) + optional Voyage dense.
- Do not call `kb_hybrid_retrieval` from Agent OS (wrong index, no `client_id`).
- Winner chosen on **faithfulness + refusal + zero leaks**, not MRR alone.

### Data / Ingestion Agent

**Recommend:** index on compile, invalidate on replace.

- After `compile_tenant_kb`, chunk active documents and upsert chunks.
- Replace document → delete old chunks by `document_id`, write new.
- Metadata: `client_id`, source, title, section, effective_date, version, status, citation fields.
- No web crawl in v1.

### Evaluation Agent

**Recommend:** dataset before model.

- Frozen labels after selection only.
- Two tenants with contradictory prices for isolation cases.
- Safety: prompt-injection docs, fabricated-citation cases, action-sensitive policy.

### Security / Tenant Isolation Reviewer

**Non-negotiable:**

- `client_id` on chunks (not `tenant_id`) — same family as `tenant_kb_documents`.
- RLS deny-public + service-role RPC with `p_client_id` required.
- Tests must prove Tenant A query never returns Tenant B chunk IDs.
- Retrieved text is **data**, never system instructions.

### Agent OS Integration Reviewer

**Non-negotiable:**

- RAG changes knowledge, not authorization.
- Action Executor / policy / approval / idempotency untouched.
- `RAG_ENABLED` default OFF (same pattern as `SEND_EMAIL_ENABLED`).
- M6 `eval:actions:gate` must stay 0 unsafe with RAG ON and OFF.

---

## Locked decisions

1. **SoT:** `tenant_kb_documents` + `tenant_kb_chunks`. Global wiki stays platform-only.
2. **Reuse:** Voyage 512d when present; lexical BM25 always available offline.
3. **Widget vs OS:** shared retrieval module; widget prompt-injection unchanged in M7 v1.
4. **Retrieval point:** context assembly (orchestrator entry), one call per turn.
5. **Stale policy:** `effective_date` + `status=superseded` excluded from default retrieve.
6. **Citations:** only IDs from the retrieved set; fabricated IDs fail the eval.
7. **Prompt injection:** document body never granted policy authority.
8. **Flag:** `RAG_ENABLED` default OFF. No production enablement in this milestone.

## Disagreements recorded

- Historical `docs/ml-router-benchmark.md` hybrid-router rec is **unrelated** and remains non-policy (see M6 decision).
- Hybrid wiki retrieval (`widget_kb_hybrid_enabled`) is **not** the Agent OS tenant RAG path.
