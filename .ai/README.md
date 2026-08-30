# AI Agent Discovery

This directory contains machine-readable configuration for AI coding agents.

## manifest.json

The `manifest.json` file is a universal index of all AI resources in this repository:

- **Skills** — Domain knowledge modules with invariants and workflows
- **Agents** — Specialized role definitions with deep domain expertise
- **Workflows** — Step-by-step procedures for common operations
- **Critical rules** — Invariants that must not be violated
- **Directory map** — What lives where in this codebase
- **`slack-agent-team.json`** — Grok-like Slack invocation surface; GitHub Issues stay the durable hub

Any AI agent can read `manifest.json` to discover available resources and understand the project structure.

## Platform-Specific Configuration

Each agent tool has its own configuration file at the repo root:

| File | Tool |
|------|------|
| `CLAUDE.md` | Claude Code (most comprehensive) |
| `AGENTS.md` | OpenAI Codex / general agents |

Both files share the same critical rules and point to `manifest.json` for full resource discovery.
