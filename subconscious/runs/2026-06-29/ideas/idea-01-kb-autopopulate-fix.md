# Idea 01 — Fix KB Autopopulate Discover Step

**Category:** code_health  
**Effort:** S (2-line change in existing bash script)  
**Moratorium-safe:** YES — AUTONOMOUS-EXECUTABLE, no new human-required item  
**AUTONOMOUS-EXECUTABLE:** YES — bash script + prompt string edit in nightly scope  

## Evidence

- `scripts/daily/kb-autopopulate.sh` line 80: `--allowedTools Bash,Read,Write,Edit,Glob,Grep` — WebFetch excluded from discover step
- Same script lines 52-53: DISCOVER_PROMPT says "per CLAUDE.md rule: NEVER use WebFetch/WebSearch" — this rule does not exist in CLAUDE.md; it's a false constraint blocking the curl/WebFetch fallback
- KB stale 53+ days (parking lot added run 54, ROI 1.8)
- `subconscious/runs/2026-06-28-pm/winning-concept.md` §Run 71 Forecast: "primary = KB autopopulate fix if SMS done"
- Nightly 2026-06-29 backlog explicitly lists "KB autopopulate fix (run 71)"
- `knowledge-base/log.md` has no entries in 53+ days

## Root Cause

Two bugs compound:
1. `--allowedTools` on line 80 excludes WebFetch → headless Claude session cannot call it
2. DISCOVER_PROMPT contains false CLAUDE.md rule "NEVER use WebFetch/WebSearch" → even if WebFetch were allowed, the prompt tells Claude not to use it
3. curl via Bash is the last fallback, but in the remote/cloud environment outbound curl may fail without the proxy config that WebFetch uses natively

## Fix

In `scripts/daily/kb-autopopulate.sh`:

**Line 80** — add WebFetch to discover step allowed tools:
```
# Before:
  --allowedTools Bash,Read,Write,Edit,Glob,Grep \

# After:
  --allowedTools Bash,Read,Write,Edit,Glob,Grep,WebFetch \
```

**Lines 52-53** — update DISCOVER_PROMPT TOOLS instruction:
```
# Before:
TOOLS: Use agent-browser via Bash (per CLAUDE.md rule: NEVER use WebFetch/WebSearch). 
Command: `agent-browser fetch <url>` and `agent-browser search <query>`. 
If agent-browser unavailable, use `curl -sL` to fetch URLs directly.

# After:
TOOLS: Use agent-browser via Bash if available (`agent-browser fetch <url>` and 
`agent-browser search <query>`). If agent-browser unavailable, use WebFetch tool 
as the primary fallback. curl -sL is a last resort only.
```

## Expected Impact

- Restores twice-daily KB auto-population (6am + 6pm)
- Clears 53-day stale KB
- knowledge-base/wiki/ grows again; /kb-query returns current results
- Removes an item from parking lot

## Nightly Scope

Bash script line edit + prompt string update = LOW risk, additive, no schema changes, no widget changes. Identical mechanism to Check 11/12 additions (061582c, 4226ef4) which nightly executed autonomously.
