#!/usr/bin/env python3
"""Controlled M8 smoke entrypoint — delegates to the real live runner.

Authorization guard only lived here previously. Live provider/DB evidence is
produced by ``scripts/m8_live_smoke.py``. This wrapper keeps the historical
command path and forwards all args/env.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> int:
    target = Path(__file__).resolve().parent / "m8_live_smoke.py"
    # runpy returns the module globals; exit via SystemExit from the target.
    try:
        runpy.run_path(str(target), run_name="__main__")
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else (0 if code is None else 1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
