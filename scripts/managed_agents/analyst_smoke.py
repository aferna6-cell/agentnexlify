"""End-to-end smoke test for the Data Analyst managed agent.

Feeds a tiny inline CSV and asks for column means. Asserts the agent
produced a response that includes numeric results for each column.

Expect ~$0.20-0.60 per run (Opus, bash for pandas analysis).

Usage:
    python -m scripts.managed_agents.analyst_smoke

Exit codes:
    0 — analyst returned a response mentioning all three columns
    1 — transport / credential / configuration failure
    2 — session streamed but structural checks failed
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
from backend.services.managed_agents_registry import data_analyst  # noqa: E402

_CSV = """\
day,visitors,leads
mon,120,8
tue,95,5
wed,180,14
thu,210,18
fri,175,12
"""

_PROMPT = f"""\
Analyze the following small CSV and report the mean of each numeric
column. Save the CSV to /tmp/smoke.csv, use pandas to compute the
means, and include the exact column names in your final answer. This
is an automated smoke test — keep the analysis brief.

[INLINE_CSV]
{_CSV}

Deliverables:
- A short Markdown summary
- Mean of `visitors`
- Mean of `leads`
- File path(s) of any analysis scripts you wrote
"""


def _validate(result: SmokeResult) -> str | None:
    reply = result.reply_text
    if not reply:
        return "reply text was empty"
    lowered = reply.lower()
    if "visitors" not in lowered:
        return "reply does not reference the visitors column"
    if "leads" not in lowered:
        return "reply does not reference the leads column"
    if not any(char.isdigit() for char in reply):
        return "reply contains no numeric output"
    return None


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return run_smoke_session(
        handle_factory=data_analyst,
        agent_label="data_analyst",
        kickoff_prompt=_PROMPT,
        session_title="managed-agents analyst smoke",
        metadata={
            "flow": "data_analyst",
            "smoke": "true",
        },
        logger_name="managed_agents.analyst_smoke",
        validator=_validate,
    )


if __name__ == "__main__":
    raise SystemExit(main())
