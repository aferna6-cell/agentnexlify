---
name: agentnexlify-widget-integrity
description: Preserve the current production widget contract in AgentNexLiFy. Use when editing widget JavaScript, widget embed snippets, widget API endpoints, business-page widget loading, widget config fields, or any code/docs that could drift between the live widget and older widget generations in this repository.
---

# AgentNexLiFy Widget Integrity

This repo contains multiple widget generations. Do not patch the wrong one.

## Current production path
- Primary source: `widget/agentnexlify-widget.js`
- Mirrored copy: `frontend/public/widget/agentnexlify-widget.js`
- Backend API: `backend/routers/widget.py`
- Public embed consumers include the hosted business page flow in `frontend/src/pages/BusinessPage.jsx`

## Current embed contract
- Required attribute: `data-api-key`
- Optional attributes: `data-brand-color`, `data-api-base`

## Legacy surfaces to treat carefully
- `widget/nexlify-chat.js` and `widget/nexlify-chat.src.js`
- `public/widget.js` and `public/widget.src.js`
- `widget/README.md` when it documents `data-business-id`, `data-business-name`, or `data-webhook-url`

## Rules
- Keep `widget/agentnexlify-widget.js` and `frontend/public/widget/agentnexlify-widget.js` identical.
- If you change widget API payloads or config fields, verify both the backend route and every embed path that reads them.
- Do not silently mix the old `data-key` / `data-business-id` contracts into the current widget line.
- If the task is to unify widget generations, make that an explicit migration plan instead of a partial spot fix.

## Quick checks
- Search for `agentnexlify-widget.js`, `nexlify-chat`, and `public/widget.js`.
- Verify the change does not break `frontend/public/widget-test.html`, `widget/preview.html`, or hosted business-page embedding assumptions.
