"""Haiku-based KB chunk reranker — optional additive reordering (#F10).

Sits AFTER the existing vector/FTS retrieval in
`backend/routers/widget_chat_helpers.py::_query_kb_articles`. Given the
visitor's query plus up to N already-retrieved article snippets, asks Haiku
(`claude-haiku-4-5-20251001`, via the shared `call_claude_messages` runtime)
to return the article indices ordered by relevance, then the caller reorders
+ truncates to that order.

No task budget here (see `.claude/rules/task-budgets.md` — widget chat reply
path is interactive/user-facing and latency-sensitive; task budgets are for
long-running/cron loops, not this call). Kept to a low `max_tokens` + short
timeout instead, same reasoning as `backend/services/widget_guard.py`.

FAIL-OPEN by design (mirrors `widget_guard.py`): any LLM error, timeout, or
malformed response returns the ORIGINAL article list/order unchanged. A
broken reranker must never break KB grounding on the widget chat path.

Opt-in only — this module has no side effect unless `rerank_kb_articles()`
is called. The caller (`_query_kb_articles`) gates the call behind the
`widget_kb_rerank_enabled` setting (default off).
"""

import json
import logging
from typing import Any

from backend.services.llm_runtime import call_claude_messages

logger = logging.getLogger(__name__)

_RERANK_MODEL = "claude-haiku-4-5-20251001"
_RERANK_MAX_TOKENS = 150
_RERANK_TIMEOUT_SECONDS = 6.0
_SNIPPET_CHARS = 280

_SYSTEM_PROMPT = (
    "You are a relevance-ranking assistant for a knowledge-base search over "
    "a small business's chat widget. You are given a visitor query and a "
    "numbered list of candidate article snippets. Return ONLY the indices "
    "of the articles that are actually relevant to the query, ordered from "
    "MOST to LEAST relevant. Drop indices for articles that are not "
    "relevant at all.\n\n"
    "Respond with ONLY strict JSON, no markdown fences, no explanation, "
    "like this:\n"
    '{"ranked_indices": [2, 0, 3]}'
)


def _strip_json_fences(text: str) -> str:
    """Best-effort removal of ```json ... ``` or ``` ... ``` wrapping."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("```", 2)[1] if stripped.count("```") >= 2 else stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:]
    return stripped.strip()


def _build_snippet(article: dict[str, Any]) -> str:
    title = (article.get("title") or "").strip()
    summary = (article.get("summary") or "").strip()
    text = f"{title}: {summary}" if title else summary
    return text[:_SNIPPET_CHARS]


async def rerank_kb_articles(
    query: str,
    articles: list[dict[str, Any]],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Reorder *articles* by relevance to *query* using a Haiku classifier.

    Returns a NEW list — `articles` itself is never mutated.

    On success: articles the model judged relevant, reordered most-to-least
    relevant, truncated to `top_k`.

    On ANY failure (LLM error, timeout, unparseable/malformed response, no
    valid indices, fewer than 2 articles, empty query): returns `articles`
    unchanged — same order, same length. This is the pre-rerank behavior,
    so a reranker failure is invisible to the widget reply.
    """
    if not articles or len(articles) < 2:
        return articles
    if not query or not query.strip():
        return articles

    numbered = "\n".join(f"{i}. {_build_snippet(a)}" for i, a in enumerate(articles))
    user_content = f"Visitor query: {query.strip()}\n\nCandidate articles:\n{numbered}"

    try:
        result = await call_claude_messages(
            operation="kb_reranker.rerank",
            model=_RERANK_MODEL,
            max_tokens=_RERANK_MAX_TOKENS,
            temperature=0.0,
            timeout=_RERANK_TIMEOUT_SECONDS,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
    except Exception:
        logger.warning(
            "kb_reranker: rerank LLM call failed for query=%r — returning original order",
            query[:60],
            exc_info=True,
        )
        return articles

    raw = (result.text or "").strip()
    if not raw:
        logger.warning(
            "kb_reranker: empty rerank response for query=%r — returning original order",
            query[:60],
        )
        return articles

    try:
        parsed = json.loads(_strip_json_fences(raw))
    except (json.JSONDecodeError, ValueError):
        logger.warning(
            "kb_reranker: unparseable rerank response=%r — returning original order",
            raw[:200],
        )
        return articles

    if not isinstance(parsed, dict):
        logger.warning(
            "kb_reranker: non-dict rerank response=%r — returning original order",
            raw[:200],
        )
        return articles

    indices = parsed.get("ranked_indices")
    if not isinstance(indices, list) or not indices:
        logger.warning(
            "kb_reranker: missing/empty ranked_indices in response=%r — returning original order",
            raw[:200],
        )
        return articles

    reranked: list[dict[str, Any]] = []
    seen: set[int] = set()
    for idx in indices:
        if not isinstance(idx, int) or isinstance(idx, bool):
            continue
        if idx < 0 or idx >= len(articles) or idx in seen:
            continue
        reranked.append(articles[idx])
        seen.add(idx)
        if len(reranked) >= top_k:
            break

    if not reranked:
        logger.warning(
            "kb_reranker: no valid indices in response=%r — returning original order",
            raw[:200],
        )
        return articles

    return reranked
