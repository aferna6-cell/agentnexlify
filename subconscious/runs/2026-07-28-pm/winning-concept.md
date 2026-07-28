# Winning Concept — 2026-07-28-pm (Run 102)

## Recommendation
Update `.claude/skills/god-class-splitter/SKILL.md` to add 2 missing patterns documented by skill-discovery-2026-07-27: (1) original file keeps backward-compat re-exports after the split; (2) grep test files for old patch targets and update to new module path before running tests.

## Why This, Why Now

`docs/skill-discovery/2026-07-27.md` §"Existing Skill Updates" explicitly called this HIGH priority with the exact reason: "both omissions cause test failures immediately after the split." This week produced two god-class splits (`calls.py` 1196L → 3 modules; `email_sequences.py` 1143L → 3 modules) and BOTH hit the same two failures from the same two missing steps. That's a 100% reproduction rate.

The pattern is not accounted for anywhere in the current SKILL.md. When the skill fires on the next god-class split, the executor will do the structural split correctly (the skill covers this) but will omit re-exports and leave stale patch targets — exactly as happened twice this week.

XS effort: 2 short paragraphs added to an existing skill. Channel proven: subconscious SKILL.md edits have landed cleanly across multiple prior runs. Zero production risk: SKILL.md only fires when explicitly invoked.

## Implementation Sketch

In `.claude/skills/god-class-splitter/SKILL.md`, after the section describing the split itself, add:

```markdown
### After splitting: backward-compat re-exports

The original file must keep re-exports for every name that moved:

```python
# calls.py (after splitting to calls_webhooks.py + calls_ai.py)
from .calls_webhooks import *  # noqa: F401
from .calls_ai import *        # noqa: F401
```

Without this, every existing `from backend.routers.calls import X` import breaks.
This is not optional — downstream callers exist across the codebase.

### After splitting: update test patch targets

Before running tests, grep for the old module path in test files:

```bash
grep -rn 'patch("backend.routers.<old_file>.' backend/tests/
```

Every match must be updated to the new module path (e.g., `backend.routers.calls_webhooks.*`).
Stale patch targets cause fixture mocks to do nothing — the real function runs, tests fail
with unexpected side effects rather than "patch not found," making root cause hard to find.
```

## Bonus Action: PR #577 Comment

Also post a comment on PR #577 via GH MCP explaining that Step 9G in that PR is now obsolete:
- Original Step 9G triggers `gh workflow run kb-autopopulate.yml`
- CCR Routine (cloud session) was deployed 2026-07-23 and now handles KB autopopulate
- GH Actions broken repo-wide (#500) — `gh workflow run` would silently fail
- Merging PR #577 as-is would land wrong diagnostic text on #403
- Corrected Step 9G should use `gh pr list --search "head:kb-autopopulate"` CCR health check

## Backlog Recommendations

1. **(MEDIUM carry-forward) Step 9G CORRECTED** — CCR Routine health monitor via `gh pr list` check. KB healthy now (5 days since last run). Pick up when KB approaches 7-day threshold or owner targets PR #577 revision.

2. **(HIGH customer impact, prerequisite unmet) Step 9H — Silent-green tenant heartbeat** — nightly query of `conversations` table for paid tenants with 0 conversations in 7 days. Keys Koffee-class churn prevention. Prerequisite: verify `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` in nightly CCR bash environment. Use `client_id`, NOT `tenant_id` (critical invariant).

3. **(XS, unblocks autonomy) GH comment + `ai-ready` label on #605** — autonomy sweeper bug. Crash mid-verify strands run in `running` state permanently. Must fix before arming Routine. Label enables issue-to-pr-loop pickup.

## Confidence
**HIGH** — Same channel (SKILL.md edit on existing skill) used across prior subconscious runs. Evidence is two direct occurrences this week with identical failure class, explicitly flagged HIGH by skill discovery. No deployment risk.
