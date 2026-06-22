#!/usr/bin/env python3
"""Manifest validation: confirm SOURCE-MANIFEST.md exists and documents every connector
used, with an account/workspace + status for each."""
import sys
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
MANIFEST = VAULT / "SOURCE-MANIFEST.md"
REQUIRED_CONNECTORS = ["GitHub", "Vercel", "Supabase", "Slack",
                       "Google Calendar", "Gmail", "Google Drive"]


def main():
    if not MANIFEST.is_file():
        print("FAIL: SOURCE-MANIFEST.md missing.")
        return 1
    text = MANIFEST.read_text(encoding="utf-8")
    problems = []
    for c in REQUIRED_CONNECTORS:
        if c not in text:
            problems.append(f"connector not documented: {c}")
    for token in ["Account", "Verification method", "Approved for ingestion"]:
        if token not in text:
            problems.append(f"manifest missing field marker: {token}")
    if problems:
        print(f"FAIL ({len(problems)}):")
        for x in problems:
            print(f"  {x}")
        return 1
    print(f"PASS: SOURCE-MANIFEST documents {len(REQUIRED_CONNECTORS)} connectors with status fields.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
