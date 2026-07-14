# Idea 4 — Local KB Autopopulate in Each Subconscious Session

## Category
operational

## Effort
XS (add bash call to SKILL.md or run manually each session)

## Evidence
- GH #403: ANTHROPIC_API_KEY missing in GitHub Actions secrets → KB autopopulate stalled
- KB last run: 2026-05-05 (69 days dark as of 2026-07-14)
- All autonomous agents (lead qualifier, widget support, advisor) operating on 69-day-stale KB
- Subconscious runner has Claude access (this session proves it)
- `scripts/daily/kb-autopopulate.sh` exists and was designed for both local + CI use

## Action
Add to Phase 1 of `.claude/skills/subconscious/SKILL.md`:
"Run `bash scripts/daily/kb-autopopulate.sh` if GH #403 still open (KB stale >48h)."

## Expected Impact
KB updates every ~12h (subconscious runs 2x/day) instead of never.
69-day staleness ends today.
No code changes. No human approval. No GH Actions dependency.

## Risk
HIGH uncertainty: ANTHROPIC_API_KEY may not be available in remote execution environment (claude.ai/code). The Python .venv scripts call Anthropic API directly — different from Claude Code's internal API access. If the env var is not set in subprocess context, script silently fails or noisy-errors. UNVERIFIED.

## Autonomy
Modifying a SKILL.md is AUTONOMOUS-EXECUTABLE by nightly-commit-review. But the runtime behavior is uncertain.

## Weakness
This is a WORKAROUND for GH #403. Once the human sets ANTHROPIC_API_KEY in GH Actions (the 2-minute fix), this workaround becomes redundant. Does not address root cause.
