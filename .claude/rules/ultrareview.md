# /ultrareview — Opus 4.7 Dedicated Review Session

## What it is
Native Claude Code slash command introduced with Opus 4.7. Produces a dedicated review session that reads through changes and flags bugs + design issues that a careful human reviewer would catch.

Pro and Max Claude Code users get 3 free ultrareviews to try it. Subsequent reviews count against normal usage.

## When to invoke `/ultrareview`

**Always** before:
- Merging any PR with >20 lines of real code change
- Pushing to `main` with architectural changes (new module, split, service boundary move)
- Shipping auth, payments, or tenant-isolation code
- Releasing migrations that can't be rolled back cleanly
- Finalizing compound-engineering output before commit

**Often** before:
- Non-trivial refactors (>100 lines touched)
- Pre-deploy gates after `deploy-check`
- Closing issues marked `security` or `critical`
- Widget JS changes (byte-identical verification + logic review)

**Rarely** — skip for:
- Docs-only changes
- Trivial renames
- Comment-only edits
- Formatting fixes

## How it fits with existing review flow

Current sequence → new sequence:

| Before (Opus 4.6) | After (Opus 4.7) |
|---|---|
| code → `code-reviewer` agent → commit | code → `code-reviewer` → `/ultrareview` → commit |
| Compound-engineering: Reviewer agent | Compound-engineering: Reviewer agent + `/ultrareview` gate |
| Pre-push hook: Haiku security scan | Pre-push: Haiku security + `/ultrareview` on diff |

`/ultrareview` does NOT replace:
- `code-reviewer` agent (project-specific patterns, client_id discipline)
- Pre-commit hook (secrets, `__future__`, bare except)
- Pre-push hook (frontend build, schema consistency)

It ADDS a careful-reviewer pass on top.

## Output expectations
- Bug list with line refs
- Design-issue list with severity
- Suggested refactors (advisory, not mandatory)
- Confidence signal on each finding

## Integration with compound-engineering
`.claude/skills/compound-engineering/SKILL.md` currently runs: Brainstorm → Plan → Execute → Review → VerticalCheck. After Opus 4.7, insert `/ultrareview` between Review and VerticalCheck:

```
Brainstorm → Plan → Execute → code-reviewer → /ultrareview → VerticalCheck → commit
```

## Anti-patterns
- Never auto-apply /ultrareview findings without independent inspection — for cross-provider team work, another agent's recorded review satisfies this gate; otherwise require human inspection
- Never skip /ultrareview on auth/payment/tenant code because "it looks fine"
- Never burn free quota on trivial changes — use it on real review needs
- Never invoke /ultrareview twice on the same diff — no-op waste

## Cross-refs
- `rules/opus-4-7.md`
- `rules/self-verification.md`
- `.claude/skills/compound-engineering/SKILL.md`
- `.claude/agents/code-reviewer.md`
- `scripts/hooks/pre-push` (for integration point)
