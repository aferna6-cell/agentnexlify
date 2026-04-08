# OpenClaw Migration

Migrated from `~/.openclaw/` to this repo on 2026-04-08.

## What's Here

### workspace/
Identity and agent personality files from the OpenClaw workspace:
- `SOUL.md` — agent personality and values
- `USER.md` — user profile (Aidan)
- `IDENTITY.md` — agent identity (MyAgent)
- `TOOLS.md` — local tool notes template
- `HEARTBEAT.md` — heartbeat config
- `MEMORY.md` — long-term agent memory

### morpheus/
Polymarket trading bot configs and strategy docs:
- `config_aggressive.yaml` — aggressive trading mode config
- `polymarket-bot-config.yaml` — main Morpheus disciplined config
- `polymarket-bot-pyproject.toml` — Python project dependencies
- `morpheus-sync-*` — Kalshi sync project configs
- Strategy docs (ENGINE_FIX_PLAN, MORPHEUS_*, POLYMARKET_STRATEGY_RESEARCH, STRATEGY_DEEP_DIVE)

### memory/
Daily session logs from OpenClaw (2026-01-31 through 2026-04-06).

### Root files
- `openclaw.json` — full OpenClaw config (model providers, channels, gateway, plugins)
- `cron-jobs.json` — scheduled job definitions
- `exec-approvals.json` — execution approval settings

## Hermes Config Changes

The following were updated in `~/.hermes/`:

### config.yaml
- Deduplicated `custom_providers` (was 8 entries, now 3: minimax, ollama, openrouter)
- Added OpenRouter provider with env var reference
- Replaced hardcoded GLM API key with `${GLM_API_KEY}` env var

### .env
- Added all OpenClaw env vars (Polymarket, Kalshi, Tavily, Telegram, etc.)
- Added AgentNexLiFy Supabase/Cloudflare keys
- Updated `MESSAGING_CWD` to point to `/home/aidan/agentnexlify`

## Model Providers (from OpenClaw)

| Provider | Base URL | Models |
|----------|----------|--------|
| Anthropic | (default) | Claude Opus 4.6 |
| MiniMax | https://api.minimax.io/anthropic | MiniMax-M2.7 |
| OpenRouter | https://openrouter.ai/api/v1 | GLM-5, Qwen 3.6 Plus |
| Ollama | http://127.0.0.1:11434 | Qwen3 Coder 30B, Qwen2.5 Coder 7B |
| OpenAI Codex | (OAuth) | GPT-5.4 |

## Agent Roles (from OpenClaw)

| Agent ID | Model | Purpose |
|----------|-------|---------|
| orchestrator | Claude Opus 4.6 | Main orchestrator |
| coder | MiniMax M2.7 | Code generation |
| general | MiniMax M2.7 | General tasks |
| helper | MiniMax M2.7 HighSpeed | Quick helpers |
| local-qwen | Qwen3 Coder 30B | Local coding |
| local-qwen-fast | Qwen2.5 Coder 7B | Fast local tasks |
