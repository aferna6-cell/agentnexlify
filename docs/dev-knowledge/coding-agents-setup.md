# Multi-Model Coding Agent Setup

How to use different AI models alongside Claude Code for AgentNexLiFy development.

## Available Tools

### 1. Claude Code (Primary — complex work)
Already configured. Use for multi-file features, debugging, architecture, git operations.
```bash
claude   # starts Claude Code in current directory
```

### 2. Aider + Qwen 3.6 Plus (Free — quick tasks)
Uses OpenRouter's free preview of Qwen 3.6 Plus. Good for code review, single-file edits, boilerplate.
```bash
# First time: set your OpenRouter API key
export OPENROUTER_API_KEY="sk-or-YOUR_KEY"

# Use Qwen 3.6 Plus (free preview, API-only)
aider --model openrouter/qwen/qwen3.6-plus-preview

# Use local Qwen 3 Coder (already installed, runs on CPU)
aider --model ollama/qwen3-coder:30b

# Use smaller local model (faster on CPU)
aider --model ollama/qwen2.5-coder:7b
```

### 3. Aider + Gemma 4 (Free — local, needs Ollama update)
```bash
# Step 1: Update Ollama (needs sudo)
curl -fsSL https://ollama.com/install.sh | sudo sh

# Step 2: Pull Gemma 4
ollama pull gemma4

# Step 3: Use with Aider
aider --model ollama/gemma4
```

### 4. Aider + Claude (Same quality as Claude Code, different interface)
```bash
export ANTHROPIC_API_KEY="your_key"
aider --model claude-sonnet-4-6
```

## When to Use What

| Task | Best Tool | Why |
|------|-----------|-----|
| New feature (multiple files) | Claude Code | Best at multi-file agent workflows |
| Fix a bug with error trace | Claude Code | Has MCP, agents, skills |
| Quick single-file edit | Aider + Qwen 3.6 Plus | Free, fast |
| Code review | Aider + Qwen 3.6 Plus | Free, good at spotting issues |
| Generate boilerplate | Aider + local Qwen | Free, no API calls |
| Write docs/comments | Aider + any model | Low stakes, any model works |
| Sensitive/private code | Aider + Ollama local | Data stays on machine |
| Pair programming style | Aider (any model) | Aider's git-native workflow |

## Cost Comparison (Monthly Estimate)

| Setup | Estimated Cost |
|-------|---------------|
| Claude Code only (current) | $100-200/mo |
| Claude Code + Qwen 3.6 Plus via OpenRouter | $60-120/mo (40% less) |
| Claude Code + Ollama local models | $80-150/mo (25% less) |
| All three combined | $50-100/mo (50% less) |

## Local Models on This Machine

Currently installed (4GB VRAM — models run on CPU):
- `qwen3-coder:30b` (18GB) — slow but high quality
- `qwen2.5-coder:7b` (4.7GB) — fastest local option

After Ollama update:
- `gemma4` — Google's latest, Apache 2.0

## OpenRouter Setup (for Qwen 3.6 Plus free access)

1. Go to https://openrouter.ai
2. Sign up and get an API key
3. Set the environment variable:
   ```bash
   export OPENROUTER_API_KEY="sk-or-YOUR_KEY"
   ```
4. Qwen 3.6 Plus is currently free on OpenRouter's preview tier
