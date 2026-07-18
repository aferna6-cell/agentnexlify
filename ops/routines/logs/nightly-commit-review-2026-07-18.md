# Nightly Commit Review — 2026-07-18

**Run time:** 2026-07-18 UTC  
**Commits reviewed:** 14  
**Issues fixed:** 0  
**Issues filed:** 0  
**Result:** CLEAN — no action required

---

## Commit Triage

### MEDIUM

| SHA | Title | Notes |
|-----|-------|-------|
| `180b19e` | Land #433: prompt caching, structured outputs, KB reranker+hybrid, Batch API (#471) | 19 files, 1855+ insertions. Large feature landing. No violations found. See analysis below. |

### LOW

| SHA | Title | Risk rationale |
|-----|-------|----------------|
| `b5e2fec` | subconscious: run 2026-07-17-pm | Docs/records only — subconscious state files |
| `e13d9e2` | docs: auto-log bug fix from 6391bd3 | Docs only |
| `6391bd3` | fix(digest): grant issues:write for digest jobs | CI workflow fix — `issues: write` permission added |
| `ab51b72` | docs: Instantly MCP setup guide | Docs only |
| `9020e80` | docs: auto-log bug fix from 26f7829 | Docs only |
| `26f7829` | fix(digest): loop-health scan pages when blind | Test + script fix. Adds defensive check when scan returns `pages` instead of row list. |
| `7009905` | subconscious: run 97 — record commit hash | Records only |
| `e9d5b7b` | docs: auto-log bug fix from f6ea32e | Docs only |
| `f6ea32e` | subconscious: run 2026-07-17 | Records only |
| `0ef040b` | docs: auto-log bug fix from a0a3457 | Docs only |
| `a0a3457` | fix(ci): sanitize rest_fetch error to prevent key leak | Security fix — re-raises as plain `RuntimeError` with `from None` to suppress urllib traceback that could expose `SUPABASE_SERVICE_KEY` in GitHub Actions logs. Good proactive fix. |
| `3080ffd` | fix(ci): log non-422 createLabel failures in digest jobs | CI diagnostics improvement only |
| `c8826e1` | ops: nightly-commit-review 2026-07-17 | Prior routine log commit |

---

## MEDIUM Commit — Detailed Analysis (`180b19e`)

**5 features shipped in one PR (#471). All opt-in + default-off + fail-open.**

### #F4 — Prompt caching (`llm_runtime.py`)
- `_build_cached_system()`: wraps plain string system in `cache_control: {type: ephemeral}` block
- `_merge_structured_output_config()`: merges `format: json_schema` into `output_config` without clobbering `effort`
- Beta header `extended-cache-ttl-2025-04-11` added only when `cache_ttl="1h"` — 5-min ephemeral needs none
- Existing callers: zero behavior change (default `cache_system=False`)
- Widget/voice routes opt-in at 5-min TTL

### #F9 — Structured Outputs (`llm_runtime.py` + `bot_health.py`)
- `response_schema` param threaded through `call_claude_messages`
- `response_schema=None` (default) → no change for all existing callers
- `bot_health` opts in with `_build_verdict_schema()`, JSON-repair fallback retained

### #F10 — KB Reranker (`backend/services/kb_reranker.py`)
- New file: 162 lines. Haiku-based reranker for KB retrieval
- Model: `claude-haiku-4-5-20251001` ✓ (valid model ID)
- 6-second timeout, 150 max_tokens — latency-conscious
- Fail-open: `<2 articles`, empty query, LLM error, unparseable response, no valid indices → returns original list
- Gated by `widget_kb_rerank_enabled` (default 0/off)

### #F12 — Hybrid KB Retrieval (`backend/services/kb_hybrid_retrieval.py`)
- New file: 91 lines. FTS pass alongside semantic rows, dedupe by `id`
- No new migration — uses existing `match_kb_articles_fts` RPC (migrations 155/163)
- Fail-open: RPC error returns `semantic_rows` unchanged
- Gated by `widget_kb_hybrid_enabled` (default 0/off)

### #F11 — Batch API Runtime (`backend/services/batch_runtime.py`)
- New file: 306 lines. Wraps Anthropic Message Batches (50% off for async)
- `submit_batch`, `poll_batch`, `get_batch_results` — all never raise (offline-safe)
- Strict rule documented: offline callers only, never from a user-waiting path
- `conversation_enrichment_job.py` gains batch variant for nightly enrichment

### Critical Invariant Checks

| Rule | Status |
|------|--------|
| `client_id` not `tenant_id` on leads/conversations | ✓ PASS — `conversation_enrichment_job.py` uses `client_id` |
| `status` not `lead_stage` | ✓ N/A — new code doesn't touch leads table |
| `areas_of_interest` not `service_interest` | ✓ N/A |
| No `from __future__ import annotations` | ✓ PASS — not present in any new/modified FastAPI file |
| Widget JS byte-identical | ✓ N/A — no widget JS changes |
| No secrets in code | ✓ PASS — `_safe_metadata()` in batch_runtime redacts sensitive keys |
| Schema changes via migration files only | ✓ N/A — no new migrations; hybrid retrieval uses existing RPC |

### Tests Shipped with PR
- `tests/test_kb_reranker.py` — 12 tests
- `tests/test_prompt_caching.py` — 10 tests
- `tests/test_structured_outputs.py` — 7 tests
- `backend/tests/test_batch_runtime.py` — 13 tests
- `backend/tests/test_conversation_enrichment.py` — existing + new enrichment-batch tests
- CI allowlist updated to include `test_batch_runtime.py`

**Assessment:** Well-engineered feature landing. All paths fail-open, all default-off. Schema discipline clean. No auth/payments/tenant isolation touched. No action required.

---

## Actions Taken

**LOW-risk bug fixes:** None warranted — no bugs found.  
**GitHub issues filed:** None warranted — no MEDIUM/HIGH issues found.

---

## Summary

14 commits reviewed. 13 LOW, 1 MEDIUM. The MEDIUM commit (feature landing #471) is well-structured with comprehensive tests, fail-open behavior, and no critical invariant violations. No issues require action.
