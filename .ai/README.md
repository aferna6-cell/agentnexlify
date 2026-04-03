# AI Agent Discovery

This directory contains machine-readable configuration for AI coding agents.

## manifest.json

The `manifest.json` file is a universal index of all AI resources in this repository:

- **Skills** — Domain knowledge modules with invariants and workflows
- **Agents** — Specialized role definitions with deep domain expertise
- **Workflows** — Step-by-step procedures for common operations
- **Critical rules** — Invariants that must not be violated
- **Directory map** — What lives where in this codebase

Any AI agent can read `manifest.json` to discover available resources and understand the project structure.

## Platform-Specific Configuration

Each AI tool has its own configuration file at the repo root:

| File | Tool |
|------|------|
| `CLAUDE.md` | Claude Code (most comprehensive) |
| `AGENTS.md` | OpenAI Codex / general agents |
| `GEMINI.md` | Google Gemini CLI |
| `.github/copilot-instructions.md` | GitHub Copilot |
| `.cursorrules` | Cursor AI |
| `.windsurfrules` | Windsurf / Codeium |
| `.clinerules` | Cline / Roo Code |
| `.aider.conf.yml` | Aider CLI |

All files share the same critical rules and point to `manifest.json` for full resource discovery.
