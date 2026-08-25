# Claude Execution Layers — 5-Layer Mental Model

## Rule
Claude Code is not a chatbot. Treat as 5-layer execution environment. If used as chatbot, underuse ~10x.

## The 5 Layers

### 1. Conversation Layer — Reasoning
Structured thinking, planning, decomposition, edge-case enumeration.
- Invoke: plain prompts, `/brainstorm`, ultrathink mode
- Models: Opus for plan, Sonnet for iterate
- Output: no code, just analysis

### 2. Code Layer — First-Class Output
Production code, refactors, full-stack features.
- Invoke: `/new-feature`, `/fix-bug`, `/refactor`
- Models: Sonnet default, Haiku for mechanical
- Output: committed code + tests

### 3. Tool Layer — External Integration
MCP servers, browser automation, APIs, filesystem.
- Invoke: MCP tools directly (`mcp__supabase__*`, `mcp__playwright__*`)
- Config: `.mcp.json` + `.claude/settings.json` `enableAllProjectMcpServers`
- Output: real-world effects (DB writes, HTTP calls, file changes)

### 4. Memory Layer — Persistent Context
CLAUDE.md, memory system, plan files, PROMPTLIBRARY.
- CLAUDE.md: project rules, auto-loaded
- `memory/`: cross-session facts (user, feedback, project, reference)
- `plans/`: active work state
- `PROMPTLIBRARY.md`: versioned prompt components
- Output: stateful teammate, not stateless AI

### 5. Workflow Layer — Programmable Automation
Skills, commands, hooks, agents, scheduled tasks.
- Skills: `.claude/skills/*/SKILL.md` — trigger-based expertise
- Commands: `.claude/commands/*.md` — slash-invokable workflows
- Hooks: `.claude/settings.json` — deterministic enforcement
- Agents: `.claude/agents/*.md` — specialized sub-executors
- Scheduled: `issue-to-pr-loop` (15-min poll), daily KB compile (6am/6pm)
- Output: systems that run themselves

## Mental Shift: Chat → Execution
| Chatbot usage | Execution-layer usage |
|---------------|-----------------------|
| Ask question, get answer | Delegate implementation, get PR |
| Copy-paste snippet | Merge committed feature |
| One-shot reply | Multi-step workflow |
| Stateless | Stateful via memory + plan files |
| Manual repetition | Skill-packaged automation |
| Single-turn | 15-min autonomous loop |

## Leverage Ladder (highest leverage last)
1. **Answer** — one-shot reply
2. **Code** — generated snippet/function
3. **Feature** — end-to-end committed change
4. **Workflow** — reusable skill/command
5. **System** — autonomous loop that runs without you

Rule 12 from Claude usage patterns: "Build the system, not the answer."

## Anthropic Learning Paths (skilljar)
Foundations:
- `anthropic.skilljar.com/claude-101`
- `anthropic.skilljar.com/ai-fluency-frameworks`

Claude Code:
- `anthropic.skilljar.com/claude-code-101`
- `anthropic.skilljar.com/claude-code-in-action`

Advanced:
- `anthropic.skilljar.com/introduction-to-mcp`
- `anthropic.skilljar.com/model-context-protocol`
- `anthropic.skilljar.com/claude-with-the-api`

Builders:
- `anthropic.skilljar.com/claude-in-amazon-bedrock`
- `anthropic.skilljar.com/claude-with-google-vertex`

AI Fluency tracks:
- `anthropic.skilljar.com/ai-fluency-for-business`
- `anthropic.skilljar.com/teaching-ai-fluency`

Study → Apply → Systemize.

## Applied to AgentNexLiFy
| Layer | AgentNexLiFy implementation |
|-------|------------------------------|
| Conversation | `/morning`, `/brainstorm`, Opus planning |
| Code | `/new-feature`, `/fix-bug`, backend-dev + frontend-dev agents |
| Tool | Supabase MCP, Playwright MCP, Chrome DevTools MCP, GitHub plugin |
| Memory | CLAUDE.md, `memory/`, `PROMPTLIBRARY.md`, `docs/dev-knowledge/` |
| Workflow | 85 skills, 25 commands, 32 hooks, 60 agents, `issue-to-pr-loop` |

## Cross-refs
- `.claude/rules/claude-usage-patterns.md` — 12 operating modes
- `.claude/rules/user-rules.md` — discipline (plan first, ask when unsure)
- `CLAUDE.md` — project rules index
- Source: "Claude Code as Operating System" (Suryansh Tiwari, 2026-04)
