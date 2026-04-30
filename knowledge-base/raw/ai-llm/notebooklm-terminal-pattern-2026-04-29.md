---
title: NotebookLM-via-terminal — pattern note for AgentNexLiFy
captured: 2026-04-29
source: community post on Claude Code controlling NotebookLM via CLI + Obsidian sync
type: pattern-extraction
status: extract patterns; skip integration
---

# What it is

Claude Code drives NotebookLM from terminal:
- YouTube/arXiv/PDF/podcast source ingestion
- Up to 300 sources per notebook
- Cited Q&A grounded in sources, ~60% citations strong-match audited
- Audio overviews -> MP3
- Mind maps, flashcards, source dashboards
- Output syncs to Obsidian with passage-level wikilinks

# Verdict

| Slice | Decision |
|---|---|
| Customer-facing (widget RAG) | NO — Google ToS, no commercial multi-tenant API, IP risk on audio. Existing pgvector + raw/wiki split already covers cited RAG. |
| Internal eng research | MARGINAL — already have kb-query + 98 wiki articles. NotebookLM gap = video/podcast ingestion + audio overviews. Replace with yt-dlp + whisper + existing `/kb-ingest`. |
| Partner research (sales/marketing/brand-voice) | YES low-risk — use NotebookLM web free for prospect/competitor research. No platform integration. |

# Patterns to extract (NOT the tool)

| Pattern | AgentNexLiFy slot |
|---|---|
| YouTube/podcast URL -> KB | extend `/kb-ingest` skill: detect URL host, route to yt-dlp + whisper -> markdown -> existing pipeline |
| Passage-level citations on widget answers | tighten source pinning in widget chat replies; thread `kb_sources.id` + chunk offset through to widget response |
| Q&A log per tenant | new `widget/knowledge-bases/<tenant>_qa.md` updated by widget runtime; daily cron compiles |
| Per-notebook persona ("concise, no preamble") | add `tone:` frontmatter field to `<tenant>_kb.md`; prepend to widget system prompt |
| Source dashboard | tenant operator dashboard backlog; pairs with voice-control spike (operator persona, hands-busy) |

# Why no platform integration

- NotebookLM = Google product, no commercial API for resale
- Per-tenant notebook provisioning = brittle scaffolding tied to a free product
- Audio overviews = Google IP, redistribution risk for tenant-branded audio
- Existing pgvector RAG already gives cited answers; we'd be paying lock-in for marginal UX

# Action items

1. Spike ticket: extend `/kb-ingest` to support YouTube + podcast URLs (separate file: `kb-ingest-yt-podcast-spike.md`)
2. Park Q&A-log + tone-frontmatter ideas in onboarding-v2 backlog
3. Recommend partners use NotebookLM web free for competitor/podcast research (`.claude/rules/plugins.md` partner-scoped)

# Cross-refs

- `.claude/skills/kb-ingest/SKILL.md` — extension target
- `knowledge-base/raw/ai-llm/openai-realtime-voice-component-2026-04-29.md` — pairs (voice + cited RAG)
- `.claude/rules/plugins.md` — partner-scoped tooling
- `project_value_prop_framework` memory — hours-saved framing fits cited-answer reduction in onboarding
