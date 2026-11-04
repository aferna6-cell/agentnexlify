#!/usr/bin/env python3
"""Re-chunk one tenant's knowledge base and write Voyage embeddings.

Safe: only the given client_id is deleted and rewritten, and only after
embeddings succeed. Other tenants are left alone.

Usage:
  python scripts/reindex_tenant_kb.py --client-id <uuid>

Requires VOYAGE_API_KEY and the Supabase service credentials in the environment.
Requests are token-batched (VOYAGE_MAX_TOKENS_PER_REQUEST, default 8000) and
paced at VOYAGE_RPM (default 3). A 429 does not delete existing chunks.
"""

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.embeddings import EmbeddingUnavailable  # noqa: E402
from backend.services.tenant_kb_index import reindex_tenant  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-index one tenant KB")
    parser.add_argument("--client-id", required=True, help="Tenant UUID (leads.client_id)")
    args = parser.parse_args()
    try:
        summary = asyncio.run(reindex_tenant(args.client_id))
    except ValueError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    except EmbeddingUnavailable as exc:
        print(f"embeddings unavailable: {exc}", file=sys.stderr)
        return 3
    print(
        f"reindexed {summary['client_id']}: "
        f"{summary['chunks']} chunks, {summary['embedded']} embeddings"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
