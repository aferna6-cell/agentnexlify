---
description: Look up live documentation for any library via Context7 MCP. Use instead of stale training data.
---

# Docs Lookup

Look up current documentation for: `$ARGUMENTS`

## Process

1. Use the Context7 MCP (`mcp__context7__resolve-library-id`) to find the library
2. Use `mcp__context7__get-library-docs` to fetch relevant docs
3. Return only the answer and minimum code example needed

## Rules

- Always use Context7 for docs — training data may be outdated
- If library not found in Context7, fall back to DeepWiki MCP or web search
- Return the current API signature, not what you remember from training
- If the user asks about a specific function/method, return that exact section
- Keep examples minimal and runnable
