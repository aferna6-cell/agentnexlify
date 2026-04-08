---
name: agentnexlify-widget-sync
description: "Verify widget JS files are identical between widget/ and frontend/public/widget/."
effort: low
allowed-tools: Read, Glob, Bash
---

# Widget File Sync Check

The embeddable chat widget is served from two locations:
- `widget/agentnexlify-widget.js`
- `frontend/public/widget/agentnexlify-widget.js`

These MUST be identical. Run:
```bash
diff widget/agentnexlify-widget.js frontend/public/widget/agentnexlify-widget.js
```

If they differ, copy the newer version to the other location. The `widget/` directory is the source of truth.
