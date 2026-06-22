---
type: project
name: "Dashboard"
tags:
  - project
  - frontend
source_status: source-backed
sensitivity: normal
status: production
last_verified: 2026-06-22
---

# Dashboard

## Summary
The React 18 / Vite 6 customer + admin dashboard at `app.agentnexlify.com` — ~35 API domain
modules covering CRM, conversations, pipeline, billing, appointments, and automations. The
owner-facing control surface for [[AgentNexLiFy Platform]].

## Patterns
- Display data always from live API, not JWT claims (claims don't refresh on plan change) —
  see [[JWT for Auth Only]].
- New page workflow: `src/pages/<Name>.jsx` → dark theme + live API + empty state → register
  in `Sidebar.jsx` + route in `App.jsx`.

## Related
- [[AgentNexLiFy Platform]] · [[Chat Widget]] · [[Agent OS]]

## Provenance
- [[docs-deployment-surfaces]] · [[dev-knowledge-architecture-decisions]] · [[repo-agentnexlify-claude-md]]
