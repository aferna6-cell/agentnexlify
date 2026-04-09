"""Full end-to-end smoke for the Document Drafter integration.

Exercises the COMPLETE pipeline:
  1. draft_document() — runs the real agent, decodes base64, persists
     to the `documents` table via Supabase
  2. Reads back the inserted row (via Supabase Management API)
  3. Decodes `file_bytes` from its `\\x` hex escape
  4. Writes the result to scratch/ and verifies the magic header

This is a real, paid, side-effecting run. It spends ~$0.20 of Opus +
container runtime. Use sparingly.

Usage:
    python -m scripts.managed_agents.drafter_e2e
"""

import logging
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

logger = logging.getLogger("managed_agents.drafter_e2e")

# Agent Nexlify internal tenant — plan=enterprise (eligible for drafting)
_TEST_TENANT_ID = "a890fba0-f89b-41f3-8dff-9cd81bbe6343"


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    from backend.services.document_drafting import (  # noqa: E402
        DocumentDraftingError,
        draft_document,
    )

    logger.info("Drafting a test quote via the real agent...")
    try:
        persisted = draft_document(
            tenant_id=_TEST_TENANT_ID,
            lead_id=None,
            kind="quote",
            customer={
                "name": "E2E Test Customer",
                "email": "e2e-test@example.com",
            },
            line_items=[
                {"description": "Test line item", "qty": 1, "unit_price": 100},
            ],
            notes="Automated integration test — delete after verification.",
        )
    except DocumentDraftingError as exc:
        logger.error("draft_document failed: %s", exc)
        return 1

    doc_id = persisted.get("id")
    title = persisted.get("title")
    logger.info("Persisted document %s: %s", doc_id, title)

    # 2. Read the row back directly via Supabase Management API so we
    #    exercise the storage round-trip.
    import subprocess
    import json as _json

    supabase_token = os.environ.get("SUPABASE_ACCESS_TOKEN")
    if not supabase_token:
        # Fall back to reading the .env file directly.
        from dotenv import dotenv_values
        env = dotenv_values(_REPO_ROOT / ".env")
        supabase_token = env.get("SUPABASE_ACCESS_TOKEN")
    if not supabase_token:
        logger.error("SUPABASE_ACCESS_TOKEN not found in env or .env")
        return 1

    query = (
        "SELECT id, file_name, file_type, "
        "encode(file_bytes, 'hex') AS file_bytes_hex, "
        "LENGTH(file_bytes) AS size "
        f"FROM documents WHERE id = '{doc_id}';"
    )
    payload = _json.dumps({"query": query})
    result = subprocess.run(
        [
            "curl",
            "-s",
            "-X",
            "POST",
            "https://api.supabase.com/v1/projects/pxserpybmajixqrmzaly/database/query",
            "-H",
            f"Authorization: Bearer {supabase_token}",
            "-H",
            "Content-Type: application/json",
            "-d",
            payload,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    rows = _json.loads(result.stdout)
    if not isinstance(rows, list) or not rows:
        logger.error("Read-back returned no rows: %s", result.stdout)
        return 1

    row = rows[0]
    logger.info("Read-back row: id=%s size=%s", row.get("id"), row.get("size"))

    # 3. Decode hex → bytes
    hex_str = row.get("file_bytes_hex")
    if not hex_str:
        logger.error("Row has no file_bytes_hex")
        return 1
    file_bytes = bytes.fromhex(hex_str)
    logger.info("Decoded %d bytes from hex", len(file_bytes))

    # 4. Verify magic header
    file_type = row.get("file_type")
    if file_type in ("docx", "xlsx"):
        assert file_bytes.startswith(b"PK\x03\x04"), f"bad {file_type} magic"
        logger.info("Magic header verified: PK\\x03\\x04 (%s)", file_type)
    elif file_type == "pdf":
        assert file_bytes.startswith(b"%PDF-"), "bad pdf magic"
        logger.info("Magic header verified: %%PDF-")

    # 5. Write to scratch for manual inspection
    scratch_path = _REPO_ROOT / "scratch" / f"e2e-{doc_id}.{file_type}"
    scratch_path.parent.mkdir(exist_ok=True)
    scratch_path.write_bytes(file_bytes)
    logger.info("Wrote decoded file to %s", scratch_path)

    print()
    print("DRAFTER E2E PASSED")
    print(f"  document_id:  {doc_id}")
    print(f"  file_name:    {row.get('file_name')}")
    print(f"  file_type:    {file_type}")
    print(f"  size:         {len(file_bytes)} bytes")
    print(f"  scratch path: {scratch_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
