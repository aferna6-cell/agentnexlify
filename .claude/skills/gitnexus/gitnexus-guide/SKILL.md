---
name: gitnexus-guide
effort: low
description: Reference guide for all GitNexus MCP tools, resources, graph schema, and the skill routing table for different code tasks. Use when user says 'what gitnexus tools', 'gitnexus reference', 'gitnexus schema', 'gitnexus tools available', 'how to use gitnexus', 'gitnexus guide', or asks about gitnexus guide.
version: 1.0.0
origin: claude
triggers:
- what gitnexus tools
- gitnexus reference
- gitnexus schema
- gitnexus tools available
- how to use gitnexus
- gitnexus guide
---

# GitNexus Guide

Quick reference for all GitNexus MCP tools, resources, and the knowledge graph schema.

## When to Use
- Looking up available GitNexus tools and their capabilities
- Understanding the graph schema for writing Cypher queries
- Finding which GitNexus skill to use for a specific task

## When NOT to Use
- Performing a specific code task (read the task-specific skill instead: exploring, debugging, impact-analysis, refactoring)
- Running CLI commands (use gitnexus-cli instead)

## Always Start Here

For any task involving code understanding, debugging, impact analysis, or refactoring:

1. **Read `gitnexus://repo/{name}/context`** — codebase overview + check index freshness
2. **Match your task to a skill below** and **read that skill file**
3. **Follow the skill's workflow and checklist**

> If step 1 warns the index is stale, run `npx gitnexus analyze` in the terminal first.

## Skills

| Task                                         | Skill to read       |
| -------------------------------------------- | ------------------- |
| Understand architecture / "How does X work?" | `gitnexus-exploring`         |
| Blast radius / "What breaks if I change X?"  | `gitnexus-impact-analysis`   |
| Trace bugs / "Why is X failing?"             | `gitnexus-debugging`         |
| Rename / extract / split / refactor          | `gitnexus-refactoring`       |
| Tools, resources, schema reference           | `gitnexus-guide` (this file) |
| Index, status, clean, wiki CLI commands      | `gitnexus-cli`               |

## Tools Reference

| Tool             | What it gives you                                                        |
| ---------------- | ------------------------------------------------------------------------ |
| `query`          | Process-grouped code intelligence — execution flows related to a concept |
| `context`        | 360-degree symbol view — categorized refs, processes it participates in  |
| `impact`         | Symbol blast radius — what breaks at depth 1/2/3 with confidence         |
| `detect_changes` | Git-diff impact — what do your current changes affect                    |
| `rename`         | Multi-file coordinated rename with confidence-tagged edits               |
| `cypher`         | Raw graph queries (read `gitnexus://repo/{name}/schema` first)           |
| `list_repos`     | Discover indexed repos                                                   |

## Resources Reference

Lightweight reads (~100-500 tokens) for navigation:

| Resource                                       | Content                                   |
| ---------------------------------------------- | ----------------------------------------- |
| `gitnexus://repo/{name}/context`               | Stats, staleness check                    |
| `gitnexus://repo/{name}/clusters`              | All functional areas with cohesion scores |
| `gitnexus://repo/{name}/cluster/{clusterName}` | Area members                              |
| `gitnexus://repo/{name}/processes`             | All execution flows                       |
| `gitnexus://repo/{name}/process/{processName}` | Step-by-step trace                        |
| `gitnexus://repo/{name}/schema`                | Graph schema for Cypher                   |

## Graph Schema

**Nodes:** File, Function, Class, Interface, Method, Community, Process
**Edges (via CodeRelation.type):** CALLS, IMPORTS, EXTENDS, IMPLEMENTS, DEFINES, MEMBER_OF, STEP_IN_PROCESS

```cypher
MATCH (caller)-[:CodeRelation {type: 'CALLS'}]->(f:Function {name: "myFunc"})
RETURN caller.name, caller.filePath
```

## Gotchas

- **Index staleness.** `npx gitnexus analyze` must re-run after any significant commit or the MCP will return pre-refactor data. Post-commit hook fires automatically — verify the hook is installed.
- **Cypher queries on a non-existent node** return empty, not an error. Validate the symbol exists with `gitnexus_context` before writing deep Cypher.
- **MCP tool name drift.** If `gitnexus_query` stops working, check `npx gitnexus --version` — the MCP server spec may have renamed tools between versions.
- **Embeddings are off by default.** Semantic search is keyword-based until `--embeddings` is enabled. Check `.gitnexus/meta.json` for current status.
- **First query after restart is slow** (2-5s) on repos with 5k+ symbols. Subsequent queries are cached. Don't mistake this for a hang.
- **`CodeRelation` edge label is a single node type** with `type` property — it's NOT separate `CALLS`, `IMPORTS` edge types at the Neo4j level. Cypher filter must use `WHERE r.type = 'CALLS'`.
- **`gitnexus_impact` confidence reflects static analysis** — dynamic dispatch (`importlib`, React.lazy) is invisible. Manually verify for meta-programming-heavy code.
