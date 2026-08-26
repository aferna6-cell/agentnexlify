---
title: AI Model Release Tracker 2026 — Launch Events, Gating, Availability Lag
date: 2026-08-05
source_url: https://axis-intelligence.com/ai-model-release-tracker/
fetched_at: 2026-08-26
category: frontier_ai
tags: [model-releases, anthropic, openai, google, deepseek, qwen, fable-5, mythos-5, gpt-5-6, gemini-3-6, pricing, availability]
---

# AI Model Release Tracker 2026

*Axis Intelligence Research, with Sarah Mitchell. Last updated Aug 5, 2026. Dataset licensed CC BY 4.0.*

## Summary stats (Apr 24 – Aug 3, 2026)

- **11** launch events tracked.
- **7 of 11 (63.6%)** were gated at launch (preview, waitlist, partner-only, or announced-not-shipped).
- **Announcement-to-Availability Lag**: median 0 days, mean 7.1 days.

## Timeline

| Date | Vendor | Model | Status / notes |
|---|---|---|---|
| Aug 3 | Alibaba | Qwen3.8-Max | API GA, $2 / $6 per MTok; open weights promised |
| Jul 30 | Google | Gemini Robotics ER 2 | Preview |
| Jul 21 | Google | Gemini 3.6 Flash + 3.5 Flash-Lite | GA; **deprecates `temperature` / `top_p` / `top_k`** |
| Jul 9 | OpenAI | GPT-5.6 family (Sol / Terra / Luna) | GA after 13-day preview from Jun 26. Sol $5 / $30 per MTok; 80 on Artificial Analysis Coding Agent Index; 92.2% BrowseComp |
| Jun 30 | Google | Gemini Omni Flash | Preview; 720p video |
| Jun 12 | Anthropic | Claude Fable 5 / Mythos 5 | **Suspended** under a US export-control directive; restored Jul 1 |
| Jun 9 | Anthropic | Claude Fable 5 + Mythos 5 | Launch. Both $10 / $50 per MTok. Fable 5 routes cyber/bio/chem/distillation-risk queries to Opus 4.8 (<5% of sessions). Mythos 5 partner-only via Project Glasswing |
| May 19 | Google | Gemini 3.5 Flash | GA |
| May 19 | Google | Gemini 3.5 Pro | Announced, not shipped — 78 days open as of update |
| Apr 24 | DeepSeek | V4-Pro (1.6T total / 49B active) + V4-Flash (284B / 13B active) | Open weights, 1M context |

## Observations from the tracker

- Frontier pricing has bifurcated: $2–6 per MTok (Qwen, Gemini Flash tier) vs $5–50 per MTok (GPT-5.6 Sol, Fable 5).
- Vendors increasingly ship GA the same day they announce (median lag 0) but gate the top tier behind partner programs.
- Google is removing classic sampling knobs on Gemini 3.6 — code that passes `temperature` will break.

## Notes for AgentNexLiFy

- Cross-check against `raw/frontier-ai/ai-release-tracker-august-2026.md` when compiling — two independent trackers now cover Jun–Aug 2026.
- `claude-fable-5` at $10/$50 is 2× Opus 4.8 ($5/$25). Keep Fable 5 for planning/advisor roles only; widget chat stays on Sonnet/Haiku (see `.claude/rules/model-routing.md`).
- Fable 5's routing of dual-use queries to Opus 4.8 is invisible to the API caller — no code change needed, but latency may vary on those <5% of sessions.
