#!/usr/bin/env python3
"""Direct Anthropic API classifier for issue-to-pr loop.

Replaces claude-code CLI invocation which was polluted by project hooks +
126k cache tokens per call ($0.17). Direct API call costs ~$0.0002/call.

Input: issue number + title + body via stdin as JSON: {"number": N, "title": "...", "body": "..."}
Output: strict JSON: {"ready": bool, "reason": "...", "clarifying_questions": [...]}
Exit: 0 on success, 1 on API error (falls back to loop default).
"""
import json
import os
import re
import sys

try:
    from anthropic import Anthropic
except ImportError:
    print('{"ready":false,"reason":"anthropic SDK missing","clarifying_questions":["pip install anthropic"]}')
    sys.exit(1)

FALLBACK = '{"ready":false,"reason":"classifier API error","clarifying_questions":["rerun manually"]}'


def main() -> int:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(FALLBACK)
        return 1

    try:
        payload = json.load(sys.stdin)
    except Exception:
        print(FALLBACK)
        return 1

    prompt = f"""Triage this GitHub issue. Is it ready for an AI subagent to implement end-to-end with no human input?

Issue #{payload.get('number')}: {payload.get('title', '')}

{payload.get('body', '')}

Return ONLY this JSON, nothing else:
{{"ready": true|false, "reason": "one short sentence", "clarifying_questions": ["..."]}}

Ready criteria: goal concrete, files identifiable, success criteria inferable, no architecture decisions needed, no new secrets required."""

    client = Anthropic(api_key=api_key)
    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        sys.stderr.write(f"classifier api error: {e}\n")
        print(FALLBACK)
        return 1

    text = "".join(block.text for block in resp.content if block.type == "text")

    m = re.search(r"\{(?:[^{}]|(?:\{[^{}]*\}))*\}", text, re.DOTALL)
    if not m:
        sys.stderr.write(f"no JSON in response: {text[:200]}\n")
        print(FALLBACK)
        return 1

    try:
        parsed = json.loads(m.group(0))
        if "ready" not in parsed:
            sys.stderr.write(f"missing 'ready' key: {m.group(0)[:200]}\n")
            print(FALLBACK)
            return 1
        print(json.dumps(parsed))
        return 0
    except json.JSONDecodeError:
        sys.stderr.write(f"JSON parse failed: {m.group(0)[:200]}\n")
        print(FALLBACK)
        return 1


if __name__ == "__main__":
    sys.exit(main())
