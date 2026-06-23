# Audit — KB Embeddings Pipeline Break (2026-06-23)

**Scope:** read-only diagnosis of the knowledge-base embeddings pipeline (per-tenant vertical-KB moat), reported broken since ~2026-04-30, suspected missing `VOYAGE_API_KEY`.

**Branch:** `claude/agent-nexlify-testing-28d597`

---

## Root cause (2-3 sentences)

`backend/services/embeddings.py` has **no fallback and no graceful degradation**: all three functions (`embed_text`, `embed_batch`, `embed_query`) call `resp.raise_for_status()` directly, so a missing/empty `settings.voyage_api_key` produces a `401` from Voyage (`Authorization: Bearer ` with empty token) which raises `httpx.HTTPStatusError`. Every **runtime** caller wraps this in try/except and degrades (stores a `null` vector), so the app keeps working — but the **cron KB-compile path** (`scripts/daily/kb-autopopulate.sh` → kb-compile skill) runs the embedding call in a bare Python snippet with **no exception handling**, so the missing key hard-crashes that step and `kb_articles.embedding` never gets populated. The design spec for this system (`docs/superpowers/specs/2026-04-04-llm-knowledge-base-design.md:118,134,321-322`) specified a **Voyage→OpenAI fallback**, which was dropped when `embeddings.py` shipped — so there is no resilience when Voyage is unavailable.

**The break is two compounding facts:** (1) owner-gated missing/invalid `VOYAGE_API_KEY` in the live env, and (2) a code gap — `embeddings.py` never implemented the specced fallback and raises hard instead of degrading.

---

## The break — exact file:line cites

### Primary break point
`backend/services/embeddings.py:34, 52, 70` — `resp.raise_for_status()` in `embed_text` / `embed_batch` / `embed_query`. With `settings.voyage_api_key == ""` (default, `backend/config.py:122`), the header is `Authorization: Bearer ` and Voyage returns 401 → raises. No retry, no fallback provider, no graceful return.

### Where the key is read
- `backend/config.py:122` — `voyage_api_key: str = ""` (pydantic-settings `BaseSettings`).
- `backend/config.py:150-154` — `model_config` loads `.env` + `.env.managed_agents`; `extra: "ignore"`. pydantic-settings is case-insensitive, so env var `VOYAGE_API_KEY` maps to `voyage_api_key`.
- `.env.example:54` — `VOYAGE_API_KEY=` (documented, empty in template).
- Used at `embeddings.py:27, 45, 63` as `settings.voyage_api_key`.

### Why it fails silently in some places, loudly in others

| Caller | File:line | On embed failure | Behavior |
|---|---|---|---|
| OS memory write | `backend/services/os_memory.py:42-47` | try/except → `logger.warning`, stores `embedding=None` | **Silent skip** (degrades) |
| OS KB sync (tenant moat) | `backend/services/os_sync/kb.py:152-162` | try/except → warning, fills `[None]*len(batch)` | **Silent skip** (degrades) |
| OS sync leads/appts/convos/gcal | `os_sync/{leads,appointments,conversations,google_calendar}.py` | each wrapped | **Silent skip** |
| OS graph memory | `backend/services/os_graph_memory.py:180,200` | caller-wrapped | **Silent skip** |
| **Cron KB compile** | kb-compile skill Step 4 (`.claude/skills/kb-compile/SKILL.md:104-115`), invoked by `scripts/daily/kb-autopopulate.sh:110-113` | `asyncio.run(embed_text(text))` with **no try/except** | **HARD CRASH** — embedding step dies, `kb_articles.embedding` left empty |

The cron wrapper at `kb-autopopulate.sh:113` swallows the whole compile step with `|| log_line ... "kb-compile step failed (non-fatal)"`, so the **run reports success while embeddings are never written** — matching the "broken since ~2026-04-30, silently" report.

### Model / dimension consistency — OK
- `embeddings.py:16-17` — `VOYAGE_MODEL = "voyage-3-lite"`, `EMBEDDING_DIM = 512`.
- `migrations/081-kb-articles-and-sources.sql:15` — `embedding vector(512)`.
- `migrations/121_os_memory_entries.sql`, `migrations/133_os_graph_memory.sql` — also `vector(512)` (per `docs/dev-knowledge/schema-log.md:1056,1101`).

512-dim is **internally consistent** across code + all tables. **Note the doc drift:** the design spec (`docs/superpowers/specs/2026-04-04-llm-knowledge-base-design.md:118`) says **1024 dimensions + OpenAI fallback** — neither shipped. Code/DB at 512 is the canonical truth; the spec is stale. Dimension is **not** the bug.

---

## What is code-fixable vs owner-gated

### Code-fixable (this repo)
1. **Graceful degradation in `embeddings.py`** — return `None`/empty and log instead of raising when the key is missing, so the cron compile step does not hard-crash. (Minimal patch below.)
2. **Wrap the cron compile embedding call** — the kb-compile skill snippet should catch embedding errors and continue the markdown compile (the skill body at `SKILL.md:99` even says "If Supabase MCP is unreachable, skip embedding but continue" — the same resilience should apply to a missing Voyage key, but the Python snippet at lines 104-115 has no guard).
3. **(Optional, larger) Restore the specced OpenAI fallback** — `text-embedding-3-small`. Deferred; out of scope for the minimal fix. Note it requires re-dimensioning (OpenAI small = 1536) or `dimensions=512` param, so it is not a drop-in.

