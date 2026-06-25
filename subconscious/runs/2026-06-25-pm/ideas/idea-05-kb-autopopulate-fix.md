# Idea 05 — Fix kb-autopopulate.sh (agent-browser CLI → WebFetch/curl)

**Category:** operational
**Confidence:** HIGH  
**Autonomous-executable:** YES
**Parking lot ROI:** 1.8 (from prior backlog)

## Problem
kb-autopopulate.sh calls agent-browser CLI which is not installed in the remote
execution environment. KB has been stale for 50+ days. Twice-daily schedule fires
but produces no output.

## Fix
Replace `agent-browser fetch <url>` calls with `curl -sL <url>` or WebFetch MCP.
The script pipes HTML to an LLM for summarization — curl produces equivalent input.

## Why not this run
1. Not urgent — KB staleness doesn't fail any invariant or block commits
2. Run 65 fix must land first (unblocks Check 13)
3. Moratorium is active — only critical/mandate items should win this run

## Verdict: PARKING LOT
Good candidate for run 68 or 69 when moratorium exits. Already tracked in
improvement-backlog.md. No change needed this run.
