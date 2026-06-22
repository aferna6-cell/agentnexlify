#!/usr/bin/env python3
"""Required-artifact validation: confirm all required folders + files exist."""
import sys
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
REQ_DIRS = ["People", "Companies", "Projects", "Products", "Topics", "Decisions",
            "Commitments", "Procedures", "Preferences", "Context Packs", "Sources",
            "Maps", "Reports", "_tools"]
REQ_FILES = ["README.md", "SOURCE-MANIFEST.md", "VALIDATION-REPORT.md",
             "COMPLETION-AUDIT.md", "INGESTION-LOG.md", "state.json",
             "Reports/ORIENTATION-REPORT.md"]


def main():
    missing = []
    for d in REQ_DIRS:
        if not (VAULT / d).is_dir():
            missing.append(f"DIR  {d}")
    for f in REQ_FILES:
        if not (VAULT / f).is_file():
            missing.append(f"FILE {f}")
    if missing:
        print(f"FAIL ({len(missing)} missing):")
        for x in missing:
            print(f"  {x}")
        return 1
    print(f"PASS: all {len(REQ_DIRS)} folders + {len(REQ_FILES)} required files present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
