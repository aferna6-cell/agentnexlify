"""End-to-end smoke test for the Deep Researcher managed agent.

Runs a short competitor-intel prompt and asserts the agent produced
a structured brief with at least a handful of citations. Because the
researcher uses web_search + web_fetch + bash, this is the most
expensive new smoke — expect ~$0.30-1.00 per run (Opus, multi-step).

Usage:
    python -m scripts.managed_agents.researcher_smoke

Exit codes:
    0 — brief returned with Summary / Key Findings / Sources sections
    1 — transport, configuration, or structural-check failure
"""

import logging
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.managed_agents._smoke_common import (  # noqa: E402
    SmokeResult,
    run_smoke_session,
)
from backend.services.managed_agents_registry import deep_researcher  # noqa: E402

_PROMPT = """\
Research GoHighLevel pricing and core features, produce a 300-word brief.

This is an automated integration test. The final output must still
follow your standard brief format:

Summary
Key Findings
Sources
Open Questions

Focus on facts you can verify with primary sources. Do not invent
URLs or quotes. If a claim cannot be verified in the time available,
move it to Open Questions.
"""


def _validate(result: SmokeResult) -> str | None:
    reply = result.reply_text
    if not reply:
        return "reply text was empty"

    required = ("Summary", "Key Findings", "Sources")
    missing = [section for section in required if section not in reply]
    if missing:
        return f"brief is missing required sections: {missing}"

    if "http" not in reply:
        return "brief has no source URLs"

    return None


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    result = run_smoke_session(
        handle_factory=deep_researcher,
        agent_label="deep_researcher",
        kickoff_prompt=_PROMPT,
        session_title="managed-agents researcher smoke",
        metadata={
            "flow": "deep_researcher",
            "smoke": "true",
            "topic": "gohighlevel",
        },
        logger_name="managed_agents.researcher_smoke",
        validator=_validate,
    )
    return 0 if result == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
