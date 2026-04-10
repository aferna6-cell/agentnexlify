"""End-to-end smoke test for the Structured Extractor managed agent.

Feeds a fake lead email and asserts the agent returns parseable JSON
with the expected `lead` schema keys. This is the one smoke script that
strictly validates the JSON contract because the extractor is the
agent with the most rigid output format.

Expect ~$0.01-0.03 per run (Haiku, no tools).

Usage:
    python -m scripts.managed_agents.extractor_smoke

Exit codes:
    0 — JSON reply parsed and contains expected lead keys
    1 — transport / credential / configuration failure
    2 — session streamed but JSON parse or schema check failed
"""

import json
import logging
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.managed_agents._smoke_common import (  # noqa: E402
    SmokeResult,
    run_smoke_session,
)
from backend.services.managed_agents_registry import (  # noqa: E402
    structured_extractor,
)

_LEAD_FIELDS = ("name", "email", "phone", "interest", "timeline", "budget", "source")

_PROMPT = """\
Extract structured data from the raw text into one JSON object.

[SCHEMA]
target_schema: lead
fields:
- name
- email
- phone
- interest
- timeline
- budget
- source

Rules:
- Return ONLY valid JSON with exactly these keys.
- Use null for any missing or unknown field.

[RAW_TEXT]
Hi, my name is Maria Lopez. I'm looking to get a quote for a full
driveway pressure wash and deck sealing at my home in Newark. Phone
is 973-555-0134, email maria.lopez@example.com. I'd like to get this
done within the next two weeks. Budget is around 500 dollars. Found
you through the Google ad.
"""


def _parse_json(reply: str) -> dict | None:
    reply = reply.strip()
    try:
        parsed = json.loads(reply)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", reply, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def _validate(result: SmokeResult) -> str | None:
    if not result.reply_text:
        return "reply text was empty"

    parsed = _parse_json(result.reply_text)
    if parsed is None:
        return f"reply is not valid JSON: {result.reply_text[:200]!r}"

    missing = [field for field in _LEAD_FIELDS if field not in parsed]
    if missing:
        return f"reply missing required lead fields: {missing}"

    print(f"  parsed JSON:      {json.dumps(parsed, ensure_ascii=False)[:300]}")
    return None


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return run_smoke_session(
        handle_factory=structured_extractor,
        agent_label="structured_extractor",
        kickoff_prompt=_PROMPT,
        session_title="managed-agents extractor smoke",
        metadata={
            "tenant_id": "smoke_test",
            "flow": "structured_extractor",
            "target_schema": "lead",
            "smoke": "true",
        },
        logger_name="managed_agents.extractor_smoke",
        validator=_validate,
    )


if __name__ == "__main__":
    raise SystemExit(main())
