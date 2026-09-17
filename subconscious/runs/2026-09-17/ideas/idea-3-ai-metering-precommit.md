# Idea 3 — Pre-commit Guard for New Unguarded AI Calls

**Category:** code_health / operational
**Effort:** S (add check to check_project_invariants.py + hook)
**Confidence:** MEDIUM-HIGH

## Problem

Step 9L AI metering sweep reports 45 violations today (+5 from yesterday).
Growth rate: ~5 new unguarded functions per day.
Owner closed #875 as duplicate. No structural prevention exists.

Evidence (2026-09-17.md):
- 45 violations (16 routers, 29 services) — UP from 40 (+5 in 1 day)
- New today: os_research.py:run_research, os_sync/conversations.py:_summarize_session,
  photo_triage.py:triage_photos, quote_builder.py:build_quote, review_responder.py:draft_response
- Pattern: new AI-calling functions are committed without ai_usage_guard decoration

Step 9L detects violations after commit. This idea stops them before commit.

## Implementation

Two changes:

**1. Add incremental guard to `scripts/check_project_invariants.py`**

New check (Check 11): when `git diff --staged` shows a new function calling `anthropic` or `claude`,
verify that function is wrapped by `ai_usage_guard`. If not, print warning with function:line.

```python
def check_new_ai_calls_guarded(staged_diff: str) -> list[str]:
    """Flag newly staged functions that call claude/anthropic without ai_usage_guard."""
    violations = []
    # Parse staged diff for added lines with anthropic/claude calls
    # Cross-check: is the enclosing function decorated with @ai_usage_guard?
    return violations
```

**2. Wire into pre-commit hook**

Add `check_new_ai_calls_guarded()` call in `scripts/install-hooks.sh` pre-commit chain.
Warning-only on first run (not blocking) — escalate to ERROR after 30-day runway.

## Expected outcome

- New AI-calling functions flagged at commit time, not discovered 24h later in nightly
- Gradual reduction in 45-violation backlog as authors fix before committing
- 30-day warning runway gives developers time to learn pattern before hard block

## Risk

MEDIUM. Requires Python AST parsing of staged diff. False-positive risk (decorator on outer
scope, not immediate function). Mitigate: warn-only, not block. Author can add `# noqa: ai-guard`
to intentionally exempt.

## Notes

Step 9L (detection) + this idea (prevention) = complete coverage.
Owner closed #875 but did not close the tracking concern — this addresses root cause.
