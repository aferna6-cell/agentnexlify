"""Keep checked-in widget assets synchronized across deploy surfaces."""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ("agentnexlify-widget.js", "preview.html")
CANONICAL_DIR = ROOT / "widget"
TARGET_DIRS = (
    ROOT / "frontend" / "public" / "widget",
    ROOT / "landing-page-v2" / "widget",
)


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def check() -> int:
    failures: list[str] = []

    for asset in ASSETS:
        source = CANONICAL_DIR / asset
        if not source.is_file():
            failures.append(f"missing canonical widget asset: {_relative(source)}")
            continue

        for target_dir in TARGET_DIRS:
            target = target_dir / asset
            if not target.is_file():
                failures.append(f"missing widget asset: {_relative(target)}")
                continue
            if not filecmp.cmp(source, target, shallow=False):
                failures.append(f"widget asset drift: {_relative(source)} != {_relative(target)}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        print("Run `python scripts/sync_widget_assets.py` and commit the updated copies.")
        return 1

    for target_dir in TARGET_DIRS:
        print(f"PASS: widget assets are synchronized with {_relative(target_dir)}")
    return 0


def sync() -> int:
    for asset in ASSETS:
        source = CANONICAL_DIR / asset
        if not source.is_file():
            print(f"FAIL: missing canonical widget asset: {_relative(source)}", file=sys.stderr)
            return 1

        for target_dir in TARGET_DIRS:
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / asset
            shutil.copy2(source, target)
            print(f"SYNC: {_relative(source)} -> {_relative(target)}")

    return check()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if synchronized copies differ")
    args = parser.parse_args()

    return check() if args.check else sync()


if __name__ == "__main__":
    raise SystemExit(main())
