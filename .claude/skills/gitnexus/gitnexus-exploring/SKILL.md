---
name: gitnexus-exploring
effort: medium
description: Explore unfamiliar codebases, understand architecture, trace execution flows, and answer how code works using GitNexus. Use when user says 'how does this work', 'project structure', 'show me the auth flow', 'explore codebase', 'understand architecture', 'what calls this function', or asks about gitnexus exploring.
version: 1.0.0
origin: claude
triggers:
- how does this work
- project structure
- show me the auth flow
- explore codebase
- understand architecture
- what calls this function
---

# Exploring Codebases with GitNexus

## When to Use

- "How does authentication work?"
- "What's the project structure?"
- "Show me the main components"
- "Where is the database logic?"
- Understanding code you haven't seen before

## When NOT to Use

- Debugging a specific bug or error (use gitnexus-debugging instead)
- Analyzing what will break before making changes (use gitnexus-impact-analysis instead)
- Renaming or restructuring code (use gitnexus-refactoring instead)

## Workflow

```
1. READ gitnexus://repos                          → Discover indexed repos
2. READ gitnexus://repo/{name}/context             → Codebase overview, check staleness
3. gitnexus_query({query: "<what you want to understand>"})  → Find related execution flows
4. gitnexus_context({name: "<symbol>"})            → Deep dive on specific symbol
5. READ gitnexus://repo/{name}/process/{name}      → Trace full execution flow
```

> If step 2 says "Index is stale" → run `npx gitnexus analyze` in terminal.

## Checklist

```
- [ ] READ gitnexus://repo/{name}/context
- [ ] gitnexus_query for the concept you want to understand
- [ ] Review returned processes (execution flows)
- [ ] gitnexus_context on key symbols for callers/callees
- [ ] READ process resource for full execution traces
- [ ] Read source files for implementation details
```

## Resources

| Resource                                | What you get                                            |
| --------------------------------------- | ------------------------------------------------------- |
| `gitnexus://repo/{name}/context`        | Stats, staleness warning (~150 tokens)                  |
| `gitnexus://repo/{name}/clusters`       | All functional areas with cohesion scores (~300 tokens) |
| `gitnexus://repo/{name}/cluster/{name}` | Area members with file paths (~500 tokens)              |
| `gitnexus://repo/{name}/process/{name}` | Step-by-step execution trace (~200 tokens)              |

## Tools

**gitnexus_query** — find execution flows related to a concept:

```
gitnexus_query({query: "payment processing"})
→ Processes: CheckoutFlow, RefundFlow, WebhookHandler
→ Symbols grouped by flow with file locations
```

**gitnexus_context** — 360-degree view of a symbol:

```
gitnexus_context({name: "validateUser"})
→ Incoming calls: loginHandler, apiMiddleware
→ Outgoing calls: checkToken, getUserById
→ Processes: LoginFlow (step 2/5), TokenRefresh (step 1/3)
```

## Example: "How does payment processing work?"

```
1. READ gitnexus://repo/my-app/context       → 918 symbols, 45 processes
2. gitnexus_query({query: "payment processing"})
   → CheckoutFlow: processPayment → validateCard → chargeStripe
   → RefundFlow: initiateRefund → calculateRefund → processRefund
3. gitnexus_context({name: "processPayment"})
   → Incoming: checkoutHandler, webhookHandler
   → Outgoing: validateCard, chargeStripe, saveTransaction
4. Read src/payments/processor.ts for implementation details
```

## Gotchas

- **`context` resource is ~150 tokens, but `cluster/{name}` can be 500+.** Use context first, cluster only when narrowing.
- **Symbol name collisions.** `gitnexus_context({name: "handle"})` returns every `handle()` across the repo. Add a file-path hint or use Cypher.
- **Process names are capitalized pascal case.** `loginFlow` returns empty — use `LoginFlow`.
- **Clusters auto-regenerate on re-analyze.** A cluster name stable today may not exist tomorrow. Don't hard-code cluster names in docs.
- **External lib calls appear as orphan nodes.** If a function "ends" at an unknown symbol, it's probably a library call. Check the import map for the real target.
