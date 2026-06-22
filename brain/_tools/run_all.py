#!/usr/bin/env python3
"""Run all vault validators and print a PASS/FAIL summary. Exit 1 if any hard gate fails."""
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
SCRIPTS = [
    ("required artifacts", "validate_artifacts.py"),
    ("slugs/paths", "validate_slugs.py"),
    ("wikilinks", "validate_wikilinks.py"),
    ("provenance", "validate_provenance.py"),
    ("secrets", "scan_secrets.py"),
    ("manifest", "validate_manifest.py"),
]


def main():
    results = []
    for label, script in SCRIPTS:
        print(f"\n===== {label} ({script}) =====")
        r = subprocess.run([sys.executable, str(TOOLS / script)])
        results.append((label, r.returncode))
    print("\n========== SUMMARY ==========")
    failed = 0
    for label, code in results:
        status = "PASS" if code == 0 else "FAIL"
        if code != 0:
            failed += 1
        print(f"  [{status}] {label}")
    print(f"\n{'ALL GATES PASS' if failed == 0 else f'{failed} GATE(S) FAILED'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
