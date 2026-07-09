# Idea 4 — Verify SMS Dashboard GH Issue Has `ai-ready` Label

**Category:** operational / workflow_efficiency  
**Effort:** XS  
**Type:** AUTONOMOUS-EXECUTABLE (verification only)  
**Score:** 6/10

## Problem

Nightly commit review 2026-07-01 filed a GH issue for the SMS Compliance Dashboard (missing frontend page + router). The issue-to-pr-loop polls every 15 min for issues with the `ai-ready` label.

If the label was not applied when the issue was filed, the loop won't pick it up.

## Proposal

Verify the GH issue has `ai-ready` label applied. If missing, apply it via GitHub MCP:

```
mcp__github__add_label_to_issue(repo="aferna6-cell/agentnexlify", label="ai-ready")
```

This is a pure operational verification, not a code change.

## Why Interesting

SMS Dashboard has been pending 11+ days (runs 73-74 winner). The nightly 2026-07-01 log confirmed GH issue was filed and "issue-to-pr-loop path activated." If label is missing, the entire pipeline stalls silently.

## Why Not Top Pick

- Not a code improvement — it's a label check
- Already noted in nightly log as "activated" — label likely applied correctly
- Verifying this is useful but secondary to Zapier mandate
- Subconscious cycle is for recommendations, not operational minutiae
- Run 75 already escalated SMS Dashboard; adding another recommendation would be circular
