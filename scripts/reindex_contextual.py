#!/usr/bin/env python3
"""Contextual retrieval reindex script.

Prepends a chunk-level context summary to each embedding before re-embedding,
implementing Anthropic's contextual retrieval pattern (~35% retrieval lift).

Usage:
    python scripts/reindex_contextual.py [--dry-run] [--target wiki|tenants|both]
                                          [--client-id <uuid>] [--limit N]

Targets:
    wiki    — kb_articles table (system-wide wiki, migration 081)
    tenants — (no tenant KB chunks table found in schema; skipped with notice)
    both    — all of the above

The script is idempotent: rows with contextual_reindexed_at IS NOT NULL are
skipped unless --force is passed.

Requirements (all already in backend/requirements.txt or stdlib):
    anthropic, supabase, python-dotenv
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: add project root to sys.path so backend.* imports work
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("reindex_contextual")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CONTEXT_MODEL = "claude-haiku-4-5-20251001"
CONTEXT_MAX_TOKENS = 150  # 50-100 token summaries; 150 gives headroom
CONTEXT_SEPARATOR = "\n\n"
BATCH_SIZE = 10  # rows to process per loop iteration (rate-limit friendly)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_env() -> None:
    """Load .env from project root if python-dotenv is available."""
    try:
        from dotenv import load_dotenv
        env_file = ROOT / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            logger.debug("Loaded .env from %s", env_file)
    except ImportError:
        pass  # dotenv not installed — rely on actual environment


def _get_supabase():
    """Return a Supabase service-role client."""
    from supabase import create_client
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


def _get_anthropic_client():
    """Return an Anthropic client."""
    import anthropic
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


async def _generate_context_summary(
    client,
    doc_title: str,
    category: str,
    chunk_text: str,
) -> str:
    """Call Claude Haiku to produce a 50-100 token context prefix for a chunk."""
    prompt = (
        f"You are indexing a knowledge base article for semantic search.\n\n"
        f"Article title: {doc_title}\n"
        f"Category: {category}\n\n"
        f"Chunk text (first 500 chars):\n{chunk_text[:500]}\n\n"
        f"Write a single concise sentence (50-100 tokens) describing what this "
        f"chunk is about and where it comes from. Start with: "
        f"'This chunk is from \"{doc_title}\"'."
    )
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.messages.create(
            model=CONTEXT_MODEL,
            max_tokens=CONTEXT_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        ),
    )
    return response.content[0].text.strip()


async def _embed_text(text: str) -> list[float]:
    """Embed text using the project's shared embedding service (Voyage AI)."""
    from backend.services.embeddings import embed_text
    return await embed_text(text)


async def _reindex_kb_articles(
    supabase,
    anthropic_client,
    *,
    dry_run: bool,
    limit: int | None,
    force: bool = False,
) -> int:
    """Reindex kb_articles with contextual prefixes. Returns count processed."""
    logger.info("Reindexing kb_articles (dry_run=%s, limit=%s)", dry_run, limit)

    query = (
        supabase.table("kb_articles")
        .select("id, title, category, content, contextual_reindexed_at")
        .order("created_at")
    )
    if not force:
        query = query.is_("contextual_reindexed_at", "null")
    if limit:
        query = query.limit(limit)

    result = query.execute()
    rows = result.data or []
    logger.info("Found %d kb_articles to reindex", len(rows))

    processed = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        for row in batch:
            row_id = row["id"]
            title = row.get("title", "Untitled")
            category = row.get("category", "general")
            content = row.get("content", "")

            if not content.strip():
                logger.warning("kb_articles row %s has empty content — skipping", row_id)
                continue

            try:
                context_summary = await _generate_context_summary(
                    anthropic_client, title, category, content
                )
            except Exception:
                logger.exception("Context generation failed for kb_articles row %s", row_id)
                continue

            enriched_text = context_summary + CONTEXT_SEPARATOR + content

            try:
                embedding = await _embed_text(enriched_text)
            except Exception:
                logger.exception("Embedding failed for kb_articles row %s", row_id)
                continue

            if dry_run:
                logger.info(
                    "[DRY RUN] Would update kb_articles id=%s context_prefix=%r",
                    row_id,
                    context_summary[:80],
                )
            else:
                try:
                    now_iso = datetime.now(timezone.utc).isoformat()
                    supabase.table("kb_articles").update(
                        {
                            "embedding": embedding,
                            "contextual_reindexed_at": now_iso,
                        }
                    ).eq("id", row_id).execute()
                    logger.info("Updated kb_articles id=%s", row_id)
                except Exception:
                    logger.exception("DB update failed for kb_articles row %s", row_id)
                    continue

            processed += 1

    return processed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reindex knowledge base chunks with contextual retrieval prefixes."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing to the database.",
    )
    parser.add_argument(
        "--target",
        choices=["wiki", "tenants", "both"],
        default="both",
        help="Which tables to reindex (default: both).",
    )
    parser.add_argument(
        "--client-id",
        dest="client_id",
        default=None,
        help="Filter to a specific tenant/client UUID (only applies to tenant tables).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of rows to process per table.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-process rows that have already been reindexed.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    _load_env()

    supabase = _get_supabase()
    anthropic_client = _get_anthropic_client()

    total = 0

    if args.target in ("wiki", "both"):
        count = await _reindex_kb_articles(
            supabase,
            anthropic_client,
            dry_run=args.dry_run,
            limit=args.limit,
            force=args.force,
        )
        total += count
        logger.info("kb_articles: %d rows processed", count)

    if args.target in ("tenants", "both"):
        # No per-tenant KB chunks table found in schema (migrations 001-113).
        # The tenant knowledge base is stored as TEXT in widget_configs.knowledge_base
        # (migration 077) — a flat column, not chunked rows with embeddings.
        # Contextual reindex does not apply to that column.
        # If a tenant_kb_chunks table is added in a future migration, add a
        # _reindex_tenant_kb_chunks() function here following the same pattern.
        logger.info(
            "target=tenants: no per-tenant embedding chunks table found in schema. "
            "Tenant KB is stored as plain text in widget_configs.knowledge_base "
            "(migration 077) — skipping. Add _reindex_tenant_kb_chunks() if "
            "a chunked table is created later."
        )
        if args.client_id:
            logger.info("--client-id %s specified but no tenant chunks table to filter.", args.client_id)

    if args.dry_run:
        logger.info("DRY RUN complete. %d rows would be updated.", total)
    else:
        logger.info("Reindex complete. %d rows updated.", total)


if __name__ == "__main__":
    asyncio.run(main())
