# SubQ / @subquadratic — 12M Context Claim (Watchlist)

Captured 2026-05-06. Source: viral thread forwarded by Aidan via email 2026-05-05 8:54 PM. Status: **UNVERIFIED — do not act on.**

## Claimed (treat as fiction until proven)

- Sub-quadratic sparse-attention architecture (SSA)
- 12M token context window
- 98% accuracy at full length
- 52x faster than FlashAttention at 1M tokens
- <$1.50/MTok vs Opus 4.7 at $5/$25 ($1.50 ≈ Haiku tier — not unprecedented)
- "Nearly 1,000x less compute"
- Single handle: `@subquadratic`

## What's real (not novel)

Sub-quadratic / sparse attention is an established research direction, not a new idea:
- Liquid AI — sub-quadratic LFM models (real, ships)
- Cartesia — Mamba-derivative state-space models
- Mamba / Mamba-2 — selective state-space (Albert Gu, Tri Dao)
- RWKV — linear-attention recurrent
- Various sparse-attention / Performer / Linformer / BigBird papers (2020-)

Architecture class is genuine. "First frontier model" claim is the marketing.

## What's missing for a real release

| Evidence | Status |
|---|---|
| arxiv paper | Not cited |
| Model card | Not cited |
| MMLU / GPQA / SWE-bench | Not posted |
| RULER (long-context retrieval) | Not posted |
| Needle-in-haystack at 12M | Not posted |
| lmsys arena entry | Not present |
| Artificial Analysis benchmark | Not present |
| SEAL evaluation | Not present |
| Independent reproduction | None |
| Company website / lab footprint | None visible |

Anthropic, OpenAI, Google, DeepSeek, Meta — every real frontier launch ships benchmarks Day 0. Pattern of "viral thread + no benchmarks" maps to demo-stage research or marketing-stage hype, not frontier release.

## Hype shape (`.claude/rules/personality.md` red flags)

- "Now read this part slowly" — engagement bait
- "Every context window you've ever been sold was marketing" — negative parallelism (banned shape)
- "It's you no longer paying for the company's mistake" — moralizing reframe
- "The transformer was the first workable answer" — sweeping declaration without source
- "Opus 4.7 was the long-context benchmark king" — past tense without proof

Matches viral-thread DNA, not technical-launch DNA.

## Re-evaluate when (any one triggers)

1. Paper drops on arxiv with method + ablations
2. Model card published with provider name + license
3. RULER / needle-in-haystack scores posted at 1M+ context
4. Artificial Analysis or lmsys lists the model
5. Third-party reproduction of speed claim (52x FA at 1M)
6. Independent test at full 12M with retrieval task
7. Pricing API actually exists and accepts requests

Until any of those: ignore.

## Action for AgentNexLiFy

**None.** Specifically:
- Widget chat stays `claude-sonnet-4-6` (`.claude/rules/python-fastapi.md`)
- Advisor stays `claude-opus-4-7` (`.claude/rules/opus-4-7.md`)
- KB embeddings stay Voyage
- No abstraction layer for "easy provider swap" — premature, defeats prompt-cache pinning
- No model-routing rule changes

## Why the pricing argument doesn't matter even if true

Our cost ceiling is not driven by Opus per-token rate:
- 99% of tenant chat traffic hits Sonnet ($3/$15) or Haiku ($1/$5), not Opus
- Advisor-executor pattern keeps Opus calls at ~300-500 output tokens per brief (`rules/advisor-consult.md`)
- $1.50/MTok hypothetical from SubQ vs $1/MTok actual Haiku = ~zero arbitrage
- Provider switch cost (prompts retuned, prompt-cache lost, eval suite rerun, contracts) far exceeds any per-token win below 50% delta

Real frontier-cost lever is cache hit rate (`rules/usage-observability.md`), not provider arbitrage.

## Cross-refs

- `.claude/rules/opus-4-7.md` — current Opus version + pricing reality
- `.claude/rules/model-routing.md` — Haiku/Sonnet/Opus split
- `.claude/rules/personality.md` — viral-thread red flag list
- `.claude/rules/usage-observability.md` — actual cost lever (cache hits)
- `knowledge-base/raw/competitors/solo-agency-7-agent-pattern-2026-05-06.md` — same playbook, different thread, same day
