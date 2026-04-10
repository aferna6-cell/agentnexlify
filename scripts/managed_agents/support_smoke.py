"""End-to-end smoke test for the Support Agent managed agent.

Runs a real session, sends a labeled tenant-context prompt, and asserts
the agent produced an assistant reply. Validates the session_id contract
and the transcript. Does NOT hit the backend DB — the smoke script
builds the four labeled blocks inline so it can run before any tenant
data exists.

Expect ~$0.05-0.15 per run (Sonnet, no tools actually invoked for
business-hours queries).

Usage:
    python -m scripts.managed_agents.support_smoke

Exit codes:
    0 — session completed with a non-empty reply
    1 — transport / credential / configuration failure
    2 — session streamed but assertions failed
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
from backend.services.managed_agents_registry import support_agent  # noqa: E402

_PROMPT = """\
[TENANT_CONTEXT]
Business name: Smoke Test Salon
Business type: hair salon
Business hours:
Timezone: America/New_York
- Monday: 09:00-18:00
- Tuesday: 09:00-18:00
- Wednesday: 09:00-18:00
- Thursday: 09:00-20:00
- Friday: 09:00-20:00
- Saturday: 10:00-16:00
- Sunday: closed

[KB_SNIPPET]
Custom instructions:
Tone is warm, concise, practical. Always confirm booking questions.
Knowledge base excerpt:
We are a small neighborhood salon. Walk-ins welcome Monday-Friday
before 4pm. Appointments preferred for color services.
FAQ entries:
- Q: Do you accept walk-ins?
  A: Yes, Monday through Friday before 4pm.
- Q: Do you do color services?
  A: Yes, by appointment only.

[CONVERSATION_HISTORY]
(no prior conversation history)

[QUESTION]
What are your business hours?

Respond to the customer using only the provided tenant context. Prefer
JSON with answer, confidence, and escalate_reason.
"""


def _validate(result: SmokeResult) -> str | None:
    if not result.reply_text:
        return "reply text was empty"
    lowered = result.reply_text.lower()
    if "monday" not in lowered and "hours" not in lowered:
        return "reply did not reference the provided hours context"
    return None


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return run_smoke_session(
        handle_factory=support_agent,
        agent_label="support_agent",
        kickoff_prompt=_PROMPT,
        session_title="managed-agents support_agent smoke",
        metadata={
            "tenant_id": "smoke_test",
            "flow": "support_agent",
            "smoke": "true",
        },
        logger_name="managed_agents.support_smoke",
        validator=_validate,
    )


if __name__ == "__main__":
    raise SystemExit(main())
