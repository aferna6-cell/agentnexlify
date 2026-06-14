# 🔌 Integrations

This directory contains The Agency integrations for Claude Code.

## Supported Tools

- **[Claude Code](#claude-code)** — `.md` agents, use the repo directly
- **[MCP Memory](#mcp-memory)** — persistent memory server config

## Quick Install

```bash
./scripts/install.sh --tool claude-code
```

## Regenerating Integration Files

If you add or modify agents, regenerate integration files:

```bash
./scripts/convert.sh
```

---

## Claude Code

The Agency was originally designed for Claude Code. Agents work natively
without conversion.

```bash
cp -r <category>/*.md ~/.claude/agents/
# or install everything at once:
./scripts/install.sh --tool claude-code
```

See [claude-code/README.md](claude-code/README.md) for details.

---

## MCP Memory

Persistent memory server configuration for Claude Code sessions.

See [mcp-memory/README.md](mcp-memory/README.md) for details.
