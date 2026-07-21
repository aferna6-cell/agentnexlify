"""KB article provenance helpers (issue #70).

Annotate retrieved ``kb_articles`` rows with source + validation metadata and
record citations, so widget answers can cite a source and warn when the
underlying article is stale.

Every function is fail-open: any DB or parse error degrades to "no provenance"
and never raises, so a bug here can never take down the widget chat path.

Provenance columns live on ``kb_articles`` (migration 181):
  * ``source_urls TEXT[]`` (existing, migration 081) — reused for the source.
  * ``last_validated TIMESTAMPTZ`` (migration 181).
  * ``citation_count INT`` (migration 181), bumped via the
    ``increment_kb_citations(uuid[])`` RPC (migration 181).

The semantic ``match_kb_articles`` RPC returns only id/slug/title/summary, so
provenance is merged here by article id after retrieval — uniform across the
semantic and FTS paths, and independent of that RPC's signature.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# An article is flagged stale once its last validation is older than this.
STALE_AFTER_DAYS = 60

# Columns pulled in the provenance back-fill query.
_PROVENANCE_COLUMNS = "id, source_urls, last_validated, citation_count"

# RPC + table names (kb_articles is a global, non-tenant-scoped table).
_INCREMENT_RPC = "increment_kb_citations"
_KB_TABLE = "kb_articles"


def _parse_timestamp(value: Any) -> Optional[datetime]:
    """Coerce a Supabase timestamptz (ISO string) or datetime to aware UTC."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


def _first_source_url(article: Dict[str, Any]) -> str:
    """Prefer a merged singular ``source_url``; fall back to first source_urls[]."""
    url = (article.get("source_url") or "").strip()
    if url:
        return url
    urls = article.get("source_urls") or []
    if isinstance(urls, (list, tuple)):
        for candidate in urls:
            if candidate and str(candidate).strip():
                return str(candidate).strip()
    return ""


def provenance_suffix(
    article: Dict[str, Any],
    *,
    now: Optional[datetime] = None,
    stale_after_days: int = STALE_AFTER_DAYS,
) -> str:
    """Build the provenance footer appended to a KB article's prompt line.

    Returns e.g. ``" [Source: https://…, last verified 2026-05-01]"`` plus,
    when the article is older than ``stale_after_days``,
    ``" ⚠ KB article may be outdated"``. Returns ``""`` when the article
    carries no source and no validation date.
    """
    now = now or datetime.now(timezone.utc)
    parts: List[str] = []

    url = _first_source_url(article)
    validated = _parse_timestamp(article.get("last_validated"))

    if url or validated:
        bits: List[str] = []
        if url:
            bits.append(f"Source: {url}")
        if validated:
            bits.append(f"last verified {validated.date().isoformat()}")
        parts.append(" [" + ", ".join(bits) + "]")

    if validated is not None and (now - validated).days > stale_after_days:
        parts.append(" ⚠ KB article may be outdated")

    return "".join(parts)


def merge_provenance(db, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Bulk-merge provenance columns into ``rows`` by article id, in place.

    One ``.in_("id", ids)`` query (never N+1). Fail-open: on any error the rows
    are returned unchanged (no source footer, no stale warning) so retrieval
    still works even before migration 181 is applied.
    """
    if not rows:
        return rows
    ids = [row.get("id") for row in rows if row.get("id")]
    if not ids:
        return rows

    try:
        result = (
            db.table(_KB_TABLE)
            .select(_PROVENANCE_COLUMNS)
            .in_("id", ids)
            .execute()
        )
        provenance = {row["id"]: row for row in (result.data or []) if row.get("id")}
    except Exception:
        logger.warning(
            "kb_provenance: back-fill query failed — returning rows without provenance",
            exc_info=True,
        )
        return rows

    for row in rows:
        prov = provenance.get(row.get("id"))
        if not prov:
            continue
        # Overwrite (not setdefault): the FTS RPC (migration 155) already returns
        # source_url=None / last_validated=None / citation_count=0 stub columns,
        # so setdefault would leave those stubs in place. The kb_articles row read
        # here is the authoritative provenance source.
        urls = prov.get("source_urls") or []
        row["source_urls"] = prov.get("source_urls")
        row["source_url"] = (
            str(urls[0]).strip()
            if isinstance(urls, (list, tuple)) and urls and urls[0]
            else None
        )
        row["last_validated"] = prov.get("last_validated")
        row["citation_count"] = prov.get("citation_count")
    return rows


def record_citations(db, rows: List[Dict[str, Any]]) -> None:
    """Fire-and-forget: atomically bump ``citation_count`` for the cited ids.

    Fail-open: swallows every error so counting can never block or break a chat
    response. Best-effort telemetry, not a transactional guarantee.
    """
    ids = [row.get("id") for row in (rows or []) if row.get("id")]
    if not ids:
        return
    try:
        db.rpc(_INCREMENT_RPC, {"article_ids": ids}).execute()
    except Exception:
        logger.warning(
            "kb_provenance: citation increment failed for %d article(s)",
            len(ids),
            exc_info=True,
        )
