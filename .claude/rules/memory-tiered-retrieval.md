---
paths:
  - "memory/**/*.md"
  - "knowledge-base/**/*.md"
  - "docs/dev-knowledge/**/*.md"
---

# Memory Tiered Retrieval — 3-Layer Progressive Disclosure

## Rule
When pulling from memory or KB, follow 3-layer pattern: **index → context → details**. Never fetch full bodies before filtering. Cuts token cost 6-12x vs flat fetch.

## Why
Pattern adapted from `thedotmack/claude-mem` (MIT) — proven 6-12x token reduction in production memory MCP. Our memory system + `knowledge-base/wiki/` currently has no tiering: every query reads full files. Long sessions burn context fast on irrelevant body content.

## The 3 Layers

| Layer | Source | Cost/result | Purpose |
|-------|--------|-------------|---------|
| 1. Index | `MEMORY.md`, `knowledge-base/INDEX.md`, `docs/dev-knowledge/*.md` headlines | ~50-100 tok | Filter — what's even relevant |
| 2. Context | Frontmatter + first 20 lines of candidate file | ~200-300 tok | Confirm — is this the right one |
| 3. Details | Full file body | ~500-2000 tok | Use — only after layers 1-2 narrow it |

**Never skip layer 1.** Going straight to Read on a candidate file = flat fetch = token waste.

## Apply to AgentNexLiFy surfaces

### Auto-memory (`~/.claude/projects/.../memory/`)
- Layer 1: `MEMORY.md` (already loaded into session) — scan one-line hooks
- Layer 2: read frontmatter (name + description fields) of 1-3 candidates via Read with `limit: 8`
- Layer 3: full Read only on the survivor

### Knowledge base (`knowledge-base/wiki/`)
- Layer 1: grep `INDEX.md` OR semantic search via `/kb-query` (returns top-K snippets, not bodies)
- Layer 2: Read `limit: 30` on top candidate (gets frontmatter + opening)
- Layer 3: full Read only when layer 2 confirms

### Dev knowledge (`docs/dev-knowledge/`)
- Layer 1: Grep with `output_mode: "files_with_matches"` for the term
- Layer 2: Grep with `output_mode: "content"` + `-C 3` for matched files
- Layer 3: full Read only when context match warrants it

## Anti-patterns
- Read full `bug-patterns.md` to find one bug → use Grep first
- Load every `wiki/` article matching a topic → semantic-search top-3 via `/kb-query`
- Run Read on a memory file before confirming MEMORY.md hook is even relevant
- Pre-load 5+ candidate files "just in case" — defeats the savings

## When to skip tiering
- File is small (<50 lines) — flat Read is fine
- Already in session context — no re-fetch needed
- Editing the file — Edit needs full content (Read first is correct here)
- Confidence is 95%+ that this is the right file (skip layer 2)

## Token-cost visibility
When using KB/memory in a long session, state the layer:
- "Layer 1 hit: 3 candidates from INDEX.md"
- "Layer 2 confirmed: wiki/ai-llm/llm-wiki-karpathy-pattern.md is the match"
- "Layer 3: full Read"

Makes cost legible. Surfaces over-fetching habits.

## Cross-refs
- `.claude/rules/kb-first.md` — check KB before researching
- `.claude/skills/last30days/SKILL.md` — knowledge synthesis (consumer of layer-1 indices)
- `.claude/skills/kb-query/SKILL.md` — semantic search (built-in layer-1 tool)
- Source: thedotmack/claude-mem `cursor-hooks/cursorrules-template.md` "3-Layer Workflow"

## Pattern attribution
3-layer progressive disclosure pattern: thedotmack/claude-mem (MIT). Adapted for AgentNexLiFy file-based memory + pgvector KB. No code copied — pattern only.