### Owner-gated (cannot be done from this repo / requires Aidan)
1. **Set/verify `VOYAGE_API_KEY` in the live env (Railway backend service)** — the actual secret value. Env var name is `VOYAGE_API_KEY` (confirmed `.env.example:54`, spec `:321`). Without this, embeddings will be `null` even after the code fix (the moat retrieval still won't have vectors — the code fix only stops the crash and lets markdown compile proceed).
2. **Confirm the key is valid / not expired / has quota** on the Voyage AI account.
3. **Backfill** — after the key is set, re-run kb-compile with `--full` (and `os_sync` backfill) to populate `embedding` for articles written `null` since ~2026-04-30.

---

## Minimal patch (DO NOT APPLY — proposal)

### Patch 1 — graceful degradation in `backend/services/embeddings.py`

Add an early guard so a missing key returns `None` instead of raising, and let callers that expect a vector handle `None` (they already do — see table above). This makes the cron path safe even though the key is owner-gated.

```diff
--- a/backend/services/embeddings.py
+++ b/backend/services/embeddings.py
@@
 logger = logging.getLogger(__name__)

 VOYAGE_API_URL = "https://api.voyageai.com/v1/embeddings"
 VOYAGE_MODEL = "voyage-3-lite"
 EMBEDDING_DIM = 512
 MAX_EMBED_CHARS = 32000  # ~8K tokens, safe limit for embedding input


+def _voyage_key() -> str | None:
+    key = (settings.voyage_api_key or "").strip()
+    if not key:
+        logger.warning(
+            "embeddings: VOYAGE_API_KEY missing — skipping embedding (vector=None). "
+            "Set VOYAGE_API_KEY in the backend env to enable semantic search."
+        )
+        return None
+    return key
+
+
 async def embed_text(text: str) -> list[float]:
     """Embed a single text string. Returns 512-dim vector."""
+    key = _voyage_key()
+    if key is None:
+        raise EmbeddingUnavailable("VOYAGE_API_KEY not configured")
     truncated = text[:MAX_EMBED_CHARS]
     async with httpx.AsyncClient(timeout=30.0) as client:
         resp = await client.post(
             VOYAGE_API_URL,
-            headers={"Authorization": f"Bearer {settings.voyage_api_key}"},
+            headers={"Authorization": f"Bearer {key}"},
             json={
                 "model": VOYAGE_MODEL,
                 "input": [truncated],
                 "input_type": "document",
             },
         )
         resp.raise_for_status()
         data = resp.json()
         return [float(x) for x in data["data"][0]["embedding"]]
```

Add a typed exception at top of file so callers can distinguish "no key" from "API error":

```python
class EmbeddingUnavailable(RuntimeError):
    """Raised when embeddings cannot be produced (missing key / provider down)."""
```

Apply the same `key = _voyage_key()` guard + `EmbeddingUnavailable` raise to `embed_batch` (line 39) and `embed_query` (line 57).

**Why raise a typed error rather than return None:** every existing runtime caller already wraps `embed_*` in try/except and degrades to `null` vectors, so a typed exception preserves their behavior exactly while making the "missing key" case explicit and cheap (no wasted HTTP round-trip to get a 401). Returning `None` instead would change the return type and force edits at every call site — larger blast radius.

### Patch 2 — guard the cron compile snippet (`.claude/skills/kb-compile/SKILL.md:104-115`)

Wrap the embedding generation so a missing key logs `embedding_errors=N` and continues the markdown compile, consistent with the existing "If Supabase MCP is unreachable, skip embedding but continue" rule already in the skill (`SKILL.md:99`):

```python
import asyncio, sys
sys.path.insert(0, '.')
from backend.services.embeddings import embed_text, EmbeddingUnavailable

try:
    embedding = asyncio.run(embed_text(text))
    print(f"Embedding generated: {len(embedding)} dimensions")
except EmbeddingUnavailable as e:
    embedding = None
    print(f"embedding_errors=1 reason={e} — markdown compile continues, vector skipped")
except Exception as e:
    embedding = None
    print(f"embedding_errors=1 reason={e!r}")
```

This is the actual fix for the reported break: it stops the cron compile step from hard-crashing on the missing key, so wiki markdown still compiles and the run no longer silently no-ops the embedding write.

---

## Verification plan (for whoever applies the fix)

1. `python -c "from backend.services.embeddings import embed_text, EmbeddingUnavailable"` — import smoke.
2. Unset key locally, run `asyncio.run(embed_text("x"))` → expect `EmbeddingUnavailable`, not `HTTPStatusError`.
3. Set valid `VOYAGE_API_KEY`, run again → expect a 512-float list.
4. After owner sets key in Railway: re-run `/kb-compile --full`, then `SELECT count(*) FROM kb_articles WHERE embedding IS NULL;` → should trend to 0.

---

## Summary table

| Item | Status |
|---|---|
| Root cause | Missing/invalid `VOYAGE_API_KEY` **+** no graceful degradation/fallback in `embeddings.py` |
| Break file:line | `backend/services/embeddings.py:34,52,70` (`raise_for_status` with empty key); cron path `kb-autopopulate.sh:110-113` + kb-compile skill `SKILL.md:104-115` (no try/except) |
| Dimension/model | Consistent (512 / voyage-3-lite, matches `migrations/081:15`). Not the bug. Spec says 1024+OpenAI fallback — stale doc drift. |
| Code-fixable | Graceful degradation in `embeddings.py`; wrap cron compile snippet; (optional) restore OpenAI fallback |
| Owner-gated | Set/verify `VOYAGE_API_KEY` secret in Railway backend env; confirm valid + has quota; backfill null vectors |
