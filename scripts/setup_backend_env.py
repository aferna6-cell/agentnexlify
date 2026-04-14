"""Create a local backend virtualenv with a supported Python version."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


SUPPORTED_PYTHON = {(3, 11), (3, 12)}
DEFAULT_VENV = ".venv"
DEV_DEPENDENCIES = [
    "pytest",
    "pytest-asyncio",
    "pytest-cov",
    "pytest-timeout",
    "diff-cover",
    "pip-audit",
]


def run(command: list[str | Path]) -> None:
    print("+ " + " ".join(str(part) for part in command))
    subprocess.check_call([str(part) for part in command])


def venv_python(venv_path: Path) -> Path:
    if os.name == "nt":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def python_version(python: Path) -> tuple[int, int] | None:
    if not python.exists():
        return None
    output = subprocess.check_output(
        [
            str(python),
            "-c",
            "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')",
        ],
        text=True,
    ).strip()
    major, minor = output.split(".", 1)
    return int(major), int(minor)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--venv",
        default=DEFAULT_VENV,
        help=f"Virtualenv directory to create or refresh. Defaults to {DEFAULT_VENV}.",
    )
    parser.add_argument(
        "--no-dev",
        action="store_true",
        help="Install only backend runtime dependencies, not local test/audit tools.",
    )
    args = parser.parse_args()

    version = sys.version_info[:2]
    if version not in SUPPORTED_PYTHON:
        current_python = ".".join(str(part) for part in sys.version_info[:3])
        supported = ", ".join(".".join(map(str, item)) for item in sorted(SUPPORTED_PYTHON))
        raise SystemExit(
            f"Unsupported Python {current_python}. Use Python {supported}; "
            "the pinned backend dependency set does not support Python 3.14."
        )

    repo_root = Path(__file__).resolve().parents[1]
    venv_path = (repo_root / args.venv).resolve()

    if not venv_path.exists():
        run([sys.executable, "-m", "venv", venv_path])

    python = venv_python(venv_path)
    if not python.exists():
        raise SystemExit(f"Virtualenv Python was not created at {python}")
    if python_version(python) != version:
        print(f"Refreshing existing virtualenv at {venv_path} for Python {version[0]}.{version[1]}")
        run([sys.executable, "-m", "venv", "--upgrade", venv_path])
        if python_version(python) != version:
            raise SystemExit(
                f"Virtualenv at {venv_path} is not using Python {version[0]}.{version[1]}. "
                "Remove it and rerun this setup helper."
            )

    run([python, "-m", "ensurepip", "--upgrade"])
    run([python, "-m", "pip", "install", "--upgrade", "pip"])
    run([python, "-m", "pip", "install", "-r", repo_root / "backend" / "requirements.txt"])

    if not args.no_dev:
        run([python, "-m", "pip", "install", *DEV_DEPENDENCIES])

    print(f"Backend environment ready: {venv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
