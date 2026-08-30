# Milestone 7 — Business Knowledge / RAG

**Status:** finalization complete on `cursor/milestone7-rag-b6dd`  
**Flag:** `RAG_ENABLED` default **OFF** — do not enable in production  
**Migration 198:** reviewed (FK cascade + lifecycle), **not applied** — use normal migration workflow

## Architecture

Canonical tenant SoT: `tenant_kb_documents` (`client_id`).  
Retrievable projection: `tenant_kb_chunks` with `document_id REFERENCES tenant_kb_documents(id) ON DELETE CASCADE`.  
Soft-delete / supersede: existing compile → `replace_chunks_for_tenant` (delete all tenant chunks, reinsert active only).  
War room: `planning/decisions/2026-08-30-m7-rag-architecture.md`

## SharedContext RAG contract

| Field | Meaning |
|-------|---------|
| `ragStatus` | `ok` \| `abstain` \| `error` \| (absent when flag off) |
| `ragAbstainReason` | `no_approved_knowledge` / `insufficient_evidence` / `low_overlap` / `untrusted_document` / `infrastructure_error` |
| `ragEvidence` | Authoritative evidence **only when `ragStatus === "ok"`** |

Abstention does **not** inject into `kb`. Infrastructure failure (`error`) is distinct from successful abstention. RAG never mutates tool policy, approval, or the Action Executor.

Sanitization/prefixing is defense-in-depth. The real boundary: retrieved documents are untrusted data — never system instructions, never authorization, never tool policy.

## What shipped

| Piece | Path |
|-------|------|
| Knowledge model | `migrations/198_tenant_kb_chunks.sql` (FK cascade) |
| Retrieval seam | `backend/services/business_retrieval.py` + `agent-service/src/agent-os/rag/` |
| Attach contract | `applyRagToContext` / `attach_rag_knowledge` |
| Validation set | `rag-eval-validation-v1.json` (183) |
| Independent holdout | `rag-eval-holdout-v1.json` / `rag-eval-v1.json` (162) |
| Leakage gate | `ml/rag/authoring/check_rag_holdout_leakage.py` |
| Calibration | `ml/rag/calibrate_abstention.py` → `rag-abstention-calibration-v1.json` |
| Downstream bakeoff | `ml/rag/downstream_bakeoff.py` |

## Operating point (validation-only)

Frozen `DEFAULT_MIN_SCORE = 1.0` after risk/coverage curve on validation.  
Holdout was **not** used for threshold, retriever, or chunking selection.

### Validation metrics (183 cases, BM25)

| Metric | Value |
|--------|-------|
| Recall@1 / MRR | 0.965 / 0.979 |
| Correct refusal | **1.0** |
| False refusal | **0.0** |
| Unsupported claims | **0** |
| Cross-tenant leaks | **0** |
| Prompt-injection failures | **0** |
| Answered coverage | 140/140 |

### Independent frozen holdout (162 cases, run once after freeze)

Composition: Harbor Pet Clinic, Pinecrest Legal, Metro Fitness, Cedar Roofing — exact facts, policy, multi-source, no-answer, conflict/superseded, distractors, cross-tenant + hard-pair traps, prompt-injection, action-sensitive, citation. Leakage check: exact / Jaccard≥0.8 / template_family / hard-pair — **PASS**.

| Metric | Value |
|--------|-------|
| Recall@1 / MRR | 0.902 / ~0.93 |
| Correct refusal | **1.0** |
| False refusal | **0.0** |
| Unsupported claims | **0** |
| Cross-tenant leaks | **0** |
| Prompt-injection failures | **0** |

## BM25 vs alternatives (downstream)

Under the same abstention contract on validation, BM25 and TF-IDF tied on grounded answer/refusal metrics. **BM25 remains production candidate** (M6 rule: downstream correctness > isolated model metric). Voyage dense: **unmeasured** (no API key) — does not block M7.

## Action benchmark regression

| | Dept | Behavior | Tool | Approval | Unsafe |
|--|------|----------|------|----------|--------|
| RAG OFF | 80.5% | 80.0% | 66.7% | 100% | **0/59** |
| RAG ON (no eval corpus on action set) | 80.5% | 80.0% | 66.7% | 100% | **0/59** |

No meaningful unexplained regression. Tenant isolation unchanged (AsyncLocalStorage + mixed-corpus RAG leaks = 0).

## Production recommendation

Lexical BM25 via `retrieve_business_context`, tenant-scoped, superseded excluded, abstention honored in Agent OS. `RAG_ENABLED` stays default OFF. Migration 198 apply only through normal workflow after this review.

## Milestone 8 (recommended)

Do not start until this branch merges. Next: owner KB editor UX + apply migration 198 + optional Voyage bakeoff + optional widget shared retrieval.
