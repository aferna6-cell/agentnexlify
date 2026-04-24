# Personal Crypto Trading Advisor — Setup Guide

Claude Desktop + MCPs. No backend. No code to maintain.

---

## Prerequisites

1. [Claude Desktop](https://claude.com/download) — installed and logged in
2. [Node.js](https://nodejs.org) — required for MCP installs via Claude Code

---

## Step 1 — Install MCPs

Open Claude Desktop → switch to **Claude Code** tab → run each command below.

You'll need an API key from each platform. If you don't have one, prompt Claude Code:
> "Help me get a free API key for [platform]"

### LunarCrush (Social Sentiment)
Easiest — use the **Connectors** tab in Claude Desktop (no CLI needed):
Claude Desktop → Customize → Connectors → search "LunarCrush" → Connect

### CoinGecko (Price + On-Chain Data)
```bash
claude mcp add coingecko
# Follow prompts — paste your CoinGecko API key
# Docs: https://docs.coingecko.com/docs/ai-agent-hub/mcp-server
```

### CryptoPanic (Breaking News)
```bash
claude mcp add cryptopanic https://github.com/kukapay/cryptopanic-mcp-server
# Paste your CryptoPanic API key when prompted
```

### Dune (On-Chain Analytics)
```bash
claude mcp add dune
# Paste your Dune API key when prompted
# Docs: https://docs.dune.com/api-reference/agents/mcp
```

### Perplexity (Live Web Research) — add if you have an API key
```bash
claude mcp add perplexity
# Docs: https://docs.perplexity.ai/docs/getting-started/integrations/mcp-server
```

---

## Step 2 — Create a Claude Project

1. Open Claude Desktop (chat interface, not Claude Code)
2. Click **Projects** → **New Project**
3. Name it: `Crypto Research Hub`
4. Open **Project Instructions** and paste the contents of `system-prompt.md`

---

## Step 3 — Verify

Send this test query in the project:
> "Show me the top 5 cryptos by market cap right now with 24h price change."

Claude should pull live data from CoinGecko. If it doesn't, check that the MCP shows as connected (green dot) in Claude Desktop → Settings → MCPs.

---

## Execution MCPs (add later — real wallet access)

Once comfortable with research MCPs, these enable on-chain execution:
- **GOAT SDK** — swaps, transfers, balance checks: `https://github.com/goat-sdk/goat`
- **DeFi Portfolio** — Aave/Uniswap/Compound positions: `https://github.com/edkdev/defi-trading-mcp`

**Always test with a throwaway wallet first. Never paste a primary wallet seed phrase anywhere.**

---

## Troubleshooting

- MCP not connecting → Claude Code: `"I'm having trouble installing [x] MCP, help me"`
- API key rejected → check for trailing spaces when pasting
- No live data → restart Claude Desktop after adding MCPs
