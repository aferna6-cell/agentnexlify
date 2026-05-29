"""Demo harness for Agent OS.

A self-contained, API-key-free way to exercise the orchestrator + 18 worker
agents against a realistic small-business profile. ``sample_data`` builds the
fixture; ``cli`` drives it from the terminal.
"""

from __future__ import annotations

from agent_os.demo.sample_data import sample_context, sample_asks

__all__ = ["sample_context", "sample_asks"]
