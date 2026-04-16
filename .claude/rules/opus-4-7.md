# Claude Opus 4.7 — Canonical Reference

Released 2026-04-16. Source: https://www.anthropic.com/news/claude-opus-4-7

## Model ID
`claude-opus-4-7` — direct upgrade to `claude-opus-4-6`, same pricing ($5/M input, $25/M output).

## Feature summary

| Feature | What it is | When to use | Rule file |
|---|---|---|---|
| Self-verification | Model verifies own outputs before reporting; catches logical faults during planning | Every non-trivial change. Always on for 4.7. | `self-verification.md` |
| /ultrareview | Native Claude Code slash command — dedicated review session flagging bugs + design issues | Before merging any >20-line change, before any PR, after feature complete | `ultrareview.md` |
| Task budgets | API-level token-spend control for long-running agents | Background agents, nightly loops, multi-hour tasks | `task-budgets.md` |
| 3x vision | Images up to 2,576px long edge (~3.75MP, 3x prior) | Screenshots, dense diagrams, high-res design comps | `vision-3x.md` |
| xhigh effort | New level between high and max | Default in Claude Code on Opus 4.7. Start here for agentic work. | — |
| Auto mode | Permissions option — Claude decides on your behalf | Long autonomous runs where user can't approve every step | — |

## Valid model IDs (updated 2026-04-16)
- `claude-opus-4-7` — planning, architecture, critical review, complex decomposition (self-verifying)
- `claude-opus-4-6` — legacy; only keep when you need behavior parity with pre-4.7 prompts
- `claude-sonnet-4-6` — code, debug, multi-file edits, most Agent executions
- `claude-haiku-4-5-20251001` — grammar, formatting, renames, quick classification

## Migration notes (Opus 4.6 → 4.7)

**Two changes that affect token usage:**
1. **Updated tokenizer** — same input can map to 1.0–1.35× more tokens depending on content
2. **More thinking at higher effort** — especially later turns in agentic settings. Better reliability, more output tokens.

**Prompt re-tuning required.** 4.7 follows instructions more literally. Previously-loose interpretations now execute to the letter. Watch for:
- Over-eager execution of instructions that were meant as guidance
- Prompts that relied on model skipping parts — 4.7 won't skip
- Unclear scope becoming over-scoped

**Mitigations:**
- Use `effort` parameter for fine control
- Adjust task budgets for long runs
- Explicitly mark optional steps as optional
- Prompt for conciseness when verbose output isn't needed

## Opus 4.7 operating differences

- **Catches own logical faults during planning phase** — surface your plan and expect push-back
- **Fixes its own code as it goes** — fewer "wrapper functions + fallback scaffolding" bloat
- **Reports missing data** instead of plausible-but-incorrect fallbacks (Hex observation)
- **Pushes back in technical discussions** — more opinionated (Replit observation)
- **Does proofs on systems code before starting** (Vercel observation)
- **Loop resistance improved** — graceful error recovery (Genspark observation)

## Anti-patterns (never do)
- Never call `claude-opus-4-5` or `claude-opus-4-5-20250514` — retired before 4.6
- Never assume old 4.6 prompt will work unchanged — re-tune or accept behavior drift
- Never skip the effort parameter on agentic tasks — xhigh is the new default; start there
- Never invoke 4.7 for truly mechanical work (grammar, rename) — Haiku still wins on cost

## When 4.7 > 4.6 (measured)
- CursorBench: 70% vs 58% (+12 points)
- Rakuten SWE-Bench: 3x more production tasks resolved
- XBOW visual-acuity: 98.5% vs 54.5%
- Notion Agent: +14% task success, 1/3 tool errors
- Databricks OfficeQA Pro: -21% errors

## Cross-refs
- `rules/self-verification.md`
- `rules/ultrareview.md`
- `rules/task-budgets.md`
- `rules/vision-3x.md`
- `rules/model-routing.md`
- `rules/fill-instructions-before-guessing.md`
- `scripts/claude-hooks/invoke-opus-47-features.sh`
