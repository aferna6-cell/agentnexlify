# Milestone 7 kickoff plan — Business Knowledge / RAG

**Status:** PLAN ONLY — do not implement until Milestone 6 is merged to `main`.  
**Prerequisite:** M6 action eval harness + safety gate on `main`; optional staging Gmail proof.

---

## North-star outcome

Each tenant's Agent OS can answer and act using **grounded, approved business knowledge** — services, pricing, policies, SOPs, FAQs, documents — with a **retrieval evaluation harness** that proves correctness before production trust.

## In scope (M7)

| Workstream | Deliverable |
|------------|-------------|
| **A — Knowledge model** | Canonical tenant KB schema: services, pricing, policies, SOPs, FAQs, document refs; RLS + `client_id` scoping |
| **B — Ingestion** | Approved upload/sync paths (dashboard + API); no arbitrary web crawl in v1 |
| **C — Retrieval** | Hybrid retrieval (existing `kb_hybrid_retrieval.py` patterns) exposed to Agent OS orchestrator/departments at decision time |
| **D — Grounding contract** | Citations required in answers; refuse when retrieval confidence below threshold |
| **E — RAG eval harness** | Frozen tenant-scoped golden sets (like `lead_qualifier_golden.json`); metrics: answer faithfulness, citation accuracy, refusal rate, unsafe hallucination count |
| **F — Integration** | Wire retrieval into department runs without bypassing action executor / approval for mutations |

## Explicitly out of scope (M7)

- Calendar, CRM, invoicing integrations
- Computer use / browser automation
- Multi-step autonomous planning loops
- Changing `SEND_EMAIL_ENABLED` default
- Replacing the M6 action benchmark or routing decision

## Dependencies on M6

- Action eval harness (`agent-service/evals/`) — regression gate for any RAG-influenced behavior change
- Semantic intent/subject axes — retrieval queries should use same `AskIntent` seam
- Safety detector — extend with "must_not_hallucinate_policy" / "must_cite_source" labels

## Proposed phases

### Phase 1 — Schema + eval dataset (vertical slice)

1. Migration: `tenant_knowledge_chunks` or extend existing KB tables with eval-friendly metadata
2. Author 50–100 frozen RAG eval cases per reference tenant (services, pricing, policy FAQs)
3. Harness: `agent-service/evals/run-rag-eval.ts` (mirror action-eval structure)

### Phase 2 — Retrieval path

1. `retrieveBusinessContext(accountId, ask, intent)` → ranked chunks + scores
2. Inject into department `SharedContext` behind feature flag `RAG_ENABLED` (default OFF)
3. Department prompts: cite chunk ids; orchestrator declines when no chunks above threshold

### Phase 3 — Dashboard + ingestion

1. Owner UI to manage KB entries (may leverage existing `knowledge-base/` wiki patterns per tenant)
2. Ingestion API with approval workflow for new documents

### Phase 4 — Bakeoff + freeze

1. Compare: no-RAG baseline vs BM25 vs hybrid vs (optional) embedding rerank on **held-out eval set**
2. Select winner on **downstream action + faithfulness**, not retrieval MRR alone
3. Run frozen RAG benchmark once after selection

## Success metrics (draft)

| Metric | Target (initial) |
|--------|------------------|
| Faithfulness (eval) | ≥90% on frozen set |
| Citation accuracy | ≥85% |
| Unsafe hallucination | **0** on safety-labelled cases |
| Action benchmark regression | No increase in unsafe actions; behavior acc within 2 pp of M6 baseline |

## War room items to resolve before build

1. **KB source of truth:** `knowledge-base/wiki/` compile pipeline vs per-tenant Supabase chunks vs both?
2. **Widget KB vs Agent OS KB:** shared retrieval service or separate indexes?
3. **When to retrieve:** orchestrator-only vs per-department vs both?
4. **Embedding provider:** reuse existing pgvector migrations vs external API cost cap

## Verification commands (target state)

```bash
cd agent-service && npm run eval:rag          # frozen RAG benchmark
cd agent-service && npm run eval:actions:gate # M6 safety regression
npm run check:full
```

---

*Prepared 2026-08-30. Implementation blocked on M6 merge.*
