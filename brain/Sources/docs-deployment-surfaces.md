---
type: source
source_id: docs-deployment-surfaces
origin: local-repo
path: /home/user/agentnexlify/docs/deployment-surfaces.md
accessed: 2026-06-22
sensitivity: normal
tags: [source]
---

# Source: docs/deployment-surfaces.md

## What this is
Map of deployed surfaces + their hosts/URLs.

## What it proves
- Backend: `agentnexlify-production.up.railway.app` (Railway).
- Marketing site: `agentnexlify.vercel.app` (Vercel).
- Dashboard: `app.agentnexlify.com`.
- Widget must stay byte-identical across mirror copies; sync via
  `python scripts/sync_widget_assets.py` (CI-enforced).
