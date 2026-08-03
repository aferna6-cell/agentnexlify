#!/usr/bin/env python3
"""Run repo Python commands with the preferred local interpreter.

This wrapper keeps npm scripts from accidentally using a system Python that is
missing backend dependencies. Set AGENTNEXLIFY_PYTHON to override discovery.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List


ROOT = Path(__file__).resolve().parents[1]


def candidate_paths() -> List[Path]:
    env_path = os.environ.get("AGENTNEXLIFY_PYTHON")
    candidates = []
    if env_path:
        candidates.append(Path(env_path))

    if os.name == "nt":
        candidates.extend(
            [
                ROOT / ".venv312" / "Scripts" / "python.exe",
                ROOT / ".venv" / "Scripts" / "python.exe",
                ROOT / ".venv313" / "Scripts" / "python.exe",
            ]
        )
    else:
        candidates.extend(
            [
                ROOT / ".venv312" / "bin" / "python",
                ROOT / ".venv" / "bin" / "python",
                ROOT / ".venv313" / "bin" / "python",
            ]
        )

    candidates.append(Path(sys.executable))
    return candidates


def preferred_python() -> Path:
    # Do NOT Path.resolve() the winner: on POSIX a venv's bin/python is a
    # symlink chain out to the base interpreter, and resolving it escapes the
    # venv entirely (no pyvenv.cfg context -> system site-packages, missing
    # backend deps — the exact failure this wrapper exists to prevent).
    # Windows venvs use a real python.exe, which is why this never showed
    # there. Absolute-ize without following symlinks.
    for path in candidate_paths():
        if path.exists():
            return path if path.is_absolute() else (Path.cwd() / path)
    return Path(sys.executable)


def main(argv: List[str]) -> int:
    python = preferred_python()
    if not argv:
        print(python)
        return 0

    completed = subprocess.run([str(python), *argv], cwd=ROOT, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
