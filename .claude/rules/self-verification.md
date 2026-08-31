# Self-Verification — Opus 4.7 Feature

## Rule
Before reporting completion on any non-trivial task, Opus 4.7 devises a verification step and executes it. This is built into the model, but the rule below governs WHEN to explicitly invoke it and HOW it should manifest in output.

## What Opus 4.7 does automatically
- Catches own logical faults during the planning phase
- Fixes own code as it goes
- Reports when data is missing instead of plausible-but-incorrect fallbacks
- Does proofs on systems code before starting work (Vercel observation)
- Verifies outputs against a self-generated check (e.g. round-trips data through a recognizer to validate)

## When to force explicit self-verification

Always run an explicit verification step before declaring done:
- After writing any code change
- After writing any config change
- After any refactor (characterization tests before + after)
- After any bug fix (regression test included)
- After any schema change (migration applied cleanly + queries resolve)
- After any auth/permission change (round-trip user flow)

## Verification patterns by task type

| Task | Verification step |
|---|---|
| Code change | Run unit tests OR `python -c "import ..."` smoke + read diff |
| Refactor | Characterization tests pass + public API unchanged (`gitnexus_impact`) |
| Bug fix | Regression test exists, passes, and fails on HEAD~1 |
| Schema migration | `mcp__supabase__apply_migration` succeeds + representative query returns data |
| API endpoint | `curl` the endpoint (or httpx) with real payload, verify 2xx + schema |
| Frontend change | `npm run build` clean + `preview_*` smoke (per `preview_tools` rules) |
| Widget change | Byte-identical check between `widget/` and `frontend/public/widget/` |
| Automation/cron | Dry-run the handler OR inspect next-scheduled-at |

## Output format
Every task-completion message MUST include a verification line. Format:

```
Verified: <what you checked> — <PASS/FAIL>
```

Examples:
- `Verified: pytest backend/tests/test_leads.py — PASS (12 passed)`
- `Verified: python -c "from backend.services.automation_engine import ..." — PASS`
- `Verified: git diff shows only expected changes + wc -l respects Rule 9 — PASS`

If you cannot verify in the current env, state WHY:
- `Verified: deferred — pytest blocked by missing dep X. CI will confirm.`

## Never
- Never declare done without a verification line
- Never claim "looks correct" in place of running a check
- Never skip verification because "it's obvious"
- Never accept the self-verification output from a subagent without inspecting it

## Enforcement
- Confidence gate (`scripts/claude-hooks/confidence-gate.sh`) already demands evidence at Stop
- This rule adds: verification line in EVERY task-done message, not just at session Stop
- Invoke-regularly hook (`scripts/claude-hooks/invoke-opus-47-features.sh`) injects reminder
- Escape hatch when &lt;90% is only a human/external blocker: `.claude/rules/confidence-gate-escape.md` (stop; do not busy-loop)

## Cross-refs
- `rules/opus-4-7.md`
- `rules/ultrareview.md` — after self-verification, optionally invoke `/ultrareview` for deeper audit
- `scripts/claude-hooks/confidence-gate.sh`
- `rules/confidence-gate-escape.md`
- `rules/workflow-orchestration.md` (quality gates)
