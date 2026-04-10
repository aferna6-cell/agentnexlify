"""End-to-end smoke test for the Field Monitor managed agent.

Asks for a short weekly digest and asserts the agent produced a
structured response listing at least three stories with links.

Expect ~$0.10-0.40 per run (Sonnet + web_search + web_fetch).

Usage:
    python -m scripts.managed_agents.field_monitor_smoke

Exit codes:
    0 — digest returned with at least 3 stories and URLs
    1 — transport / credential / configuration failure
    2 — session streamed but the digest failed structural checks
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
from backend.services.managed_agents_registry import field_monitor  # noqa: E402

_PROMPT = """\
Produce this week's top 3 AI automation news items most relevant to a
founder building service-business automation (lead capture, chat
widgets, scheduling, small-SaaS tooling). This is an automated smoke
test, so 3 stories is enough — do not return 5.

For each story include:
- a headline
- a direct source URL
- exactly 3 short bullet summaries

End with one line naming the signal to watch next week.
"""


def _validate(result: SmokeResult) -> str | None:
    reply = result.reply_text
    if not reply:
        return "reply text was empty"
    if reply.lower().count("http") < 3:
        return "digest has fewer than 3 source URLs"
    if "watch" not in reply.lower() and "next week" not in reply.lower():
        return "digest is missing the next-week signal line"
    return None


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return run_smoke_session(
        handle_factory=field_monitor,
        agent_label="field_monitor",
        kickoff_prompt=_PROMPT,
        session_title="managed-agents field_monitor smoke",
        metadata={
            "flow": "field_monitor",
            "smoke": "true",
        },
        logger_name="managed_agents.field_monitor_smoke",
        validator=_validate,
    )


if __name__ == "__main__":
    raise SystemExit(main())
